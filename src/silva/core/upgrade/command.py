# -*- coding: utf-8 -*-
# Copyright (c) 2002-2012 Infrae. All rights reserved.
# See also LICENSE.txt

from silva.system.utils.script import NEED_SILVA_SESSION
from silva.core.upgrade.upgrade import registry
from silva.core.interfaces import IContainer, IRoot
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
            "--subtree", help="path to a subtree to upgrade")
        parser.add_argument(
            "--from-version", dest="version",
            help="start upgrade from the given version")
        parser.add_argument(
            "-u", "--username",
            help="username to use for the upgrade")
        parser.add_argument(
            "paths", nargs="+",
            help="path to Silva sites to work on")
        parser.add_argument(
            "--require-tags", nargs="+",
            help="list of required tags")
        parser.add_argument(
            "--exclude-tags", nargs="+",
            help="list of exclude tags")
        parser.set_defaults(plugin=self)

    def run(self, root, options):
        from_version = options.version
        if options.subtree and not from_version:
            logger.error('you need to provide --from-version '
                'to upgrade a subtree')
            exit(3)
        if not from_version:
            from_version = root.get_silva_content_version()
        to_version = root.get_silva_software_version()
        logger.info("upgrade from version %s to version %s" % (
                from_version, to_version))
        target = root
        if options.subtree:
            try:
                target = root.unrestrictedTraverse(options.subtree)
            except KeyError:
                logger.error('Invalid subtree.')
                exit(1)
        if not IContainer.providedBy(target):
            logger.error('subtree is not a container.')
            exit(2)
        registry.upgrade(target, from_version, to_version,
            whitelist=options.require_tags, blacklist=options.exclude_tags)
        if IRoot.providedBy(target):
            target._content_version = to_version
        transaction.commit()
