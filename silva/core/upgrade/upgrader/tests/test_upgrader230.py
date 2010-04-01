# Copyright (c) 2009-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

import os

from Products.Silva.tests import SilvaTestCase
from Products.ParsedXML.ParsedXML import ParsedXML

from silva.core.references.interfaces import IReferenceService
from silva.core.upgrade.upgrader.upgrade_230 import DocumentUpgrader
from zope import component

def test_open(filename, mode='r'):
    directory = os.path.dirname(__file__)
    return open(os.path.join(directory, 'data', filename), mode)


class DocumentUpgraderTestCase(SilvaTestCase.SilvaTestCase):
    """Test upgrader which rewrites links and images to use
    references.
    """

    def afterSetUp(self):
        self.add_document(self.root, 'document', 'Document')
        self.add_folder(self.root, 'folder', 'Folder')
        self.add_publication(self.root, 'publication', 'Publication')
        self.add_image(
            self.root, 'chocobo', 'Chocobo', file=test_open('chocobo.jpg'))

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
        result = DocumentUpgrader.upgrade(self.root.document)
        self.assertEqual(result, self.root.document)
        document_dom = editable._get_document_element()
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
        result = DocumentUpgrader.upgrade(self.root.document)
        self.assertEqual(result, self.root.document)
        document_dom = editable._get_document_element()
        links = document_dom.getElementsByTagName('link')
        self.assertEqual(len(links), 1)
        link = links[0]
        self.failIf(link.hasAttribute('reference'))
        self.failUnless(link.hasAttribute('url'))
        self.assertEquals(link.getAttribute('url'), './edit')
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
        result = DocumentUpgrader.upgrade(self.root.document)
        self.assertEqual(result, self.root.document)
        document_dom = editable._get_document_element()
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
        result = DocumentUpgrader.upgrade(self.root.document)
        self.assertEqual(result, self.root.document)
        document_dom = editable._get_document_element()
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
        result = DocumentUpgrader.upgrade(self.root.document)
        self.assertEqual(result, self.root.document)
        document_dom = editable._get_document_element()
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
        result = DocumentUpgrader.upgrade(self.root.document)
        self.assertEqual(result, self.root.document)
        document_dom = editable._get_document_element()
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
        result = DocumentUpgrader.upgrade(self.root.document)
        self.assertEqual(result, self.root.document)
        document_dom = editable._get_document_element()
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
        result = DocumentUpgrader.upgrade(self.root.document)
        reference_service = component.getUtility(IReferenceService)
        self.assertEqual(result, self.root.document)
        document_dom = editable._get_document_element()

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
        result = DocumentUpgrader.upgrade(self.root.document)
        reference_service = component.getUtility(IReferenceService)
        self.assertEqual(result, self.root.document)
        document_dom = editable._get_document_element()

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
        result = DocumentUpgrader.upgrade(self.root.document)
        reference_service = component.getUtility(IReferenceService)
        self.assertEqual(result, self.root.document)
        document_dom = editable._get_document_element()

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
        result = DocumentUpgrader.upgrade(self.root.document)
        reference_service = component.getUtility(IReferenceService)
        self.assertEqual(result, self.root.document)
        document_dom = editable._get_document_element()

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



import unittest
def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(DocumentUpgraderTestCase))
    return suite

