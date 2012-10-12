
import unittest
from ..upgrade import BaseUpgrader, UpgradeRegistry, AnyMetaType, UpgradeProcess


VERSION = '1.0'


class PrimaryColor(BaseUpgrader):

    tags = set(['blue', 'red', 'green'])


class BlackAndWhite(BaseUpgrader):

    tags = set(['black', 'white'])


class GreenAndWhite(BaseUpgrader):

    tags = set(['green', 'white'])


class NoTags(BaseUpgrader):
    pass


no_tags = NoTags(VERSION, AnyMetaType, priority=1.0)
primary = PrimaryColor(VERSION, AnyMetaType, priority=2.0)
black_and_white = BlackAndWhite(VERSION, AnyMetaType, priority=3.0)
green_and_white = GreenAndWhite(VERSION, AnyMetaType, priority=4.0)


class FakeContent(object):

    meta_type = 'Fake Content'


class TagsFilteringTestCase(unittest.TestCase):

    def setUp(self):
        self.registry = UpgradeRegistry()
        self.registry.register(primary)
        self.registry.register(no_tags) 
        self.registry.register(black_and_white)
        self.registry.register(green_and_white)

    def test_no_tags_filtering(self):
        process = UpgradeProcess(self.registry, [VERSION])
        self.assertEquals([no_tags, primary, black_and_white, green_and_white],
            process.get_upgraders(FakeContent))

    def test_whitelist(self):
        process = UpgradeProcess(self.registry, [VERSION], whitelist=['white'])
        self.assertEquals([black_and_white, green_and_white],
            process.get_upgraders(FakeContent))

    def test_blacklist(self):
        process = UpgradeProcess(self.registry, [VERSION], blacklist=['white'])
        self.assertEquals([no_tags, primary],
            process.get_upgraders(FakeContent))

    def test_blacklist_and_whitelist(self):
        process = UpgradeProcess(self.registry, [VERSION], blacklist=['black'],
            whitelist=['white'])
        self.assertEquals([green_and_white],
            process.get_upgraders(FakeContent))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TagsFilteringTestCase))
    return suite

