# -*- coding: utf-8 -*-
# Copyright (c) 2013 Infrae. All rights reserved.
# See also LICENSE.txt

import unittest

from zope.interface.verify import verifyObject

from Products.Silva.testing import FunctionalLayer
from silva.core.interfaces import IBlobFile, IFile, IGhostAsset
from silva.core.upgrade.upgrader.upgrade_236 import file_upgrader


class FileUpgraderTestCase(unittest.TestCase):
    layer = FunctionalLayer

    def setUp(self):
        self.root = self.layer.get_application()
        self.layer.login('manager')

    def test_file(self):
        factory = self.root.manage_addProduct['Silva']
        with self.layer.open_fixture('silva.png') as data:
            factory.manage_addFile('file', 'File', data)
        data = self.root._getOb('file')

        self.assertTrue(IFile.providedBy(data))
        self.assertFalse(IBlobFile.providedBy(data))
        self.assertTrue(file_upgrader.validate(data))

        result = file_upgrader.upgrade(data)
        self.assertNotEqual(result, data)
        self.assertTrue(verifyObject(IBlobFile, result))
        self.assertEqual(self.root._getOb('file'), result)
        self.assertEqual(result.get_mime_type(), 'image/png')
        self.assertEqual(result.get_filename(), 'file.png')

    def test_file_in_valid_ghost_folder(self):
        factory = self.root.manage_addProduct['Silva']
        factory.manage_addFolder('folder', 'Folder')
        factory.manage_addGhostFolder('ghost', None, haunted=self.root.folder)
        factory = self.root.folder.manage_addProduct['Silva']
        with self.layer.open_fixture('silva.png') as data:
            factory.manage_addFile('file', 'File', data)
        factory = self.root.ghost.manage_addProduct['Silva']
        with self.layer.open_fixture('silva.png') as data:
            factory.manage_addFile('file', 'File', data)
        data = self.root.ghost._getOb('file')

        self.assertTrue(IFile.providedBy(data))
        self.assertFalse(IBlobFile.providedBy(data))
        self.assertTrue(file_upgrader.validate(data))

        result = file_upgrader.upgrade(data)
        self.assertNotEqual(result, data)

        # The file have been replaced with a ghost asset to the original one.
        self.assertEqual(self.root.ghost._getOb('file'), result)
        self.assertTrue(verifyObject(IGhostAsset, result))
        self.assertEqual(result.get_link_status(), None)
        self.assertEqual(result.get_haunted(), self.root.folder.file)
        self.assertEqual(result.get_mime_type(), 'image/png')
        self.assertEqual(result.get_filename(), 'file.png')

    def test_file_in_valid_ghost_folder_missing_original(self):
        factory = self.root.manage_addProduct['Silva']
        factory.manage_addFolder('folder', 'Folder')
        factory.manage_addGhostFolder('ghost', None, haunted=self.root.folder)
        factory = self.root.folder.manage_addProduct['Silva']
        factory.manage_addIndexer('file', 'File') # This is not a file.
        factory = self.root.ghost.manage_addProduct['Silva']
        with self.layer.open_fixture('silva.png') as data:
            factory.manage_addFile('file', 'File', data)
        data = self.root.ghost._getOb('file')

        self.assertTrue(IFile.providedBy(data))
        self.assertFalse(IBlobFile.providedBy(data))
        self.assertTrue(file_upgrader.validate(data))

        result = file_upgrader.upgrade(data)
        self.assertNotEqual(result, data)
        self.assertTrue(verifyObject(IBlobFile, result))
        self.assertEqual(self.root.ghost._getOb('file'), result)
        self.assertEqual(result.get_mime_type(), 'image/png')
        self.assertEqual(result.get_filename(), 'file.png')

    def test_file_in_broken_ghost_folder(self):
        factory = self.root.manage_addProduct['Silva']
        factory.manage_addGhostFolder('ghost', None,)
        factory = self.root.ghost.manage_addProduct['Silva']
        with self.layer.open_fixture('silva.png') as data:
            factory.manage_addFile('file', 'File', data)
        data = self.root.ghost._getOb('file')

        self.assertTrue(IFile.providedBy(data))
        self.assertFalse(IBlobFile.providedBy(data))
        self.assertTrue(file_upgrader.validate(data))

        result = file_upgrader.upgrade(data)
        self.assertNotEqual(result, data)
        self.assertTrue(verifyObject(IBlobFile, result))
        self.assertEqual(self.root.ghost._getOb('file'), result)
        self.assertEqual(result.get_mime_type(), 'image/png')
        self.assertEqual(result.get_filename(), 'file.png')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(FileUpgraderTestCase))
    return suite
