# Copyright (c) 2002-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

from Products.SilvaDocument.interfaces import IDocumentVersion
from Products.SilvaDocument.transform.base import Context
from zExceptions import NotFound

from silva.core.interfaces import ISilvaObject
from silva.core.upgrade.upgrade import BaseUpgrader, AnyMetaType, content_path
from silva.core.upgrade.upgrader.update_220 import UpdateIndexerUpgrader

from urlparse import urlparse
import logging
import transaction

logger = logging.getLogger('silva.core.upgrade')


#-----------------------------------------------------------------------------
# 2.2.0 to 2.3.0a1
#-----------------------------------------------------------------------------

VERSION_A1='2.3a1'


class RootUpgrader(BaseUpgrader):

    def upgrade(self, root):
        from silva.core.references.interfaces import IReferenceService
        installed_ids = root.objectIds()

        # add service_references
        factory = root.manage_addProduct['silva.core.references']

        def install_ref_service():
            factory.manage_addReferenceService('service_references')

        if 'service_references' not in installed_ids:
            install_ref_service()
        elif not IReferenceService.providedBy(root.service_references):
            root.manage_delObjects(['service_references'])
            install_ref_service()

        reg = root.service_view_registry
        reg.unregister('public', 'Silva Ghost')
        reg.unregister('public', 'Silva Ghost Version')
        reg.unregister('preview', 'Silva Ghost Version')

        # remove un-needed Silva Document services
        for service in ['service_editor',
                        'service_editorsupport',
                        'service_old_codesource_charset',
                        'service_widgets',
                        'service_doc_editor',
                        'service_doc_viewer',
                        'service_field_editor',
                        'service_field_viewer',
                        'service_nlist_editor',
                        'service_nlist_viewer',
                        'service_widgets',
                        'service_sub_editor',
                        'service_sub_viewer',
                        'service_news_sub_viewer',
                        'service_news_sub_editor',
                        'service_table_editor',
                        'service_table_viewer']:
            try:
                root.manage_delObjects([service])
            except:
                logger.warn("failed to remove %s" % service)
        transaction.commit()
        return root


root_upgrader = RootUpgrader(VERSION_A1, 'Silva Root')


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


def resolve_path(url, version_path, context, obj_type=u'link'):
    """Resolve path to an object or report an error.
    """
    scheme, netloc, path, parameters, query, fragment = urlparse(url)
    if scheme:
        # This is a remote URL
        logger.debug(u'found a remote link %s' % url)
        return None, None
    if not path:
        # This is to an anchor in the document, nothing else
        return None, fragment
    try:
        target = context.model.unrestrictedTraverse(split_path(path))
    except (AttributeError, KeyError, NotFound):
        logger.error(u'broken %s %s in %s' % (obj_type, url, version_path))
        return None, fragment
    if not ISilvaObject.providedBy(target):
        logger.error(
            u'link %s did not resolve to a Silva content in %s' % (
                path, version_path))
        return None, fragment
    return target, fragment


class DocumentUpgrader(BaseUpgrader):
    """We rewrite here document links and images in order to use
    references where ever it is possible.
    """

    def upgrade(self, obj):
        for version in obj.objectValues():
            if IDocumentVersion.providedBy(version):
                logger.info('will upgrade content on version %s' %
                    "/".join(version.getPhysicalPath()))
                context = Context(version, None)
                dom = version.content.documentElement
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
            # Look for object
            target, fragment = resolve_path(path, version_path, context)
            if fragment:
                link.setAttribute('anchor', fragment)
                link.removeAttribute('url')
            if target is None:
                continue
            build_reference(context, target, link)
            if not fragment:
                link.removeAttribute('url')

    def __upgrade_images(self, version, context, dom):
        images = dom.getElementsByTagName('image')
        version_path = content_path(version)

        def make_link(image, target, title='', window_target='', fragment=''):
            """Create a link, replace the image with it and set the
            image as child of the link.
            """
            link = dom.createElement('link')
            if not isinstance(target, unicode):
                build_reference(context, target, link)
            else:
                link.setAttribute('url', target)
            if fragment:
                link.setAttribute('anchor', fragment)
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
            target, fragment = resolve_path(
                path, version_path, context, 'image')
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
                    link_target, fragment = resolve_path(
                        link, version_path, context)
                    if link_target is not None:
                        make_link(
                            image, link_target, title, window_target, fragment)
                    elif fragment:
                        make_link(image, '', title, window_target, fragment)
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


class ArticleUpgrader(BaseUpgrader):

    def upgrade(self, obj):
        for version in obj.objectValues():
            if IDocumentVersion.providedBy(version):
                logger.info('upgrade xmlattribute for %s' %
                    "/".join(version.getPhysicalPath()))
                parsed_xml = version.content._content
                version.content = parsed_xml
        return obj


class GhostUpgrader(BaseUpgrader):

    def upgrade(self, obj):
        if hasattr(obj, '_content_path'):
            target_path = obj._content_path
            if target_path:
                target = obj.get_root().unrestrictedTraverse(
                    target_path, None)
                if target:
                    logger.info('upgrade reference object for Ghost @%s' %
                        "/".join(obj.getPhysicalPath))
                    obj.set_haunted(target)
                else:
                    logger.warn(
                        'Ghost at %s point to a non existing object at %s' %
                        "/".join(obj.getPhysicalPath()),
                        "/".join(target_path))
            del obj._content_path


document_upgrader = DocumentUpgrader(VERSION_A1, 'Silva Document')

article_upgrader_agenda = \
    ArticleUpgrader(VERSION_A1, 'Silva Agenda Item', 100)
article_upgrader_article = \
    ArticleUpgrader(VERSION_A1, 'Silva Article', 100)

document_upgrader_agenda = \
    DocumentUpgrader(VERSION_A1, "Silva Agenda Item", 101)
document_upgrader_article = \
    DocumentUpgrader(VERSION_A1, "Silva Article", 101)

ghost_upgrader = GhostUpgrader(VERSION_A1, ["Silva Ghost", "Silva Ghost Folder"])
indexer_upgrader = UpdateIndexerUpgrader(VERSION_A1, "Silva Indexer")
