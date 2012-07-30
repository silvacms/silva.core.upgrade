# Copyright (c) 2009-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

import unittest

from Acquisition import aq_chain

from zope.component import getUtility
from zope.interface.verify import verifyObject

from Products.Silva.testing import FunctionalLayer
from silva.core.upgrade.upgrader.upgrade_230 import ghost_upgrader
from silva.core.interfaces import IPublicationWorkflow
from silva.core.references.interfaces import IReferenceService
from silva.core.references.interfaces import IWeakReferenceValue
from silva.core.references.interfaces import IDeleteSourceReferenceValue


class GhostUpgraderTestCase(unittest.TestCase):
    """Test upgrader which rewrites links and images to use
    references.
    """
    layer = FunctionalLayer

    def setUp(self):
        self.root = self.layer.get_application()
        self.layer.login('editor')
        factory = self.root.manage_addProduct['Silva']
        factory.manage_addPublication('publication', 'Publication')
        factory.manage_addGhostFolder('ghost_folder', 'Ghost Folder')
        factory.manage_addMockupVersionedContent('document', 'Document')

        factory = self.root.publication.manage_addProduct['Silva']
        factory.manage_addGhost('ghost', 'Ghost of Document')

        version = self.root.publication.ghost.get_editable()
        version._content_path = ('', 'root', 'document')
        IPublicationWorkflow(self.root.publication.ghost).publish()

        self.root.ghost_folder._content_path = ('', 'root', 'publication')
        factory = self.root.ghost_folder.manage_addProduct['Silva']
        factory.manage_addGhost('ghost', 'Ghost of Document')
        version = self.root.ghost_folder.ghost.get_editable()
        version._content_path = ('', 'root', 'document')
        IPublicationWorkflow(self.root.ghost_folder.ghost).publish()

    def test_upgrade_ghost(self):
        version = self.root.publication.ghost.get_viewable()
        self.assertIsNot(version, None)
        self.assertTrue(ghost_upgrader.validate(version))
        self.assertEqual(ghost_upgrader.upgrade(version), version)

        self.assertFalse(ghost_upgrader.validate(version))
        self.assertEqual(
            version.get_haunted(),
            self.root.document)
        self.assertEquals(
            aq_chain(self.root.document),
            aq_chain(version.get_haunted()))

        service = getUtility(IReferenceService)
        reference = service.get_reference(version, name=u"haunted")
        self.assertTrue(verifyObject(IWeakReferenceValue, reference))
        self.assertEquals(
            aq_chain(reference.source),
            aq_chain(version))

    def test_upgrade_ghost_invalid_path(self):
        version = self.root.publication.ghost.get_viewable()
        self.assertIsNot(version, None)
        version._content_path = ('', 'root', 'root', 'document')
        self.assertTrue(ghost_upgrader.validate(version))
        self.assertEqual(ghost_upgrader.upgrade(version), version)

        # This didn't change anything, but didn't break.
        self.assertTrue(ghost_upgrader.validate(version))
        self.assertEqual(
            version.get_haunted(),
            None)

    def test_upgrade_ghost_unexisting_path(self):
        version = self.root.publication.ghost.get_viewable()
        self.assertIsNot(version, None)
        version._content_path = ('', 'root', 'lala')
        self.assertTrue(ghost_upgrader.validate(version))
        self.assertEqual(ghost_upgrader.upgrade(version), version)

        # This didn't change anything, but didn't break.
        self.assertTrue(ghost_upgrader.validate(version))
        self.assertEqual(
            version.get_haunted(),
            None)

    def test_upgrade_ghost_in_ghost_folder(self):
        version = self.root.ghost_folder.ghost.get_viewable()
        self.assertIsNot(version, None)
        self.assertTrue(ghost_upgrader.validate(version))
        self.assertEqual(ghost_upgrader.upgrade(version), version)

        self.assertFalse(ghost_upgrader.validate(version))
        self.assertEqual(
            self.root.document,
            version.get_haunted())
        self.assertEquals(
            aq_chain(self.root.document),
            aq_chain(version.get_haunted()))

        service = getUtility(IReferenceService)
        reference = service.get_reference(version, name=u"haunted")
        self.assertTrue(verifyObject(IDeleteSourceReferenceValue, reference))
        self.assertEquals(
            aq_chain(reference.source),
            aq_chain(version))

    def test_upgrade_ghost_folder(self):
        folder = self.root.ghost_folder
        self.assertTrue(ghost_upgrader.validate(folder))
        self.assertEqual(ghost_upgrader.upgrade(folder), folder)

        self.assertFalse(ghost_upgrader.validate(folder))
        self.assertEquals(
            self.root.publication,
            folder.get_haunted())
        self.assertEquals(
            aq_chain(self.root.publication),
            aq_chain(folder.get_haunted()))

        service = getUtility(IReferenceService)
        reference = service.get_reference(folder, name=u"haunted")
        self.assertTrue(verifyObject(IWeakReferenceValue, reference))
        self.assertEquals(
            aq_chain(reference.source),
            aq_chain(folder))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(GhostUpgraderTestCase))
    return suite
