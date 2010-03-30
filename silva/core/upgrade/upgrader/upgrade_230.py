# Copyright (c) 2002-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

from Products.SilvaDocument.interfaces import IDocumentVersion
from Products.SilvaDocument.transform.base import Context
from zExceptions import NotFound

from silva.core.upgrade.upgrade import BaseUpgrader, AnyMetaType, content_path

from urlparse import urlparse


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

        return root


RootUpgrader = RootUpgrader(VERSION_A1, 'Silva Root')


class DocumentUpgrader(BaseUpgrader):

    def upgrade(self, obj):
        for version in obj.objectValues():
            if IDocumentVersion.providedBy(version):
                context = Context(version, None)
                dom = version._get_document_element()
                self.__upgrade_links(version, context, dom)
                self.__upgrade_images(version, context, dom)
        return obj

    def __upgrade_links(version, context, dom):
        links = dom.getElementsByTabName('link')
        version_path = content_path(version)
        if links:
            logger.info('upgrading links in: %s', version_path)
        for link in links:
            path = link.getAttribute('url')
            if not urlparse(unicode(path))[0]:
                # Look for object
                try:
                    target = context.model.unrestrictedTraverse(path)
                except (AttributeError, KeyError, NotFound):
                    logger.error('broken link %s in %s' % (path, version_path))
                    continue
                reference_name, reference = context.new_reference()
                reference.set_target(target)
                link.setAttribute('reference', reference_name)
                link.removeAttribute('url')

    def __upgrade_images(version, context, dom):
        pass


DocumentUpgrader = DocumentUpgrader(VERSION_A1, 'Silva Document')
