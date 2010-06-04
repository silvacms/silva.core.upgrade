# Copyright (c) 2002-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

# Python
from StringIO import StringIO
from bisect import insort_right
from pkg_resources import parse_version
import logging
import datetime

logger = logging.getLogger('silva.core.upgrade')

# Zope
from zope.interface import implements
import transaction

# Silva
from silva.core.interfaces import IUpgrader, IUpgradeRegistry, IRoot

threshold = 50

# marker for upgraders to be called for any object
AnyMetaType = object()

def content_path(content):
    return '/'.join(content.getPhysicalPath())


class BaseUpgrader(object):
    """All upgrader should inherit from this upgrader.
    """
    implements(IUpgrader)

    def __init__(self, version, meta_type, priority=0):
        """Create an instance of this upgrader for the given meta_type
        to upgrade to the given version. If more than one upgrader is
        defined for the same meta_type to the same version, the one
        with the smallest priority would be run first.
        """
        self.version = version
        self.meta_type = meta_type
        self.priority = priority

    def upgrade(self, obj):
        raise NotImplementedError

    def __cmp__(self, other):
        sort = cmp(self.priority, other.priority)
        if sort == 0:
            sort = cmp(self.__class__.__name__,
                       other.__class__.__name__)
        return sort


def get_version_index(version_list, wanted_version):
    """Return the index of the version in the list.
    """
    try:
        dev_index = wanted_version.index('dev')
        wanted_version = wanted_version[:dev_index]
    except ValueError:
        # It's not a development version everything is ok.
        pass
    wanted_version = parse_version(wanted_version)
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
    versions.sort(lambda x, y: cmp(parse_version(x), parse_version(y)))
    version_start_index = get_version_index(versions, from_version)
    version_end_index = get_version_index(versions, to_version)
    return versions[version_start_index:version_end_index]


class UpgradeRegistry(object):
    """Here people can register upgrade methods for their objects
    """

    implements(IUpgradeRegistry)

    def __init__(self):
        self.__registry = {}
        self.__in_process = False

    def registerUpgrader(self, upgrader, version=None, meta_type=None):
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

    def getUpgraders(self, version, meta_type):
        """Return the registered upgrade_handlers of meta_type
        """
        upgraders = []
        v_mt = self.__registry.get(version, {})
        upgraders.extend(v_mt.get(AnyMetaType, []))
        upgraders.extend(v_mt.get(meta_type, []))
        return upgraders

    def upgradeObject(self, obj, version):
        mt = obj.meta_type
        for upgrader in self.getUpgraders(version, mt):
            path = content_path(obj)
            logger.debug('Upgrading %s with %r' % (path, upgrader))

            # sometimes upgrade methods will replace objects, if so
            # the new object should be returned so that can be used
            # for the rest of the upgrade chain instead of the old
            # (probably deleted) one
            __traceback_supplement__ = (
                UpgraderTracebackSupplement, self, obj, upgrader)
            try:
                obj = upgrader.upgrade(obj)
            except ValueError, e:
                logger.error('Error while upgrading object %s with %r: %s' %
                             (path, upgrader, str(e)))
            assert obj is not None, "Upgrader %r seems to be broken, " \
                "this is a bug." % (upgrader, )
        return obj

    def upgradeTree(self, root, version, blacklist=[]):
        stats = {
            'total': 0,
            'threshold': 0,
            'maxqueue' : 0,
            }

        object_list = [root]
        while object_list:
            obj = object_list.pop()

            if not (obj.meta_type in blacklist):
                obj = self.upgradeObject(obj, version)

            if (hasattr(obj.aq_base, 'objectValues') and
                obj.meta_type != "Parsed XML"):

                object_list.extend(obj.objectValues())
                stats['maxqueue'] = max(
                    stats['maxqueue'], len(object_list))

            stats['total'] += 1
            stats['threshold'] += 1
            if stats['threshold'] > threshold:
                transaction.commit()
                if hasattr(obj, '_p_jar') and obj._p_jar is not None:
                    obj._p_jar.cacheGC()
                stats['threshold'] = 0

        return stats

    def upgrade(self, root, from_version, to_version):
        """Upgrade a root object from the from_version to the
        to_version.
        """
        if self.__in_process is True:
            raise ValueError(u"An upgrade process is already going on")
        log_stream = StringIO()
        log_handler = logging.StreamHandler(log_stream)
        logger.addHandler(log_handler)
        try:
            logger.info('upgrading from %s to %s.' %
                        (from_version, to_version))

            start = datetime.datetime.now()
            upgrade_chain = get_upgrade_chain(
                self.__registry.keys(), from_version, to_version)
            if not upgrade_chain:
                logger.info('nothing needs to be done.')

            if IRoot.providedBy(root):
                # First, upgrade Silva Root so Silva services /
                # extensions will be upgraded
                for version in upgrade_chain:
                    logger.info('upgrading root to version %s.' % version)
                    self.upgradeObject(root, version)

            # Now, upgrade site content
            for version in upgrade_chain:
                logger.info('upgrading content to version %s.' % version)
                self.upgradeTree(root, version, blacklist=['Silva Root',])

            if IRoot.providedBy(root):
                # Now, refresh extensions
                logger.info('refresh extensions.')
                root.service_extensions.refresh_all()

            end = datetime.datetime.now()
            logger.info(
                'upgrade finished in %d seconds.' % (end - start).seconds)
        finally:
            logger.removeHandler(log_handler)
            self.__in_process = False
        return log_stream.getvalue()


registry = UpgradeRegistry()


class UpgraderTracebackSupplement(object):
    """Implementation of zope.exceptions.ITracebackSupplement,
    to amend the traceback during upgrades so that object
    information is present.
    """

    def __init__(self, context, obj, upgrader):
        self.context = context
        self.obj = obj
        self.upgrader = upgrader

    def getInfo(self, as_html=0):
        import pprint
        data = {"object": self.obj,
                "object_path": content_path(self.obj),
                "upgrader": self.upgrader}
        s = pprint.pformat(data)
        if not as_html:
            return '   - Object Info:\n      %s' % s.replace('\n', '\n      ')
        else:
            from cgi import escape
            return '<b>Names:</b><pre>%s</pre>'%(escape(s))
