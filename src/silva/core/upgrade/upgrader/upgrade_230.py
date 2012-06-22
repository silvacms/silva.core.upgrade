# Copyright (c) 2002-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

from urlparse import urlparse
import logging

from zope.event import notify
from zope.lifecycleevent import ObjectCreatedEvent

from Acquisition import aq_base
from zExceptions import NotFound
from five.intid.site import aq_iter

from Products.Silva.ExtensionRegistry import extensionRegistry

from silva.core.interfaces import ISilvaObject, IVersionedContent
from silva.core.references.interfaces import IReferenceService
from silva.core.services.interfaces import IContainerPolicyService
from silva.core.services.interfaces import IMemberService
from silva.core.upgrade.upgrade import BaseUpgrader, content_path
#from silva.core.upgrade.upgrader.upgrade_220 import UpdateIndexerUpgrader

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
            factory.manage_addReferenceService('service_references')

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
    scheme, netloc, path, parameters, query, fragment = urlparse(url)
    if scheme:
        # This is a remote URL
        logger.debug(u'found a remote link %s' % url)
        return None, None
    if not path:
        # This is to an anchor in the document, nothing else
        return None, fragment
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
            logger.error(u'broken %s %s in %s' % (obj_type, url, content_path))
            return None, fragment
    if not ISilvaObject.providedBy(target):
        logger.error(
            u'%s %s did not resolve to a Silva content in %s' % (
                obj_type, path, content_path))
        return None, fragment
    try:
        [o for o in aq_iter(target, error=RuntimeError)]
        return target, fragment
    except RuntimeError:
        logger.error(u'invalid target %s %s in %s' %(
                obj_type, path, content_path))
        return None, fragment


class GhostUpgrader(BaseUpgrader):

    def validate(self, obj):
        return hasattr(obj, '_content_path')

    def upgrade(self, obj):
        target_path = obj._content_path
        if target_path:
            target = obj.get_root().unrestrictedTraverse(
                target_path, None)
            if target is not None:
                logger.info('upgrade reference object for Ghost @%s' %
                            "/".join(obj.getPhysicalPath()))
                obj.set_haunted(target)
            else:
                logger.warn(
                    'Ghost at %s point to a non existing object at %s' %
                    ("/".join(obj.getPhysicalPath()), target_path,))
            del obj._content_path
        return obj


class VersionedContentUpgrader(BaseUpgrader):
    """Remove cache_data from versioned content as this is not used anymore.
    """

    def validate(self, obj):
        return IVersionedContent.providedBy(obj)

    def upgrade(self, obj):
        if hasattr(aq_base(obj), '_cached_checked'):
            del obj._cached_checked
        if hasattr(aq_base(obj), '_cached_data'):
            del obj._cached_data
        return obj


class LinkVersionUpgrader(BaseUpgrader):
    """ replace relative links with references
    """

    def validate(self, version):
        return (not version.__dict__.has_key('_relative') and
                not self.__is_absolute_url(version._url))

    def upgrade(self, version):
        link_path = content_path(version)
        target, fragment = resolve_path(
            version._url, link_path, version.get_container())

        if target:
            logger.info('upgrade link %s' % link_path)
            version.set_relative(True)
            version.set_target(target)
            version._url = u''
        else:
            logger.warn('cannot find target for link %s to %s' %
                        (link_path, version._url,))
        return version

    def __is_absolute_url(self, url):
        purl = urlparse(url)
        return bool(purl.netloc)


link_upgrader = LinkVersionUpgrader(VERSION_B1, 'Silva Link Version')

cache_upgrader = VersionedContentUpgrader(
    VERSION_B1, ['Silva Ghost', 'Silva Link'])
ghost_upgrader = GhostUpgrader(
    VERSION_B1, ["Silva Ghost Version", "Silva Ghost Folder"])
#indexer_upgrader = UpdateIndexerUpgrader(
#    VERSION_B1, "Silva Indexer")


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
            if extensionRegistry.have('silva.pas.base'):
                root.service_extensions.install('silva.pas.base')
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
        if hasattr(root, 'service_subscriptions'):
            from silva.app.subscriptions.interfaces import ISubscriptionService
            sm.registerUtility(
                root.service_subscriptions, ISubscriptionService)
            template_ids = root.service_subscriptions.objectIds()
            root.service_subscriptions.manage_delObjects(template_ids)
            # This trigger a reconfiguration of the service.
            notify(ObjectCreatedEvent(root.service_subscriptions))
        if hasattr(root, 'service_news'):
            from Products.SilvaNews.interfaces import IServiceNews
            sm.registerUtility(
                root.service_news, IServiceNews)
        if not hasattr(root, 'service_secret'):
            factory = root.manage_addProduct['silva.core.services']
            factory.manage_addSecretService()
        if hasattr(root, 'service_subscriptions_mailhost'):
            root.manage_renameObject(
                'service_subscriptions_mailhost',
                'service_mailhost')
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

