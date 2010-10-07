# Copyright (c) 2002-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

import atexit
import logging
import optparse
import os.path
import sys

from AccessControl.SecurityManagement import newSecurityManager
from Testing.makerequest import makerequest
from infrae.wsgi.paster import boot_zope
from silva.core.interfaces import IRoot
from silva.core.upgrade.upgrade import registry
from zope.location.interfaces import ISite
from zope.security.management import newInteraction
from zope.site.hooks import setSite, setHooks
import AccessControl.User
import Zope2

logger = logging.getLogger('silva.core.upgrade')

parser = optparse.OptionParser(
    description="Upgrade a Silva site to the lastest version.")
parser.add_option(
    "-c", "--config",
    help="load zope config")
parser.add_option(
    "--from-version", dest="version",
    help="start upgrade from the given version")
parser.add_option(
    "--list", action="store_true", dest="list",
    help="list all available Silva at the root of the database "
    "and their versions"),
parser.add_option(
    "--pack", action="store_true", dest="pack",
    help="pack database after the upgrade")


def upgrade():
    options, args = parser.parse_args()

    if options.config is None or not os.path.isfile(options.config):
        sys.stderr.write("use --config to specify zope configuration")
        sys.exit(1)

    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler(sys.stdout))

    boot_zope(options.config)

    newInteraction()
    newSecurityManager(None, AccessControl.User.system)
    Zope2.zpublisher_transactions_manager.begin()
    root = makerequest(Zope2.bobo_application())

    def close():
        logger.info("Closing database.")
        Zope2.DB.close()

    atexit.register(close)

    if options.list:
        logger.info('Silva Root at the root of the database:')
        for content_id, content in root.objectItems():
            if IRoot.providedBy(content):
                logger.info('- /%s: version %s' % (
                        content_id, content.get_silva_content_version()))
        sys.exit(0)

    if not len(args):
        sys.stderr.write("Please give paths to Silva Root as arguments.")
        sys.exit(1)

    for silva_path in args:
        silva = root.unrestrictedTraverse(silva_path)
        if not IRoot.providedBy(silva):
            sys.stderr.write("%s is not a valid Silva Root." % silva_path)
            sys.exit(1)
        if ISite.providedBy(silva):
            setSite(silva)
        else:
            setSite(None)
        setHooks()
        from_version = options.version
        if not from_version:
            from_version = silva.get_silva_content_version()
        to_version = silva.get_silva_software_version()
        logger.info("upgrade from version %s to version %s" % (
                from_version, to_version))
        registry.upgrade(silva, from_version, to_version)
        silva._content_version = to_version

    Zope2.zpublisher_transactions_manager.commit()
    if options.pack:
        logger.info("packing database...")
        Zope2.DB.pack()

    sys.exit(0)
