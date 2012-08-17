# -*- coding: utf-8 -*-
# Copyright (c) 2009-2012 Infrae. All rights reserved.
# See also LICENSE.txt

import unittest

from Products.Silva.testing import FunctionalLayer
from silva.core.upgrade.upgrader.upgrade_230 import link_upgrader, resolve_path


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

        factory.manage_addPublication('publication', 'Publication')
        self.publication = self.root.publication
        factory = self.root.publication.manage_addProduct['Silva']
        factory.manage_addFile('file', 'File')

    def test_resolve_path_absolute_link_spaces(self):
        """resolve_path should work event if there are spaces in the
        input.
        """
        self.assertEqual(
            resolve_path(' http://www.google.com/',
                         '/root/publication',
                         self.root),
            ('http://www.google.com/', None, None))
        self.assertEqual(
            resolve_path(' http://www.google.com/ ',
                         '/root/publication',
                         self.root),
            ('http://www.google.com/', None, None))

    def test_not_validate_absolute_link(self):
        self.version._url = 'http://www.google.com/'
        self.assertFalse(link_upgrader.validate(self.version))

    def test_not_validate_absolute_link_spaces(self):
        """An absolute URL should not validate, even if there are
        spaces before or after it.
        """
        self.version._url = ' http://www.google.com/'
        self.assertFalse(link_upgrader.validate(self.version))

    def test_not_validate_relative_set(self):
        """If the link is already convert, it should not validate
        (there is already _relative set).
        """
        self.version._relative = False
        self.assertFalse(link_upgrader.validate(self.version))

    def test_validate_when_relative(self):
        self.version._url = '/root/publication/file'
        self.assertTrue(link_upgrader.validate(self.version))
        self.version._url = 'publication/file'
        self.assertTrue(link_upgrader.validate(self.version))

    def test_root_link(self):
        self.version._url = '/root/publication/file'
        link_upgrader.upgrade(self.version)
        self.assertEquals(
            self.version.get_target(),
            self.root.publication.file)

    def test_root_link_spaces_post(self):
        """A path to a Silva content should work even if there are
        spaces at the end of it.
        """
        self.version._url = '/root/publication/file '
        link_upgrader.upgrade(self.version)
        self.assertEquals(
            self.version.get_target(),
            self.root.publication.file)

    def test_root_link_spaces_pre(self):
        """A path to a Silva content should work event if there are
        spaces in front of it.
        """
        self.version._url = ' /root/publication/file'
        link_upgrader.upgrade(self.version)
        self.assertEquals(
            self.version.get_target(),
            self.root.publication.file)

    def test_root_link_without_root(self):
        """A common case when the root is removed with Apache rewrite
        rules.
        """
        self.version._url = '/publication/file'
        link_upgrader.upgrade(self.version)
        self.assertEquals(
            self.version.get_target(),
            self.root.publication.file)

    def test_relative_to_self(self):
        self.version._url = '../root/publication/file'
        link_upgrader.upgrade(self.version)
        self.assertEquals(
            self.version.get_target(),
            self.root.publication.file)

    def test_relative_to_not_exists(self):
        self.version._url = '/root/doesnotexists'
        link_upgrader.upgrade(self.version)
        self.assertEquals(
            self.version.get_target(),
            None)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(LinkVersionUpgraderTestCase))
    return suite

