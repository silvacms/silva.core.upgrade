# -*- coding: utf-8 -*-
# Copyright (c) 2002-2013 Infrae. All rights reserved.
# See also LICENSE.txt

from silva.system.utils.script import NEED_SILVA_SESSION
from silva.core.upgrade.upgrade import registry
from silva.core.interfaces import ISilvaObject, IRoot
import transaction
import logging

logger = logging.getLogger('silva.system')


class UpgradeCommand(object):
    flags = NEED_SILVA_SESSION

    def get_options(self, factory):
        parser = factory(
            'upgrade',
            help='upgrade a site to the latest version')
        parser.add_argument(
            "-u", "--username",
            help="username to use for the upgrade")
        parser.add_argument(
            "--content",
            help="path to a content to upgrade, no child will be upgraded")
        parser.add_argument(
            "--folder",
            help="path to a folder to upgrade, child will be upgraded")
        parser.add_argument(
            "--from-version", dest="version",
            help="start upgrade from the given version")
        parser.add_argument(
            "--require-tags", nargs="+",
            help="list of required tags")
        parser.add_argument(
            "--exclude-tags", nargs="+",
            help="list of exclude tags")
        parser.set_defaults(plugin=self)
        parser.add_argument(
            "paths", nargs="+",
            help="path to Silva sites to work on")

    def run(self, root, options):
        target = root
        target_path = options.folder or options.content
        to_version = root.get_silva_software_version()
        from_version = options.version

        if target_path and not from_version:
            logger.error('You need to provide --from-version '
                         'to upgrade a folder or a content.')
            exit(3)
        if target_path:
            try:
                target = root.unrestrictedTraverse(target_path)
            except (KeyError, AttributeError):
                logger.error('Invalid content path %s.', target_path)
                exit(1)
        if not ISilvaObject.providedBy(target):
            logger.error('Content %s is not a Silva content.', target_path)
            exit(2)
        if not from_version:
            from_version = root.get_silva_content_version()
        logger.info("Upgrade from version %s to version %s." % (
                from_version, to_version))
        if options.content:
            registry.upgrade_content(
                target, from_version, to_version,
                whitelist=options.require_tags,
                blacklist=options.exclude_tags)
        else:
            registry.upgrade(
                target, from_version, to_version,
                whitelist=options.require_tags,
                blacklist=options.exclude_tags)
        if IRoot.providedBy(target):
            target._content_version = to_version
        transaction.commit()
