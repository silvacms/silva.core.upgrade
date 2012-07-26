# Copyright (c) 2002-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

# Python
from bisect import insort_right
from pkg_resources import parse_version
import tempfile
import logging
import datetime
import gc
import copy

logger = logging.getLogger('silva.core.upgrade')

# Zope
from five import grok
from Acquisition import aq_base
from OFS.interfaces import IFolder
from ZODB.broken import Broken
from zope.interface import providedBy, alsoProvides
from zope.annotation.interfaces import IAnnotations
from zope.component import getUtility
from zope.event import notify
import transaction

# Silva
from Products.Silva.Membership import NoneMember
from silva.core.interfaces import ISecurity, IPostUpgrader
from silva.core.interfaces import IUpgrader, IUpgradeRegistry, IRoot
from silva.core.interfaces.events import UpgradeFinishedEvent
from silva.core.interfaces.events import UpgradeStartedEvent
from silva.core.interfaces.events import UpgradeTransaction, IUpgradeTransaction
from silva.core.references.interfaces import IReferenceService
from silva.core.views.interfaces import ICustomizableTag

THRESHOLD = 2000

# marker for upgraders to be called for any object
AnyMetaType = object()

def content_path(content):
    return '/'.join(content.getPhysicalPath())


class BaseUpgrader(object):
    """All upgrader should inherit from this upgrader.
    """
    grok.implements(IUpgrader)
    grok.baseclass()

    def __init__(self, version, meta_type, priority=0):
        """Create an instance of this upgrader for the given meta_type
        to upgrade to the given version. If more than one upgrader is
        defined for the same meta_type to the same version, the one
        with the smallest priority would be run first.
        """
        self.version = version
        self.meta_type = meta_type
        self.priority = priority

    def replace(self, old_obj, new_obj):
        """Helper that help to replace a Silva object by a different one.
        """
        # Copy annotations (metadata)
        source_annotations = IAnnotations(old_obj)
        target_annotations = IAnnotations(new_obj)
        for key in source_annotations.keys():
            target_annotations[key] = copy.deepcopy(source_annotations[key])
        if ISecurity.providedBy(old_obj):
            # Copy last author information
            user = aq_base(old_obj.sec_get_last_author_info())
            if not isinstance(user, NoneMember):
                new_obj._last_author_userid = user.id
                new_obj._last_author_info = user
        # Copy customization markers
        for iface in providedBy(old_obj).interfaces():
            if iface.extends(ICustomizableTag):
                alsoProvides(new_obj, iface)
        # Copy creator information
        owner = getattr(aq_base(old_obj), '_owner', None)
        if owner is not None:
            new_obj._owner = owner

    def replace_references(self, old_obj, new_obj):
        """Helper that help to replace a referenced Silva object by a
        different one.
        """
        service = getUtility(IReferenceService)
        # list are here required. You cannot iterator and change the
        # result at the same time, as they won't appear in the result any
        # more and move eveything. :)
        for reference in list(service.get_references_to(old_obj)):
            reference.set_target(new_obj)
        for reference in list(service.get_references_from(old_obj)):
            reference.set_source(new_obj)

    def validate(self, obj):
        return True

    def upgrade(self, obj):
        raise NotImplementedError

    def __cmp__(self, other):
        sort = cmp(self.priority, other.priority)
        if sort == 0:
            sort = cmp(self.__class__.__name__,
                       other.__class__.__name__)
        return sort


def convert_dev(version):
    if 'dev' in version:
        return version.replace('dev', '**dev')
    return version


def get_version_index(version_list, wanted_version):
    """Return the index of the version in the list.
    """
    wanted_version = parse_version(convert_dev(wanted_version))
    for index, version in enumerate(version_list):
        parsed_version = parse_version(version)
        if wanted_version < parsed_version:
            return index
        elif wanted_version == parsed_version:
            return index + 1
    # Version outside of scope, return the last upgrader.
    return index + 1


def get_upgrade_chain(versions, from_version, to_version):
    """Return a list of version to upgrade to when upgrading from to
    to version.
    """
    from_version = convert_dev(from_version)
    to_version = convert_dev(to_version)
    versions.sort(lambda x, y: cmp(parse_version(x), parse_version(y)))
    version_start_index = get_version_index(versions, from_version)
    version_end_index = get_version_index(versions, to_version)
    return versions[version_start_index:version_end_index]


class UpgradeProcess(object):

    def __init__(self, registry, versions):
        self.versions = versions
        self.registry = registry
        self._count = 0
        self._post = []
        self._upgraders = {}
        notify(UpgradeTransaction())

    def get_upgraders(self, content):
        if content.meta_type not in self._upgraders:
            self._upgraders[content.meta_type] = self.registry.get_upgraders(
                self.versions, content.meta_type)
        return self._upgraders[content.meta_type]

    def notify_upgraded(self, content):
        self._count += 1
        if self._count > THRESHOLD:
            transaction.commit()
            notify(UpgradeTransaction())
            if (hasattr(aq_base(content), '_p_jar') and
                content._p_jar is not None):
                # Cache minimize kill the ZODB cache
                # that is just resized at the end of the request
                # normally as well.
                content._p_jar.cacheMinimize()
                self._count = 0

    def upgrade_content(self, content):
        post = []
        for upgrader in self.get_upgraders(content):
            __traceback_supplement__ = (UpgraderTraceback, content, upgrader)
            try:
                if upgrader.validate(content):
                    if IPostUpgrader.providedBy(upgrader):
                        post.append((content, upgrader))
                    else:
                        result = upgrader.upgrade(content)
                        assert result is not None
                        self.notify_upgraded(result)
                        if result.meta_type != content.meta_type:
                            # Object replaced, abort, return new object
                            return result
                        content = result
            except ValueError as error:
                logger.error(
                    u'Error while upgrading object %s with %r: %s',
                    content_path(content), upgrader, str(error))
        if post:
            self._post.extend(post)
        return content

    def upgrade_container(self, root, blacklist=[]):
        notify(UpgradeTransaction())
        contents = [root]
        while contents:
            iterate = True
            content = contents.pop()

            if isinstance(content, Broken):
                # We don't upgrade broken objects. They should be
                # removed by their contains if needed.
                continue

            if content.meta_type not in blacklist:
                try:
                    content = self.upgrade_content(content)
                except StopIteration:
                    iterate = False

            if (iterate and
                IFolder.providedBy(content) and
                content.meta_type != "Parsed XML"):
                contents.extend(content.objectValues())

    def post_upgrade(self):
        for content, upgrader in self._post:
            __traceback_supplement__ = (UpgraderTraceback, content, upgrader)
            try:
                result = upgrader.upgrade(content)
                assert result is not None
                self.notify_upgraded(result)
                if result.meta_type != content.meta_type:
                    # Object replaced, abort upgraders.
                    break
                content = result
            except ValueError as error:
                logger.error(
                    u'Error while upgrading object %s with %r: %s',
                    content_path(content), upgrader, str(error))
        self._post = []


class UpgradeRegistry(object):
    """Here people can register upgrade methods for their objects
    """
    grok.implements(IUpgradeRegistry)

    def __init__(self):
        self.__registry = {}
        self.__in_process = False

    def register(self, upgrader, version=None, meta_type=None):
        assert IUpgrader.providedBy(upgrader)
        if not version:
            version = upgrader.version
        if not meta_type:
            meta_type = upgrader.meta_type
        if isinstance(meta_type, str) or meta_type is AnyMetaType:
            meta_type = [meta_type,]
        for type_ in meta_type:
            registry = self.__registry.setdefault(version, {}).setdefault(
                type_, [])
            insort_right(registry, upgrader)

    def get_upgraders(self, versions, meta_type):
        """Return the registered upgrade_handlers of meta_type
        """
        if isinstance(versions, str):
            versions = [versions,]
        upgraders = []
        for version in versions:
            v_mt = self.__registry.get(version, {})
            upgraders.extend(v_mt.get(AnyMetaType, []))
            upgraders.extend(v_mt.get(meta_type, []))
        return upgraders

    def upgrade_tree(self, root, version, blacklist=[]):
        logger.info(
            u'Upgrading container %s to %s.', content_path(root), version)
        start = datetime.datetime.now()
        notify(UpgradeStartedEvent(root, 'n/a', version))
        process = UpgradeProcess(self, [version])
        try:
            process.upgrade_container(root, blacklist=blacklist)
            process.post_upgrade()
        except:
            notify(UpgradeFinishedEvent(root, 'n/a', version, False))
            raise
        else:
            end = datetime.datetime.now()
            notify(UpgradeFinishedEvent(root, 'n/a', version, True))
            logger.info(
                u'Upgrade finished in %d seconds.', (end - start).seconds)

    def upgrade(self, root, from_version, to_version):
        """Upgrade a root object from the from_version to the
        to_version.
        """
        if self.__in_process is True:
            raise ValueError(u"An upgrade process is already going on")
        log_stream = tempfile.NamedTemporaryFile()
        log_handler = logging.StreamHandler(log_stream)
        logger.addHandler(log_handler)
        try:
            logger.info(
                u'Upgrading from %s to %s.', from_version, to_version)
            notify(UpgradeStartedEvent(root, from_version, to_version))

            start = datetime.datetime.now()
            end = None
            versions = get_upgrade_chain(
                self.__registry.keys(), from_version, to_version)
            if not versions:
                logger.info(u'Nothing needs to be done.')
            process = UpgradeProcess(self, versions)

            if IRoot.providedBy(root):
                # First, upgrade Silva Root so Silva services /
                # extensions will be upgraded
                logger.info(
                    u'Upgrading root to versions %s.',
                    ', '.join(versions))
                process.upgrade_content(root)
                transaction.commit()

            # Now, upgrade site content
            logger.info(u'Upgrading content to version %s.', ', '.join(versions))
            process.upgrade_container(root, blacklist=['Silva Root',])
            process.post_upgrade()

            end = datetime.datetime.now()
            logger.info(
                u'Upgrade finished in %d seconds.', (end - start).seconds)
        finally:
            logger.removeHandler(log_handler)
            self.__in_process = False
        notify(UpgradeFinishedEvent(root, from_version, to_version, end is not None))
        log_stream.seek(0, 0)
        return log_stream


registry = UpgradeRegistry()


class UpgraderTraceback(object):
    """Implementation of zope.exceptions.ITracebackSupplement,
    to amend the traceback during upgrades so that object
    information is present.
    """

    def __init__(self, context, content, upgrader):
        self.context = context
        self.content = content
        self.upgrader = upgrader

    def getInfo(self, as_html=0):
        import pprint
        data = {"content": self.content,
                "content_path": content_path(self.content),
                "upgrader": self.upgrader}
        s = pprint.pformat(data)
        if not as_html:
            return '   - Content Info:\n      %s' % s.replace('\n', '\n      ')
        else:
            from cgi import escape
            return '<b>Names:</b><pre>%s</pre>'%(escape(s))


@grok.subscribe(IUpgradeTransaction)
def garbage_collect(event):
    gc.collect()
