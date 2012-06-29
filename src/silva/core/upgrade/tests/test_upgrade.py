# Copyright (c) 2009-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

import unittest

from silva.core.interfaces import IUpgradeRegistry
from zope.interface.verify import verifyObject

from ..upgrade import get_version_index, get_upgrade_chain
from ..upgrade import BaseUpgrader, AnyMetaType
from ..upgrade import registry, UpgradeRegistry


class UpgradeUtilitiesTestCase(unittest.TestCase):
    """Test utilities which determines which version step should be
    run.
    """

    def test_get_version_index(self):
        versions = ['1.2', '1.4', '1.5a1', '1.5b2', '1.6a2', '2.0',
                    '2.0.1', '2.1.3.4', '2.2', '2.3']
        self.assertEquals(
            get_version_index(versions, '1.5a1'), 3)
        self.assertEquals(
            get_version_index(versions, '1.7b2dev-r3456'), 5)
        self.assertEquals(
            get_version_index(versions, '2.0'), 6)
        self.assertEquals(
            get_version_index(versions, '2.0.0'), 6)
        self.assertEquals(
            get_version_index(versions, '2.1'), 7)
        self.assertEquals(
            get_version_index(versions, '2.2dev-r3458'), 8)
        self.assertEquals(
            get_version_index(versions, '2.3'), 10)
        self.assertEquals(
            get_version_index(versions, '2.4'), 10)

    def test_get_upgrade_chain(self):
        versions = ['1.2', '1.4', '1.5a1', '1.5b2', '1.6a2', '2.0',
                    '2.0.1', '2.1.3.4', '2.2', '2.3']
        self.assertEquals(
            get_upgrade_chain(versions, '1.3', '2.0'),
            ['1.4', '1.5a1', '1.5b2', '1.6a2', '2.0'])
        self.assertEquals(
            get_upgrade_chain(versions, '1.5', '2.0'),
            ['1.6a2', '2.0'])
        self.assertEquals(
            get_upgrade_chain(versions, '1.7', '1.9'),
            [])
        self.assertEquals(
            get_upgrade_chain(versions, '2.1dev-r5678', '2.4'),
            ['2.1.3.4', '2.2', '2.3',])
        self.assertEquals(
            get_upgrade_chain(versions, '2.2', '2.3'),
            ['2.3',])

        versions = ['2.2', '2.3b1', '2.3b2']
        self.assertEquals(
            get_upgrade_chain(versions, '2.3dev', '2.3b2'),
            ['2.3b1', '2.3b2'])

        versions = ['1.2', '1.4', '1.5a1', '1.5b2', '1.6a2', '2.0']
        self.assertEquals(
            get_upgrade_chain(versions, '1.5dev', '1.6'),
            ['1.5a1', '1.5b2', '1.6a2'])


class TestUpgraderA(BaseUpgrader):
    pass

class TestUpgraderB(BaseUpgrader):
    pass

class TestUpgraderC(BaseUpgrader):
    pass

class TestUpgraderD(BaseUpgrader):
    pass


class UpgradeTestCase(unittest.TestCase):
    """Test for the upgrade machinery.
    """

    def test_registry(self):
        verifyObject(IUpgradeRegistry, registry)

    def test_registration_priority(self):
        """Create a registry and register upgrader manually to
        it. Check how they are sorted according to their priority.
        """
        registry = UpgradeRegistry()

        upgraderA = TestUpgraderA('1.0', 'Silva Root', 10)
        upgraderB = TestUpgraderB('1.0', 'Silva Root', 100)
        upgraderC = TestUpgraderC('1.0', AnyMetaType, 50)
        upgraderD = TestUpgraderD('1.2', 'Silva Root', 50)

        registry.register(upgraderB)
        registry.register(upgraderA)
        registry.register(upgraderC)
        registry.register(upgraderD)
        self.assertItemsEqual(
            registry.get_upgraders('1.0', 'Silva Root'),
            [upgraderA, upgraderB, upgraderC])
        self.assertItemsEqual(
            registry.get_upgraders(['1.0',], 'Silva Root'),
            [upgraderA, upgraderB, upgraderC])
        self.assertItemsEqual(
            registry.get_upgraders(['1.0', '1.2'], 'Silva Root'),
            [upgraderA, upgraderB, upgraderC, upgraderD])



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(UpgradeUtilitiesTestCase))
    suite.addTest(unittest.makeSuite(UpgradeTestCase))
    return suite
