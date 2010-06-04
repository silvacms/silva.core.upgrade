# Copyright (c) 2009-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

import unittest

from infrae.testing import TestCase
from silva.core.interfaces import IUpgradeRegistry
from silva.core.upgrade import upgrade
from zope.interface.verify import verifyObject


class UpgradeUtilitiesTestCase(unittest.TestCase):
    """Test utilities which determines which version step should be
    run.
    """

    def setUp(self):
        self.versions = ['1.2', '1.4', '1.5a1', '1.5b2',
                         '1.6a2', '2.0', '2.0.1', '2.1.3.4', '2.2', '2.3']

    def test_get_version_index(self):
        versions = self.versions
        self.assertEquals(
            upgrade.get_version_index(versions, '1.5a1'), 3)
        self.assertEquals(
            upgrade.get_version_index(versions, '1.7b2dev-r3456'), 5)
        self.assertEquals(
            upgrade.get_version_index(versions, '2.0'), 6)
        self.assertEquals(
            upgrade.get_version_index(versions, '2.0.0'), 6)
        self.assertEquals(
            upgrade.get_version_index(versions, '2.1'), 7)
        self.assertEquals(
            upgrade.get_version_index(versions, '2.2dev-r3458'), 9)
        self.assertEquals(
            upgrade.get_version_index(versions, '2.3'), 10)
        self.assertEquals(
            upgrade.get_version_index(versions, '2.4'), 10)

    def test_get_upgrade_chain(self):
        versions = self.versions
        self.assertEquals(
            upgrade.get_upgrade_chain(versions, '1.3', '2.0'),
            ['1.4', '1.5a1', '1.5b2', '1.6a2', '2.0'])
        self.assertEquals(
            upgrade.get_upgrade_chain(versions, '1.5', '2.0'),
            ['1.6a2', '2.0'])
        self.assertEquals(
            upgrade.get_upgrade_chain(versions, '1.7', '1.9'),
            [])
        self.assertEquals(
            upgrade.get_upgrade_chain(versions, '2.1dev-r5678', '2.4'),
            ['2.1.3.4', '2.2', '2.3',])
        self.assertEquals(
            upgrade.get_upgrade_chain(versions, '2.2', '2.3'),
            ['2.3',])


class TestUpgraderA(upgrade.BaseUpgrader):
    pass

class TestUpgraderB(upgrade.BaseUpgrader):
    pass

class TestUpgraderC(upgrade.BaseUpgrader):
    pass


class UpgradeTestCase(TestCase):
    """Test for the upgrade machinery.
    """

    def test_registry(self):
        verifyObject(IUpgradeRegistry, upgrade.registry)

    def test_registration_priority(self):
        """Create a registry and register upgrader manually to
        it. Check how they are sorted according to their priority.
        """
        registry = upgrade.UpgradeRegistry()

        upgraderA = TestUpgraderA(1.0, 'Silva Root', 10)
        upgraderB = TestUpgraderB(1.0, 'Silva Root', 100)
        upgraderC = TestUpgraderC(1.0, 'Silva Root', 50)

        registry.registerUpgrader(upgraderB)
        registry.registerUpgrader(upgraderA)
        registry.registerUpgrader(upgraderC)
        self.assertListEqual(
            registry.getUpgraders(1.0, 'Silva Root'),
            [upgraderA, upgraderB, upgraderC])



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(UpgradeUtilitiesTestCase))
    suite.addTest(unittest.makeSuite(UpgradeTestCase))
    return suite
