# Copyright (c) 2002-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

from Products.SilvaDocument.interfaces import IDocumentVersion
from Products.SilvaDocument.transform.base import Context
from zExceptions import NotFound

from silva.core.upgrade.upgrade import BaseUpgrader, AnyMetaType, content_path

from urlparse import urlparse
import logging

logger = logging.getLogger('silva.core.upgrade')


#-----------------------------------------------------------------------------
# 2.2.0 to 2.3.0a1
#-----------------------------------------------------------------------------

VERSION_A1='2.3a1'


class RootUpgrader(BaseUpgrader):

    def upgrade(self, root):
        installed_ids = root.objectIds()

        # add service_references
        factory = root.manage_addProduct['silva.core.references']
        if 'service_references' not in installed_ids:
            factory.manage_addReferenceService(
                'service_references', 'Silva References')

        # remove un-needed Silva Document services
        for service in ['service_editor',
                        'service_editorsupport',
                        'service_old_codesource_charset',
                        'service_widgets',
                        'service_doc_editor',
                        'service_doc_previewer',
                        'service_doc_viewer',
                        'service_field_editor',
                        'service_field_viewer',
                        'service_nlist_editor',
                        'service_nlist_previewer',
                        'service_nlist_viewer',
                        'service_sub_editor',
                        'service_sub_previewer',
                        'service_sub_viewer',
                        'service_table_editor',
                        'service_table_viewer']:
            try:
                root.managed_delObjects([service])
            except:
                logger.error("failed to remove %s" % service)

        return root


RootUpgrader = RootUpgrader(VERSION_A1, 'Silva Root')


def split_path(path):
    parts = path.split('/')
    while parts and parts[0] == '.':
        parts = parts[1:]
    return parts


def build_reference(context, target, node):
    """Create a new reference to the given target and store it on the
    node.
    """
    reference_name, reference = context.new_reference()
    reference.set_target(target)
    node.setAttribute('reference', reference_name)


class DocumentUpgrader(BaseUpgrader):
    """We rewrite here document links and images in order to use
    references where ever it is possible.
    """

    def upgrade(self, obj):
        for version in obj.objectValues():
            if IDocumentVersion.providedBy(version):
                context = Context(version, None)
                dom = version._get_document_element()
                self.__upgrade_links(version, context, dom)
                self.__upgrade_images(version, context, dom)
        return obj

    def __upgrade_links(self, version, context, dom):
        links = dom.getElementsByTagName('link')
        version_path = content_path(version)
        if links:
            logger.info('upgrading links in: %s', version_path)
        for link in links:
            path = link.getAttribute('url')
            if not urlparse(unicode(path))[0]:
                # Look for object
                try:
                    target = context.model.unrestrictedTraverse(
                        split_path(path))
                except (AttributeError, KeyError, NotFound):
                    logger.error('broken link %s in %s' % (path, version_path))
                    continue
                build_reference(context, target, link)
                link.removeAttribute('url')

    def __upgrade_images(self, version, context, dom):
        images = dom.getElementsByTagName('image')
        version_path = content_path(version)

        def resolve_path(path):
            """Resolve a path to the given content.
            """
            try:
                return context.model.unrestrictedTraverse(split_path(path))
            except (AttributeError, KeyError, NotFound):
                logger.error('broken image %s in %s' % (path, version_path))
                return None

        def make_link(image, target, title='', window_target=''):
            """Create a link, replace the image with it and set the
            image as child of the link.
            """
            link = dom.createElement('link')
            if not isinstance(target, unicode):
                build_reference(context, target, link)
            else:
                link.setAttribute('url', target)
            if title:
                link.setAttribute('title', title)
            if window_target:
                link.setAttribute('target', window_target)
            parent = image.parentNode
            parent.replaceChild(link, image)
            link.appendChild(image)
            return link

        if images:
            logger.info('upgrading images in: %s', version_path)
        for image in images:
            path = image.getAttribute('path')
            target = resolve_path(path)
            if target is not None:
                # If the image target is found it is changed to a
                # reference. However if it is not, we still want to
                # process the other aspect of the image tag migration
                # so just don't do continue here.
                build_reference(context, target, image)
                image.removeAttribute('path')
                image.removeAttribute('rewritten_path')
            # Collect link title/target
            title = ''
            if image.hasAttribute('title'):
                title = image.getAttribute('title')
                image.removeAttribute('title')
            window_target = ''
            if image.hasAttribute('target'):
                window_target = image.getAttribute('target')
                image.removeAttribute('target')
            link_set = False
            # Check for a link
            if image.hasAttribute('link'):
                link = image.getAttribute('link')
                if link:
                    link_target = resolve_path(link)
                    if link_target is not None:
                        make_link(image, link_target, title, window_target)
                    else:
                        make_link(image, link, title, window_target)
                    link_set = True
                image.removeAttribute('link')
            # Check for a link to high resolution version of the image
            if image.hasAttribute('link_to_hires'):
                link = image.getAttribute('link_to_hires')
                if link == '1' and link_set is False:
                    make_link(image, target, title, window_target)
                    link_set = True
                image.removeAttribute('link_to_hires')
            # Save the image title (aka alt) to its new name
            if image.hasAttribute('image_title'):
                title = image.getAttribute('image_title')
                image.removeAttribute('image_title')
                image.setAttribute('title', title)



DocumentUpgrader = DocumentUpgrader(VERSION_A1, 'Silva Document')
