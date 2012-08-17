# -*- coding: utf-8 -*-
# Copyright (c) 2002-2012 Infrae. All rights reserved.
# See also LICENSE.txt

from silva.system.utils.script import NEED_SILVA_SESSION
from silva.core.upgrade.upgrade import registry
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
            "--from-version", dest="version",
            help="start upgrade from the given version")
        parser.add_argument(
            "-u", "--username",
            help="username to use for the upgrade")
        parser.add_argument(
            "paths", nargs="+",
            help="path to Silva sites to work on")
        parser.set_defaults(plugin=self)

    def run(self, root, options):
        from_version = options.version
        if not from_version:
            from_version = root.get_silva_content_version()
        to_version = root.get_silva_software_version()
        logger.info("upgrade from version %s to version %s" % (
                from_version, to_version))
        registry.upgrade(root, from_version, to_version)
        root._content_version = to_version
        transaction.commit()
