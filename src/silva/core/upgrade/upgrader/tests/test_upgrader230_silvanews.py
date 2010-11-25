import unittest
from silva.core.upgrade.upgrader.upgrade_230 import (silvanews_filter_upgrader,
    silvanews_viewer_upgrader)
from Products.SilvaNews.tests.SilvaNewsTestCase import FunctionalLayer


class SilvaNewsUpgraderTestCase(unittest.TestCase):
    layer = FunctionalLayer

    def setUp(self):
        self.root = self.layer.get_application()
        silvanews_factory = self.root.manage_addProduct['SilvaNews']
        factory = self.root.manage_addProduct['Silva']
        factory.manage_addFolder('folder', 'Folder')
        silvanews_factory.manage_addAgendaViewer('agenda', 'Agenda Viewer')
        silvanews_factory.manage_addNewsPublication('newspub', 'News Pub')
        silvanews_factory.manage_addNewsFilter('news_filter', 'Filter')
        silvanews_factory = self.root.folder.manage_addProduct['SilvaNews']
        silvanews_factory.manage_addNewsPublication('newspub', 'News pub')
        silvanews_factory.manage_addAgendaFilter(
            'agenda_filter', 'Agenda Filter')
        silvanews_factory.manage_addNewsViewer('news', 'News Viewer')

    def test_filters_change_sources(self):
        agenda_filter = self.root.folder.agenda_filter
        news_filter = self.root.news_filter
        agenda_filter._sources = ['/root/folder/newspub', '/root/doesnotexists']
        news_filter._sources = ['/root/newspub', '/root/folder/newspub']

        self.assertTrue(silvanews_filter_upgrader.validate(news_filter))
        self.assertTrue(silvanews_filter_upgrader.validate(agenda_filter))

        silvanews_filter_upgrader.upgrade(news_filter)
        silvanews_filter_upgrader.upgrade(agenda_filter)

        self.assertEquals([self.root.newspub, self.root.folder.newspub],
            news_filter.get_sources())
        self.assertEquals([self.root.folder.newspub],
            agenda_filter.get_sources())

        self.assertFalse(silvanews_filter_upgrader.validate(news_filter))
        self.assertFalse(silvanews_filter_upgrader.validate(agenda_filter))

    def test_viewers_change_filters(self):
        agenda_viewer = self.root.agenda
        news_viewer = self.root.folder.news

        news_viewer._filters = [
            '/root/folder/agenda_filter', '/root/news_filter']
        agenda_viewer._filters = [
            '/root/folder/agenda_filter', '/root/doesnotexists']

        self.assertTrue(silvanews_viewer_upgrader.validate(agenda_viewer))
        self.assertTrue(silvanews_viewer_upgrader.validate(news_viewer))

        silvanews_viewer_upgrader.upgrade(news_viewer)
        silvanews_viewer_upgrader.upgrade(agenda_viewer)

        self.assertEquals(
            [self.root.folder.agenda_filter, self.root.news_filter],
            news_viewer.get_filters())
        self.assertEquals(
            [self.root.folder.agenda_filter], agenda_viewer.get_filters())

        self.assertFalse(silvanews_viewer_upgrader.validate(agenda_viewer))
        self.assertFalse(silvanews_viewer_upgrader.validate(news_viewer))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SilvaNewsUpgraderTestCase))
    return suite

