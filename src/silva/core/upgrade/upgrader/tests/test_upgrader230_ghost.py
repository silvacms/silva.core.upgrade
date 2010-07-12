# Copyright (c) 2009-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

import unittest

from Acquisition import aq_chain

from Products.Silva.testing import FunctionalLayer
from silva.core.upgrade.upgrader.upgrade_230 import ghost_upgrader
from silva.core.references.interfaces import IReferenceService
from zope.component import getUtility


class GhostUpgraderTestCase(unittest.TestCase):
    """Test upgrader which rewrites links and images to use
    references.
    """
    layer = FunctionalLayer

    def setUp(self):
        self.root = self.layer.get_application()
        self.layer.login('editor')
        factory = self.root.manage_addProduct['Silva']
        factory.manage_addPublication('pub', 'Publication')
        factory.manage_addGhostFolder('ghost_folder', 'Ghost Folder')

        factory = self.root.manage_addProduct['SilvaDocument']
        factory.manage_addDocument('doc', 'Document')
        factory = self.root.pub.manage_addProduct['Silva']
        factory.manage_addGhost('ghost', 'Ghost of Document')

        self.ghost = self.root.pub.ghost
        self.ghost_version = self.ghost.getLastVersion()
        self.ghost_version._content_path = ('', 'root', 'doc')

        self.ghost_folder = self.root.ghost_folder
        self.ghost_folder._content_path = ('', 'root', 'pub')

    def test_upgrade_ghost(self):
        self.assertTrue(ghost_upgrader.validate(self.ghost_version))
        ghost_upgrader.upgrade(self.ghost_version)

        self.assertFalse(ghost_upgrader.validate(self.ghost_version))
        self.assertEquals(
            self.root.doc,
            self.ghost_version.get_haunted())
        self.assertEquals(
            aq_chain(self.root.doc),
            aq_chain(self.ghost_version.get_haunted()))

        service = getUtility(IReferenceService)
        reference = service.get_reference(self.ghost_version, name=u"haunted")
        self.assertEquals(
            aq_chain(reference.source),
            aq_chain(self.ghost_version))

    def test_upgrade_ghost_folder(self):
        self.assertTrue(ghost_upgrader.validate(self.ghost_folder))
        ghost_upgrader.upgrade(self.ghost_folder)

        self.assertFalse(ghost_upgrader.validate(self.ghost_folder))
        self.assertEquals(
            self.root.pub,
            self.ghost_folder.get_haunted())
        self.assertEquals(
            aq_chain(self.root.pub),
            aq_chain(self.ghost_folder.get_haunted()))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(GhostUpgraderTestCase))
    return suite
