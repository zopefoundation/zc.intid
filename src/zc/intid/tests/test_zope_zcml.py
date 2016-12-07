##############################################################################
#
# Copyright (c) 2001, 2002, 2009, 2016 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""
Tests for the zope-intid.zcml file.

"""
import sys
import unittest

from zc.intid.utility import IntIds

import zope.event

class TestZopeIntidZcml(unittest.TestCase):

    _BARE_IMPLEMENTS = tuple(sorted(zope.interface.implementedBy(IntIds)))

    def setUp(self):
        self.zi = sys.modules['zope.intid']
        self.zii = sys.modules['zope.intid.interfaces']
        sys.modules['zope.intid'] = None

    def tearDown(self):
        sys.modules['zope.intid'] = self.zi
        sys.modules['zope.intid.interfaces'] = self.zii

    def _load_file(self):
        from zope.configuration import xmlconfig
        import zc.intid
        xmlconfig.file('zope-intid.zcml', package=zc.intid)

    def _check_only_zc_interface(self):
        provs = tuple(sorted(zope.interface.implementedBy(IntIds)))
        self.assertEqual(provs, self._BARE_IMPLEMENTS)

    def test_no_zope_intid(self):
        self._check_only_zc_interface()
        self._load_file()
        self._check_only_zc_interface()

    def test_zope_intid_available(self):
        import types
        self.assertRaises(ImportError, __import__, 'zope.intid')
        self._check_only_zc_interface()

        zope_intid_interfaces = types.ModuleType('zope.intid.interfaces')
        class I(zope.interface.Interface):
            pass
        zope_intid_interfaces.IIntIds = I

        sys.modules['zope.intid'] = types.ModuleType('zope.intid')
        sys.modules['zope.intid.interfaces'] = zope_intid_interfaces


        try:
            self._check_only_zc_interface()
            self._load_file()

            implements_now = tuple(zope.interface.implementedBy(IntIds))
            self.assertIn(I, implements_now)

            # Cleanup
            zope.interface.classImplementsOnly(IntIds, *self._BARE_IMPLEMENTS)
        finally:
            del sys.modules['zope.intid']
            del sys.modules['zope.intid.interfaces']

        self._check_only_zc_interface()



def test_suite():
    return unittest.TestSuite([
        unittest.makeSuite(TestZopeIntidZcml),
    ])

test_suite() # coverage

if __name__ == '__main__': # pragma: no cover
    unittest.main()
