# Copyright (c) 2009-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

import unittest

from Products.Silva.testing import FunctionalLayer
from silva.core.upgrade.upgrader.upgrade_230 import link_upgrader


class LinkVersionUpgraderTestCase(unittest.TestCase):
    """Test upgrader relative links to references
    """
    layer = FunctionalLayer

    def setUp(self):
        self.root = self.layer.get_application()
        self.layer.login('editor')
        factory = self.root.manage_addProduct['Silva']
        factory.manage_addLink('link', 'Link', url="http://www.google.com")
        self.link = self.root.link
        self.version = self.link.get_editable()

        factory.manage_addPublication('pub', 'Pub')
        self.pub = self.root.pub
        factory = self.pub.manage_addProduct['Silva']
        factory.manage_addFile('file', 'File')

    def test_not_validate_absolute_link(self):
        self.version._url = 'http://www.google.com/'
        self.assertFalse(link_upgrader.validate(self.version))

    def test_not_validate_relative_set(self):
        self.version._relative = False
        self.assertFalse(link_upgrader.validate(self.version))

    def test_validate_when_relative(self):
        self.version._url = '/root/pub/file'
        self.assertTrue(link_upgrader.validate(self.version))
        self.version._url = 'pub/file'
        self.assertTrue(link_upgrader.validate(self.version))

    def test_root_link(self):
        self.version._url = '/root/pub/file'
        link_upgrader.upgrade(self.version)
        self.assertEquals(self.pub.file, self.version.get_target())

    def test_root_link_without_root(self):
        """ A common case when the root is remove with rewrite rules
        in apache.
        """
        self.version._url = '/pub/file'
        link_upgrader.upgrade(self.version)
        self.assertEquals(self.pub.file, self.version.get_target())

    def test_relative_to_self(self):
        self.version._url = '../root/pub/file'
        link_upgrader.upgrade(self.version)
        self.assertEquals(self.pub.file, self.version.get_target())

    def test_relative_to_not_exists(self):
        self.version._url = '/root/doesnotexists'
        link_upgrader.upgrade(self.version)
        self.assertEquals(None, self.version.get_target())


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(LinkVersionUpgraderTestCase))
    return suite

