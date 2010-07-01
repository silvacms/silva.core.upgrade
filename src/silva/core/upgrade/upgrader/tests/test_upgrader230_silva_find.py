# Copyright (c) 2009-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

import unittest

from zope.component import getUtility
from Products.Silva.testing import FunctionalLayer
from silva.core.upgrade.upgrader.upgrade_230 import silva_find_upgrader
from silva.core.references.interfaces import IReferenceService
from Products.SilvaFind.errors import SilvaFindError


class SilvaFindUpgraderTestCase(unittest.TestCase):
    """Test upgrader which rewrites links and images to use
    references.
    """
    layer = FunctionalLayer

    def setUp(self):
        self.root = self.layer.get_application()
        self.layer.login('editor')
        factory = self.root.manage_addProduct['Silva']
        factory.manage_addPublication('pub', 'Pub')
        factory = self.root.manage_addProduct['SilvaFind']
        factory.manage_addSilvaFind('search', 'Search')
        self.silva_find = self.root.search
        self.silva_find.setCriterionValue('path', '/root/pub')

    def test_upgrade_create_reference(self):
        silva_find_upgrader.upgrade(self.silva_find)
        ref_service = getUtility(IReferenceService)
        refs = list(ref_service.get_references_to(self.root.pub))
        self.assertTrue(self.silva_find in [r.source for r in refs])


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SilvaFindUpgraderTestCase))
    return suite
