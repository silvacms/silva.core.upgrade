# Copyright (c) 2009-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

import unittest

from Products.Silva.testing import FunctionalLayer
from Products.Silva.tests.helpers import open_test_file
from Products.ParsedXML.ParsedXML import ParsedXML

from silva.core.references.interfaces import IReferenceService
from silva.core.upgrade.upgrader.upgrade_230 import document_upgrader
from zope import component



class DocumentUpgraderTestCase(unittest.TestCase):
    """Test upgrader which rewrites links and images to use
    references.
    """
    layer = FunctionalLayer

    def setUp(self):
        self.root = self.layer.get_application()
        self.layer.login('editor')
        factory = self.root.manage_addProduct['Silva']
        factory.manage_addFolder('folder', 'Folder')
        factory.manage_addPublication('publication', 'Publication')
        factory.manage_addImage('chocobo', 'Chocobo', file=open_test_file(
                'chocobo.jpg', globals()))
        factory = self.root.manage_addProduct['SilvaDocument']
        factory.manage_addDocument('document', 'Document')

    def test_upgrade_link(self):
        """Test upgrade of a simple link
        """
        editable = self.root.document.get_editable()
        editable.content = ParsedXML(
            'content',
            """<?xml version="1.0" encoding="utf-8"?>
<doc>
  <p type="normal">
    <link target="_blank" url="./publication">Publication link</link>
  </p>
</doc>""")
        result = document_upgrader.upgrade(self.root.document)
        self.assertEqual(result, self.root.document)
        document_dom = editable.content.documentElement
        links = document_dom.getElementsByTagName('link')
        self.assertEqual(len(links), 1)
        link = links[0]
        self.failUnless(link.hasAttribute('reference'))
        self.failIf(link.hasAttribute('url'))
        self.failIf(link.hasAttribute('anchor'))
        reference_name = link.getAttribute('reference')
        reference_service = component.getUtility(IReferenceService)
        reference = reference_service.get_reference(
            editable, name=reference_name)
        self.assertEqual(reference.target, self.root.publication)

    def test_upgrade_link_not_silva_object(self):
        """Test upgrade of a link that does not point to a Silva
        object, like for instance to the edit interface.
        """
        editable = self.root.document.get_editable()
        editable.content = ParsedXML(
            'content',
            """<?xml version="1.0" encoding="utf-8"?>
<doc>
  <p type="normal">
    <link target="_blank" url="./edit">SMI</link>
  </p>
</doc>""")
        result = document_upgrader.upgrade(self.root.document)
        self.assertEqual(result, self.root.document)
        document_dom = editable.content.documentElement
        links = document_dom.getElementsByTagName('link')
        self.assertEqual(len(links), 1)
        link = links[0]
        self.failIf(link.hasAttribute('reference'))
        self.failUnless(link.hasAttribute('url'))
        self.assertEquals(link.getAttribute('url'), './edit')
        self.failIf(link.hasAttribute('anchor'))

    def test_upgrade_link_too_high(self):
        """Test upgrade of a link that have an invalid relative path
        to something not possible (like too many ..).
        """
        editable = self.root.document.get_editable()
        editable.content = ParsedXML(
            'content',
            """<?xml version="1.0" encoding="utf-8"?>
<doc>
  <p type="normal">
    <link target="_blank" url="./../../../MANAGE">ME HACKER</link>
  </p>
</doc>""")
        result = document_upgrader.upgrade(self.root.document)
        self.assertEqual(result, self.root.document)
        document_dom = editable.content.documentElement
        links = document_dom.getElementsByTagName('link')
        self.assertEqual(len(links), 1)
        link = links[0]
        self.failIf(link.hasAttribute('reference'))
        self.failUnless(link.hasAttribute('url'))
        self.assertEquals(link.getAttribute('url'), './../../../MANAGE')
        self.failIf(link.hasAttribute('anchor'))

    def test_upgrade_link_only_anchor(self):
        """Test upgrade of a link that is only to an anchor on the
        same page
        """
        editable = self.root.document.get_editable()
        editable.content = ParsedXML(
            'content',
            """<?xml version="1.0" encoding="utf-8"?>
<doc>
  <p type="normal">
    <link target="_blank" url="#on_me">On me link</link>
  </p>
</doc>""")
        result = document_upgrader.upgrade(self.root.document)
        self.assertEqual(result, self.root.document)
        document_dom = editable.content.documentElement
        links = document_dom.getElementsByTagName('link')
        self.assertEqual(len(links), 1)
        link = links[0]
        self.failIf(link.hasAttribute('reference'))
        self.failIf(link.hasAttribute('url'))
        self.failUnless(link.hasAttribute('anchor'))
        self.assertEqual(link.getAttribute('anchor'), 'on_me')

    def test_upgrade_link_with_anchor(self):
        """Test upgrade of a simple link to a content with an anchor
        """
        editable = self.root.document.get_editable()
        editable.content = ParsedXML(
            'content',
            """<?xml version="1.0" encoding="utf-8"?>
<doc>
  <p type="normal">
    <link target="_blank" url="./publication#on_me">On me link</link>
  </p>
</doc>""")
        result = document_upgrader.upgrade(self.root.document)
        self.assertEqual(result, self.root.document)
        document_dom = editable.content.documentElement
        links = document_dom.getElementsByTagName('link')
        self.assertEqual(len(links), 1)
        link = links[0]
        self.failUnless(link.hasAttribute('reference'))
        self.failIf(link.hasAttribute('url'))
        self.failUnless(link.hasAttribute('anchor'))
        self.assertEqual(link.getAttribute('anchor'), 'on_me')
        reference_name = link.getAttribute('reference')
        reference_service = component.getUtility(IReferenceService)
        reference = reference_service.get_reference(
            editable, name=reference_name)
        self.assertEqual(reference.target, self.root.publication)

    def test_upgrade_link_external(self):
        """Test upgrade of a link which is an external URL
        """
        editable = self.root.document.get_editable()
        editable.content = ParsedXML(
            'content',
            """<?xml version="1.0" encoding="utf-8"?>
<doc>
  <p type="normal">
    <link target="_blank" url="http://infrae.com#top">Infrae link</link>
  </p>
</doc>""")
        result = document_upgrader.upgrade(self.root.document)
        self.assertEqual(result, self.root.document)
        document_dom = editable.content.documentElement
        links = document_dom.getElementsByTagName('link')
        self.assertEqual(len(links), 1)
        link = links[0]
        self.failIf(link.hasAttribute('reference'))
        self.failIf(link.hasAttribute('anchor'))
        self.failUnless(link.hasAttribute('url'))
        url = link.getAttribute('url')
        self.assertEqual(url, 'http://infrae.com#top')

    def test_upgrade_link_broken(self):
        """Test upgrade of a link which is an external URL
        """
        editable = self.root.document.get_editable()
        editable.content = ParsedXML(
            'content',
            """<?xml version="1.0" encoding="utf-8"?>
<doc>
  <p type="normal">
    <link target="_blank" url="inexisting_document">Document link</link>
  </p>
</doc>""")
        result = document_upgrader.upgrade(self.root.document)
        self.assertEqual(result, self.root.document)
        document_dom = editable.content.documentElement
        links = document_dom.getElementsByTagName('link')
        self.assertEqual(len(links), 1)
        link = links[0]
        self.failIf(link.hasAttribute('reference'))
        self.failUnless(link.hasAttribute('url'))
        url = link.getAttribute('url')
        self.assertEqual(url, 'inexisting_document')

    def test_upgrade_image(self):
        """Test upgrade of an image, regular without any link
        """
        editable = self.root.document.get_editable()
        editable.content = ParsedXML(
            'content',
            """<?xml version="1.0" encoding="utf-8"?>
<doc>
  <p type="normal">
    <image alignment="image-left" title="" width="600" image_title="Chocobo" rewritten_path="http://localhost/root/chocobo" target="_self" height="177" path="chocobo" link_to_hires="0" link="" />
  </p>
</doc>""")
        result = document_upgrader.upgrade(self.root.document)
        self.assertEqual(result, self.root.document)
        document_dom = editable.content.documentElement
        images = document_dom.getElementsByTagName('image')
        self.assertEqual(len(images), 1)
        image = images[0]
        self.failUnless(image.hasAttribute('reference'))
        self.failIf(image.hasAttribute('path'))
        self.failIf(image.hasAttribute('rewritten_path'))
        self.failIf(image.hasAttribute('target'))
        self.failIf(image.hasAttribute('link'))
        self.failIf(image.hasAttribute('link_to_hires'))
        self.failIf(image.hasAttribute('silva_title'))
        self.failUnless(image.hasAttribute('title'))
        self.assertEqual(image.getAttribute('title'), 'Chocobo')
        reference_name = image.getAttribute('reference')
        reference_service = component.getUtility(IReferenceService)
        reference = reference_service.get_reference(
            editable, name=reference_name)
        self.assertEqual(reference.target, self.root.chocobo)

    def test_upgrade_image_link_to_hires(self):
        """Test to upgrade an image that contains a link to a hires
        version of itself.
        """
        editable = self.root.document.get_editable()
        editable.content = ParsedXML(
            'content',
            """<?xml version="1.0" encoding="utf-8"?>
<doc>
  <p type="normal">
    <image alignment="image-left" title="Big Chocobo" width="600" image_title="Chocobo" rewritten_path="http://localhost/root/chocobo" target="_self" height="177" path="chocobo" link_to_hires="1" link="" />
  </p>
</doc>""")
        result = document_upgrader.upgrade(self.root.document)
        reference_service = component.getUtility(IReferenceService)
        self.assertEqual(result, self.root.document)
        document_dom = editable.content.documentElement

        # The converter added a link to the hires chocobo
        links = document_dom.getElementsByTagName('link')
        self.assertEqual(len(links), 1)
        link = links[0]
        self.failUnless(link.hasAttribute('reference'))
        self.failUnless(link.hasAttribute('target'))
        self.assertEqual(link.getAttribute('target'), '_self')
        self.failUnless(link.hasAttribute('title'))
        self.assertEqual(link.getAttribute('title'), 'Big Chocobo')
        reference_name = link.getAttribute('reference')
        reference = reference_service.get_reference(
            editable, name=reference_name)
        self.assertEqual(reference.target, self.root.chocobo)

        # The image points to the chocobo as well
        images = link.childNodes
        self.assertEqual(len(images), 1)
        image = images[0]
        self.assertEqual(image.nodeName, 'image')
        self.failUnless(image.hasAttribute('reference'))
        self.failIf(image.hasAttribute('path'))
        self.failIf(image.hasAttribute('rewritten_path'))
        self.failIf(image.hasAttribute('target'))
        self.failIf(image.hasAttribute('link'))
        self.failIf(image.hasAttribute('link_to_hires'))
        self.failIf(image.hasAttribute('silva_title'))
        self.failUnless(image.hasAttribute('title'))
        self.assertEqual(image.getAttribute('title'), 'Chocobo')
        reference_name = image.getAttribute('reference')
        reference = reference_service.get_reference(
            editable, name=reference_name)
        self.assertEqual(reference.target, self.root.chocobo)

        # There is only one image in the document
        images = document_dom.getElementsByTagName('image')
        self.assertEqual(len(images), 1)
        self.assertEqual(image, images[0])

    def test_upgrade_image_link(self):
        """Test to upgrade an image that contains a link to a
        different content in Silva.
        """
        editable = self.root.document.get_editable()
        editable.content = ParsedXML(
            'content',
            """<?xml version="1.0" encoding="utf-8"?>
<doc>
  <p type="normal">
    <image alignment="image-left" title="Pub" width="600" image_title="Chocobo" rewritten_path="http://localhost/root/chocobo" target="_blank" height="177" path="chocobo" link_to_hires="0" link="../publication" />
  </p>
</doc>""")
        result = document_upgrader.upgrade(self.root.document)
        reference_service = component.getUtility(IReferenceService)
        self.assertEqual(result, self.root.document)
        document_dom = editable.content.documentElement

        # The converter added a link to the publication
        links = document_dom.getElementsByTagName('link')
        self.assertEqual(len(links), 1)
        link = links[0]
        self.failUnless(link.hasAttribute('reference'))
        self.failUnless(link.hasAttribute('target'))
        self.assertEqual(link.getAttribute('target'), '_blank')
        self.failUnless(link.hasAttribute('title'))
        self.assertEqual(link.getAttribute('title'), 'Pub')
        reference_name = link.getAttribute('reference')
        reference = reference_service.get_reference(
            editable, name=reference_name)
        self.assertEqual(reference.target, self.root.publication)

        # The image points to the chocobo
        images = link.childNodes
        self.assertEqual(len(images), 1)
        image = images[0]
        self.assertEqual(image.nodeName, 'image')
        self.failUnless(image.hasAttribute('reference'))
        self.failIf(image.hasAttribute('path'))
        self.failIf(image.hasAttribute('rewritten_path'))
        self.failIf(image.hasAttribute('target'))
        self.failIf(image.hasAttribute('link'))
        self.failIf(image.hasAttribute('link_to_hires'))
        self.failIf(image.hasAttribute('silva_title'))
        self.failUnless(image.hasAttribute('title'))
        self.assertEqual(image.getAttribute('title'), 'Chocobo')
        reference_name = image.getAttribute('reference')
        reference = reference_service.get_reference(
            editable, name=reference_name)
        self.assertEqual(reference.target, self.root.chocobo)

        # There is only one image in the document
        images = document_dom.getElementsByTagName('image')
        self.assertEqual(len(images), 1)
        self.assertEqual(image, images[0])

    def test_upgrade_image_broken_link(self):
        """Test to upgrade an missing image that contains a link to a
        different content in Silva.
        """
        editable = self.root.document.get_editable()
        editable.content = ParsedXML(
            'content',
            """<?xml version="1.0" encoding="utf-8"?>
<doc>
  <p type="normal">
    <image alignment="image-left" title="Pub" width="600" image_title="Nothing" rewritten_path="http://localhost/root/nothing" target="_blank" height="177" path="nothing" link_to_hires="0" link="../publication" />
  </p>
</doc>""")
        result = document_upgrader.upgrade(self.root.document)
        reference_service = component.getUtility(IReferenceService)
        self.assertEqual(result, self.root.document)
        document_dom = editable.content.documentElement

        # The converter added a link to the publication
        links = document_dom.getElementsByTagName('link')
        self.assertEqual(len(links), 1)
        link = links[0]
        self.failUnless(link.hasAttribute('reference'))
        self.failUnless(link.hasAttribute('target'))
        self.assertEqual(link.getAttribute('target'), '_blank')
        self.failUnless(link.hasAttribute('title'))
        self.assertEqual(link.getAttribute('title'), 'Pub')
        reference_name = link.getAttribute('reference')
        reference = reference_service.get_reference(
            editable, name=reference_name)
        self.assertEqual(reference.target, self.root.publication)

        # The image keeps its old path settings
        images = link.childNodes
        self.assertEqual(len(images), 1)
        image = images[0]
        self.assertEqual(image.nodeName, 'image')
        self.failIf(image.hasAttribute('reference'))
        self.failUnless(image.hasAttribute('path'))
        self.assertEqual(image.getAttribute('path'), 'nothing')
        self.failUnless(image.hasAttribute('rewritten_path'))
        self.assertEqual(
            image.getAttribute('rewritten_path'),
            'http://localhost/root/nothing')
        self.failIf(image.hasAttribute('target'))
        self.failIf(image.hasAttribute('link'))
        self.failIf(image.hasAttribute('link_to_hires'))
        self.failIf(image.hasAttribute('silva_title'))
        self.failUnless(image.hasAttribute('title'))
        self.assertEqual(image.getAttribute('title'), 'Nothing')

        # There is only one image in the document
        images = document_dom.getElementsByTagName('image')
        self.assertEqual(len(images), 1)
        self.assertEqual(image, images[0])

    def test_upgrade_image_link_broken(self):
        """Test to upgrade an image that contains a link to a
        different missing content in Silva. This would be the same for
        link with external URLs.
        """
        editable = self.root.document.get_editable()
        editable.content = ParsedXML(
            'content',
            """<?xml version="1.0" encoding="utf-8"?>
<doc>
  <p type="normal">
    <image alignment="image-left" title="Pub" width="600" image_title="Chocobo" rewritten_path="http://localhost/root/chocobo" target="_blank" height="177" path="chocobo" link_to_hires="0" link="foo_bar" />
  </p>
</doc>""")
        result = document_upgrader.upgrade(self.root.document)
        reference_service = component.getUtility(IReferenceService)
        self.assertEqual(result, self.root.document)
        document_dom = editable.content.documentElement

        # The converter added a link to the foo_bar URL.
        links = document_dom.getElementsByTagName('link')
        self.assertEqual(len(links), 1)
        link = links[0]
        self.failIf(link.hasAttribute('reference'))
        self.failUnless(link.hasAttribute('url'))
        self.assertEqual(link.getAttribute('url'), 'foo_bar')
        self.failUnless(link.hasAttribute('target'))
        self.assertEqual(link.getAttribute('target'), '_blank')
        self.failUnless(link.hasAttribute('title'))
        self.assertEqual(link.getAttribute('title'), 'Pub')

        # The image points to the chocobo
        images = link.childNodes
        self.assertEqual(len(images), 1)
        image = images[0]
        self.assertEqual(image.nodeName, 'image')
        self.failUnless(image.hasAttribute('reference'))
        self.failIf(image.hasAttribute('path'))
        self.failIf(image.hasAttribute('rewritten_path'))
        self.failIf(image.hasAttribute('target'))
        self.failIf(image.hasAttribute('link'))
        self.failIf(image.hasAttribute('link_to_hires'))
        self.failIf(image.hasAttribute('silva_title'))
        self.failUnless(image.hasAttribute('title'))
        self.assertEqual(image.getAttribute('title'), 'Chocobo')
        reference_name = image.getAttribute('reference')
        reference = reference_service.get_reference(
            editable, name=reference_name)
        self.assertEqual(reference.target, self.root.chocobo)

        # There is only one image in the document
        images = document_dom.getElementsByTagName('image')
        self.assertEqual(len(images), 1)
        self.assertEqual(image, images[0])


from silva.core.upgrade.upgrader.upgrade_230 import LinkVersionUpgrader

class LinkVersionUpgraderTestCase(unittest.TestCase):
    """Test upgrader relative links to references
    """
    layer = FunctionalLayer

    def setUp(self):
        self.root = self.layer.get_application()
        factory = self.root.manage_addProduct['Silva']
        factory.manage_addLink('link', 'Link', url="http://www.google.com")
        self.link = self.root.link
        self.version = getattr(self.root.link, '0')
        self.upgrader = LinkVersionUpgrader('2.3', 'Link Version')

        factory.manage_addPublication('pub', 'Pub')
        self.pub = self.root.pub
        factory = self.pub.manage_addProduct['Silva']
        factory.manage_addFile('file', 'File')

    def test_not_validate_absolute_link(self):
        self.version._url = 'http://www.google.com/'
        self.assertFalse(self.upgrader.validate(self.version))

    def test_not_validate_relative_set(self):
        self.version._relative = False
        self.assertFalse(self.upgrader.validate(self.version))

    def test_validate_when_relative(self):
        self.version._url = '/root/pub/file'
        self.assertTrue(self.upgrader.validate(self.version))
        self.version._url = 'pub/file'
        self.assertTrue(self.upgrader.validate(self.version))

    def test_root_link(self):
        self.version._url = '/root/pub/file'
        self.upgrader.upgrade(self.version)
        self.assertEquals(self.pub.file, self.version._target)

    def test_root_link_without_root(self):
        """ A common case when the root is remove with rewrite rules
        in apache.
        """
        self.version._url = '/pub/file'
        self.upgrader.upgrade(self.version)
        self.assertEquals(self.pub.file, self.version._target)

    def test_relative_to_self(self):
        self.version._url = '../root/pub/file'
        self.upgrader.upgrade(self.version)
        self.assertEquals(self.pub.file, self.version._target)

    def test_relative_to_not_exists(self):
        self.version._url = '/root/doesnotexists'
        self.upgrader.upgrade(self.version)
        self.assertEquals(None, self.version._target)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(DocumentUpgraderTestCase))
    suite.addTest(unittest.makeSuite(LinkVersionUpgraderTestCase))
    return suite

