# Copyright (c) 2002-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

from urlparse import urlparse
import logging

from zope.event import notify
from zope.lifecycleevent import ObjectCreatedEvent

from Acquisition import aq_base, aq_parent
from zExceptions import NotFound
from five.intid.site import aq_iter

from Products.Silva.ExtensionRegistry import extensionRegistry

from silva.core.interfaces import ISilvaObject, IVersionedContent, IGhostFolder
from silva.core.references.interfaces import IReferenceService
from silva.core.services.interfaces import IContainerPolicyService
from silva.core.services.interfaces import IMemberService
from silva.core.upgrade.upgrade import BaseUpgrader, content_path

logger = logging.getLogger('silva.core.upgrade')


#-----------------------------------------------------------------------------
# 2.2.0 to 2.3.0b1
#-----------------------------------------------------------------------------

VERSION_B1='2.3b1'
VERSION_B2='2.3b2'
VERSION_FINAL='2.3'


class RootUpgrader(BaseUpgrader):

    def upgrade(self, root):
        installed_ids = root.objectIds()

        # add service_references
        factory = root.manage_addProduct['silva.core.references']

        def install_ref_service():
            from silva.core.references.service import configure_service

            factory.manage_addReferenceService('service_references')
            configure_service(root.service_references)

        if 'service_references' not in installed_ids:
            install_ref_service()
        elif not IReferenceService.providedBy(root.service_references):
            root.manage_delObjects(['service_references'])
            install_ref_service()

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
                logger.warn(u"failed to remove %s", service)
        return root


root_upgrader = RootUpgrader(VERSION_B1, 'Silva Root')


def split_path(path, context, root=None):
    """Split path, remove . components, be sure there is enough parts
    in the context path to get all .. working.
    """
    if root is None:
        root = context.getPhysicalRoot()
    parts = path.split('/')
    if len(parts) and not parts[0]:
        context = root
    parts = filter(lambda x: x != '', parts)
    context_parts = filter(lambda x: x != '', list(context.getPhysicalPath()))
    root_parts = filter(lambda x: x != '', list(root.getPhysicalPath()))
    assert len(context_parts) >= len(root_parts)
    if len(root_parts):
        context_parts = context_parts[len(root_parts):]
    while parts:
        if parts[0] == '.':
            parts = parts[1:]
        elif parts[0] == '..':
            if len(context_parts):
                context_parts = context_parts[:-1]
                parts = parts[1:]
            else:
                raise KeyError(path)
        else:
            break
    return context_parts + parts, root


def resolve_path(url, content_path, context, obj_type=u'link'):
    """Resolve path to an object or report an error.
    """
    if isinstance(url, unicode):
        # If the link contains unicode, that is not a link.
        try:
            url.encode('ascii')
        except UnicodeEncodeError:
            logger.error(u"Invalid %s '%s' (contains unicode).", obj_type, url)
            return url, None, None
    url = url.strip()
    scheme, netloc, path, parameters, query, fragment = urlparse(url)
    if scheme:
        # This is a remote URL
        #logger.debug(u'Found a remote link %s' % url)
        return url, None, None
    if not path:
        # This is to an anchor in the document, nothing else
        return url, None, fragment
    try:
        cleaned_path, path_root = split_path(path, context)
        target = path_root.unrestrictedTraverse(cleaned_path)
    except (AttributeError, KeyError, NotFound, TypeError):
        # Try again using Silva Root as /
        try:
            cleaned_path, path_root = split_path(
                path, context, context.get_root())
            target = path_root.unrestrictedTraverse(cleaned_path)
        except (AttributeError, KeyError, NotFound, TypeError):
            logger.debug(
                u'Cannot resolve %s %s in %s',
                obj_type, url, content_path)
            return url, None, fragment
    if not ISilvaObject.providedBy(target):
        logger.error(
            u'%s %s did not resolve to a Silva content in %s',
            obj_type, path, content_path)
        return url, None, fragment
    try:
        [o for o in aq_iter(target, error=RuntimeError)]
        return url, target, fragment
    except RuntimeError:
        logger.error(
            u'Invalid target %s %s in %s',
            obj_type, path, content_path)
        return url, None, fragment


class GhostUpgrader(BaseUpgrader):

    def validate(self, ghost):
        return hasattr(ghost, '_content_path')

    def upgrade(self, ghost):
        target_path = ghost._content_path
        if target_path:
            try:
                target = ghost.get_root().unrestrictedTraverse(target_path)
            except (AttributeError, KeyError, NotFound, TypeError):
                logger.error(
                    u'Unexisting target for Ghost %s: %s.',
                    content_path(ghost), "/".join(target_path))
                return ghost
            try:
                [o for o in aq_iter(target, error=RuntimeError)]
            except RuntimeError:
                logger.error(
                    u'Invalid target for Ghost %s: %s.',
                    content_path(ghost), '/'.join(target_path))
                return ghost
            if not ISilvaObject.providedBy(target):
                logger.error(
                    u'Ghost target is not a Silva object for: %s.',
                    content_path(ghost))
                return ghost
            if target is not None and ISilvaObject.providedBy(target):
                logger.info(
                    u'Upgrading Ghost target for: %s.',
                    "/".join(ghost.getPhysicalPath()))
                container = aq_parent(ghost).get_container()
                ghost.set_haunted(
                    target,
                    auto_delete=IGhostFolder.providedBy(container))
            del ghost._content_path
        return ghost


class VersionedContentUpgrader(BaseUpgrader):
    """Remove cache_data from versioned content as this is not used anymore.
    """

    def validate(self, content):
        return (IVersionedContent.providedBy(content) and
                ('_cached_checked' in content.__dict__ or
                 '_cached_data' in content.__dict__))

    def upgrade(self, content):
        if '_cached_checked' in content.__dict__:
            del content._cached_checked
        if '_cached_data' in content.__dict__:
            del content._cached_data
        return content


class LinkVersionUpgrader(BaseUpgrader):
    """ replace relative links with references
    """

    def validate(self, version):
        return (not version.__dict__.has_key('_relative') and
                not self._is_absolute_url(version._url))

    def upgrade(self, version):
        link_path = content_path(version)
        url, target, fragment = resolve_path(
            version._url, link_path, version.get_container())

        if target:
            logger.info(u'Upgrade link %s.', link_path)
            version.set_relative(True)
            version.set_target(target)
            version._url = u''
        else:
            version._url = url
        return version

    def _is_absolute_url(self, url):
        return bool(urlparse(url.strip()).netloc)


link_upgrader = LinkVersionUpgrader(VERSION_B1, 'Silva Link Version')

cache_upgrader = VersionedContentUpgrader(
    VERSION_B1, ['Silva Ghost', 'Silva Link'])
ghost_upgrader = GhostUpgrader(
    VERSION_B1, ["Silva Ghost Version", "Silva Ghost Folder"])


class SecondRootUpgrader(BaseUpgrader):

    def upgrade(self, root):
        # Convert Members folder
        root.manage_renameObject('Members', 'OldMembers')
        root.manage_addProduct['BTreeFolder2'].manage_addBTreeFolder('Members')
        for identifier, member in root.OldMembers.objectItems():
            if identifier not in root.Members.objectIds():
                root.Members._setObject(identifier, aq_base(member))
        root.manage_delObjects(['OldMembers'])

        # Register services
        sm = root.getSiteManager()
        if not IMemberService.providedBy(root.service_members):
            root.manage_delObjects(['service_members'])
            if extensionRegistry.get_extension('silva.pas.base') is not None:
                from silva.pas.base.subscribers import configure_service

                factory = root.manage_addProduct['silva.pas.base']
                factory.manage_addMemberService()
                configure_service(root, None)
            else:
                factory = root.manage_addProduct['Silva']
                factory.manage_addSimpleMemberService()
        else:
            sm.registerUtility(root.service_members, IMemberService)
        container_policy = root.service_containerpolicy
        if hasattr(aq_base(container_policy), '_policies'):
            container_policy._ContainerPolicyRegistry__policies = dict(
                container_policy._policies)
            delattr(container_policy, '_policies')
        sm.registerUtility(
            root.service_containerpolicy, IContainerPolicyService)
        if root._getOb('service_subscriptions', None) is not None:
            from silva.app.subscriptions.interfaces import ISubscriptionService
            sm.registerUtility(
                root.service_subscriptions, ISubscriptionService)
            template_ids = root.service_subscriptions.objectIds()
            root.service_subscriptions.manage_delObjects(template_ids)
            # This trigger a reconfiguration of the service.
            notify(ObjectCreatedEvent(root.service_subscriptions))
        if root._getOb('service_news', None) is not None:
            from silva.app.news.interfaces import IServiceNews
            sm.registerUtility(root.service_news, IServiceNews)
        if root._getOb('service_find', None) is not None:
            from Products.SilvaFind.interfaces import IFindService
            sm.registerUtility(root.service_find, IFindService)
        if root._getOb('service_secret', None) is None:
            factory = root.manage_addProduct['silva.core.services']
            factory.manage_addSecretService()
        if root._getOb('service_subscriptions_mailhost', None) is not None:
            root.manage_renameObject(
                'service_subscriptions_mailhost',
                'service_mailhost')

        if hasattr(aq_base(root), '__initialization__'):
            delattr(root, '__initialization__')
        return root


class CSVSourceUpgrader(BaseUpgrader):

    def upgrade(self, content):
        from Products.SilvaExternalSources.CSVSource import (
            reset_parameter_form, reset_table_layout)
        reset_parameter_form(content)
        reset_table_layout(content)
        return content


csvsource_upgrader = CSVSourceUpgrader(VERSION_B2, 'Silva CSV Source')
second_root_upgrader = SecondRootUpgrader(VERSION_B2, 'Silva Root')


class ThirdRootUpgrader(BaseUpgrader):

    def upgrade(self, content):
        if '_properties' in content.__dict__:
            del content.__dict__['_properties']
        return content



third_root_upgrarder = ThirdRootUpgrader(VERSION_FINAL, 'Silva Root')

