# -*- coding: utf-8 -*-
# Copyright (c) 2013 Infrae. All rights reserved.
# See also LICENSE.txt

import unittest

from zope.interface.verify import verifyObject
from OFS.Image import Image
from Products.Silva.testing import FunctionalLayer

from silva.core.interfaces import IFile, IImage, IGhostAsset
from silva.core.upgrade.upgrader.upgrade_236 import image_upgrader


class ImageUpgraderTestCase(unittest.TestCase):
    layer = FunctionalLayer

    def setUp(self):
        self.root = self.layer.get_application()
        self.layer.login('manager')

    def test_image(self):
        factory = self.root.manage_addProduct['Silva']
        factory.manage_addImage('image', 'Image')
        image = self.root._getOb('image')

        with self.layer.open_fixture('silva.png') as data:
            image.hires_image = Image('image', 'Image', data)

        self.assertFalse(IFile.providedBy(image.image))
        self.assertFalse(IFile.providedBy(image.hires_image))
        self.assertFalse(IFile.providedBy(image.thumbnail_image))
        self.assertTrue(image_upgrader.validate(image))
        result = image_upgrader.upgrade(image)
        self.assertEqual(result, image)

        # Image is still here, and content have been replaced.
        self.assertTrue(verifyObject(IImage, result))
        self.assertTrue(verifyObject(IFile, result.image))
        self.assertTrue(verifyObject(IFile, result.hires_image))
        self.assertTrue(verifyObject(IFile, result.thumbnail_image))
        self.assertEqual(self.root._getOb('image'), result)
        self.assertEqual(result.get_mime_type(), 'image/png')
        self.assertEqual(result.get_filename(), 'image.png')

    def test_image_in_valid_ghost_folder(self):
        factory = self.root.manage_addProduct['Silva']
        factory.manage_addFolder('folder', 'Folder')
        factory.manage_addGhostFolder('ghost', None, haunted=self.root.folder)
        factory = self.root.folder.manage_addProduct['Silva']
        with self.layer.open_fixture('silva.png') as data:
            factory.manage_addImage('image', 'Image', data)

        factory = self.root.ghost.manage_addProduct['Silva']
        factory.manage_addImage('image', 'Image')
        image = self.root.ghost._getOb('image')
        with self.layer.open_fixture('silva.png') as data:
            image.hires_image = Image('image', 'Image', data)

        self.assertFalse(IFile.providedBy(image.image))
        self.assertFalse(IFile.providedBy(image.hires_image))
        self.assertFalse(IFile.providedBy(image.thumbnail_image))
        self.assertTrue(image_upgrader.validate(image))

        result = image_upgrader.upgrade(image)
        self.assertNotEqual(result, image)

        # The image have been replaced with a ghost asset to the original one.
        self.assertEqual(self.root.ghost._getOb('image'), result)
        self.assertTrue(verifyObject(IGhostAsset, result))
        self.assertEqual(result.get_link_status(), None)
        self.assertEqual(result.get_haunted(), self.root.folder.image)
        self.assertEqual(result.get_mime_type(), 'image/png')
        self.assertEqual(result.get_filename(), 'image.png')

    def test_image_in_valid_ghost_folder_missing_original(self):
        factory = self.root.manage_addProduct['Silva']
        factory.manage_addFolder('folder', 'Folder')
        factory.manage_addGhostFolder('ghost', None, haunted=self.root.folder)
        factory = self.root.folder.manage_addProduct['Silva']
        factory.manage_addIndexer('image', 'Image') # This is not an image.
        factory = self.root.ghost.manage_addProduct['Silva']
        factory.manage_addImage('image', 'Image')
        image = self.root.ghost._getOb('image')
        with self.layer.open_fixture('silva.png') as data:
            image.hires_image = Image('image', 'Image', data)

        self.assertFalse(IFile.providedBy(image.image))
        self.assertFalse(IFile.providedBy(image.hires_image))
        self.assertFalse(IFile.providedBy(image.thumbnail_image))
        self.assertTrue(image_upgrader.validate(image))

        result = image_upgrader.upgrade(image)
        self.assertEqual(result, image)

        # Image should have not been replaced, but have been updated.
        self.assertEqual(self.root.ghost._getOb('image'), result)
        self.assertTrue(verifyObject(IImage, result))
        self.assertTrue(verifyObject(IFile, result.image))
        self.assertTrue(verifyObject(IFile, result.hires_image))
        self.assertTrue(verifyObject(IFile, result.thumbnail_image))
        self.assertEqual(result.get_mime_type(), 'image/png')
        self.assertEqual(result.get_filename(), 'image.png')

    def test_image_in_broken_ghost_folder(self):
        factory = self.root.manage_addProduct['Silva']
        factory.manage_addGhostFolder('ghost', None)
        factory = self.root.ghost.manage_addProduct['Silva']
        factory.manage_addImage('image', 'Image')
        image = self.root.ghost._getOb('image')

        with self.layer.open_fixture('silva.png') as data:
            image.hires_image = Image('image', 'Image', data)

        self.assertFalse(IFile.providedBy(image.image))
        self.assertFalse(IFile.providedBy(image.hires_image))
        self.assertFalse(IFile.providedBy(image.thumbnail_image))
        self.assertTrue(image_upgrader.validate(image))

        result = image_upgrader.upgrade(image)
        self.assertEqual(result, image)

        # Image should have not been replaced, but have been updated.
        self.assertEqual(self.root.ghost._getOb('image'), result)
        self.assertTrue(verifyObject(IImage, result))
        self.assertTrue(verifyObject(IFile, result.image))
        self.assertTrue(verifyObject(IFile, result.hires_image))
        self.assertTrue(verifyObject(IFile, result.thumbnail_image))
        self.assertEqual(result.get_mime_type(), 'image/png')
        self.assertEqual(result.get_filename(), 'image.png')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ImageUpgraderTestCase))
    return suite

