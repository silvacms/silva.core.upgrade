# Copyright (c) 2012 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$


import unittest

from zope.component import getUtility


from Products.Silva.testing import FunctionalLayer
from silva.core.upgrade.upgrader.upgrade_300 import hide_from_toc_upgrader
from Products.SilvaMetadata.interfaces import IMetadataService


SILVA_EXTRA = "http://infrae.com/namespace/metadata/silva-extra"


class HideFromTOCUpgraderTestCase(unittest.TestCase):
    """Test upgrader move hide_from_tocs metadata to silva-settings
    """
    layer = FunctionalLayer

    def setUp(self):
        self.root = self.layer.get_application()
        self.layer.login('manager')
        factory = self.root.manage_addProduct['Silva']
        factory.manage_addFolder('folder', 'Folder')
        folder = self.root.folder

    def test_hide_from_toc(self):
        service = getUtility(IMetadataService)
        self.assertFalse(hide_from_toc_upgrader.validate(self.root.folder))
        mset = self.root.folder.__annotations__[SILVA_EXTRA]
        mset['hide_from_tocs'] = 'hide'
        self.assertTrue(hide_from_toc_upgrader.validate(self.root.folder))
        self.assertEquals(
            hide_from_toc_upgrader.upgrade(self.root.folder),
            self.root.folder)
        self.assertFalse(hide_from_toc_upgrader.validate(self.root.folder))
        self.assertEqual('hide', service.getMetadataValue(
            self.root.folder, 'silva-settings', 'hide_from_tocs'))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(HideFromTOCUpgraderTestCase))
    return suite
