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
Tests for the unique id utility.

"""


import BTrees

import unittest

from zc.intid.interfaces import IIdAddedEvent
from zc.intid.interfaces import IIdRemovedEvent
from zc.intid.interfaces import IIntIds
from zc.intid.interfaces import IIntIdsSubclass
from zc.intid.interfaces import IntIdMismatchError
from zc.intid.interfaces import IntIdInUseError


from zc.intid.utility import IntIds

from zope.interface.verify import verifyObject


from zope.security.checker import CheckerPublic
from zope.security.proxy import Proxy

from zope.intid.interfaces import IntIdMissingError
from zope.intid.interfaces import ObjectMissingError

import zope.event


class P(object):
    pass


class TestIntIds(unittest.TestCase):

    def createIntIds(self, attribute="iid"):
        return IntIds(attribute)

    def setUp(self):
        self.events = []
        zope.event.subscribers.append(self.events.append)

    def tearDown(self):
        zope.event.subscribers.remove(self.events.append)

    def test_interface(self):
        u = self.createIntIds()
        verifyObject(IIntIds, u)
        verifyObject(IIntIdsSubclass, u)

    def test_proxies(self):
        # This test ensures that the `getId` method exhibits the same
        # behavior when passed a proxy as it does in zope.intid.
        u = self.createIntIds()
        obj = P()
        iid = u.register(obj)
        proxied = Proxy(obj,
                        CheckerPublic)
        # Passing `getId` a proxied object yields the correct id
        self.assertEqual(u.getId(proxied), iid)
        # `getId` raises a KeyError with the proxied object if it isn't
        # in its mapping.
        obj.iid = None
        with self.assertRaises(IntIdMissingError) as ex:
            u.getId(proxied)
        self.assertIs(ex.exception.args[0], proxied)

        obj.iid = -1
        with self.assertRaises(IntIdMismatchError) as ex:
            u.getId(proxied)
        self.assertIs(ex.exception.args[0], proxied)


        obj = P()
        obj.iid = iid
        proxied = Proxy(obj,
                        CheckerPublic)
        with self.assertRaises(IntIdMissingError) as ex:
            u.getId(proxied)
        self.assertIs(ex.exception.args[0], proxied)

    def test_non_keyreferences(self):
        #
        # This test, copied from zope.intid, was used in that context to
        # determine that failed adaptations to IKeyReference did not
        # cause unexpected behaviors from the API.
        #
        # In zc.intid, this simple ensures that the behaviors don't
        # differ from that of zope.intid.
        #
        u = self.createIntIds()
        obj = object()

        self.assertIsNone(u.queryId(obj))
        self.assertIsNone(u.unregister(obj))
        self.assertRaises(IntIdMissingError, u.getId, obj)

    def test(self):
        u = self.createIntIds()
        obj = P()

        self.assertRaises(IntIdMissingError, u.getId, obj)
        self.assertRaises(IntIdMissingError, u.getId, P())

        self.assertIsNone(u.queryId(obj))
        self.assertIs(u.queryId(obj, 42), 42)
        self.assertIs(u.queryId(P(), 42), 42)
        self.assertIsNone(u.queryObject(42))
        self.assertIs(u.queryObject(42, obj), obj)

        uid = u.register(obj)
        self.assertIs(u.getObject(uid), obj)
        self.assertIs(u.queryObject(uid), obj)
        self.assertEqual(u.getId(obj), uid)
        self.assertEqual(u.queryId(obj), uid)
        self.assertEqual(obj.iid, uid)

        # Check the id-added event:
        self.assertEqual(len(self.events), 1)
        event = self.events[-1]
        self.assertTrue(IIdAddedEvent.providedBy(event))
        self.assertIs(event.object, obj)
        self.assertIs(event.idmanager, u)
        self.assertEqual(event.id, uid)

        uid2 = u.register(obj)
        self.assertEqual(uid, uid2)

        u.unregister(obj)
        self.assertIsNone(obj.iid)
        self.assertRaises(ObjectMissingError, u.getObject, uid)
        self.assertRaises(IntIdMissingError, u.getId, obj)

        # Check the id-removed event:
        self.assertEqual(len(self.events), 3)
        event = self.events[-1]
        self.assertTrue(IIdRemovedEvent.providedBy(event))
        self.assertIs(event.object, obj)
        self.assertIs(event.idmanager, u)
        self.assertEqual(event.id, uid)

    def test_btree_long(self):
        # This is a somewhat arkward test, that *simulates* the border case
        # behaviour of the generateId method
        u = self.createIntIds()
        u._randrange = lambda x,y:int(2**31-1)

        # The chosen int is exactly the largest number possible that is
        # delivered by the randint call in the code
        obj = P()
        uid = u.register(obj)
        self.assertEqual(2**31-1, uid)
        # Make an explicit tuple here to avoid implicit type casts on 2**31-1
        # by the btree code
        self.assertIn(2**31-1, tuple(u.refs.keys()))

    def test_len_items(self):
        u = self.createIntIds()
        obj = P()

        self.assertEqual(len(u), 0)
        self.assertEqual(u.items(), [])
        self.assertEqual(list(u), [])

        uid = u.register(obj)
        self.assertEqual(len(u), 1)
        self.assertEqual(u.items(), [(uid, obj)])
        self.assertEqual(list(u), [uid])

        obj2 = P()

        uid2 = u.register(obj2)
        self.assertEqual(len(u), 2)
        result = u.items()
        expected = [(uid, obj), (uid2, obj2)]
        result.sort()
        expected.sort()
        self.assertEqual(result, expected)
        result = list(u)
        expected = [uid, uid2]
        result.sort()
        expected.sort()
        self.assertEqual(result, expected)

        u.unregister(obj)
        u.unregister(obj2)
        self.assertEqual(len(u), 0)
        self.assertEqual(u.items(), [])

    def test_getenrateId(self):
        u = self.createIntIds()
        self.assertEqual(u._v_nextid, None)
        id1 = u.generateId(None)
        self.assertIsNotNone(u._v_nextid)
        id2 = u.generateId(None)
        self.assertEqual(id1 + 1, id2)
        u.refs[id2 + 1] = "Taken"
        id3 = u.generateId(None)
        self.assertNotEqual(id3, id2 + 1)
        self.assertNotEqual(id3, id2)
        self.assertNotEqual(id3, id1)

    def test_cohabitation(self):
        # Show that two id utilities that use different attribute names
        # can assign different ids for a single object, without stomping
        # on each other.

        def generator(utility, odd):
            gen = utility.generateId
            def generateId(ob):
                iid = gen(ob)
                while (iid % 2) != int(odd):
                    iid = gen(ob)
                return iid
            return generateId

        # u1 only generates odd ids
        u1 = self.createIntIds("id1")
        u1.generateId = generator(u1, True)

        # u2 only generates even ids
        u2 = self.createIntIds("id2")
        u2.generateId = generator(u2, False)

        obj = P()

        uid1 = u1.register(obj)
        uid2 = u2.register(obj)

        self.assertNotEqual(uid1, uid2)
        self.assertEqual(obj.id1, uid1)
        self.assertEqual(obj.id2, uid2)

        self.assertIsNone(u1.queryObject(uid2))
        self.assertIsNone(u2.queryObject(uid1))

        # Unregistering from on utility has no affect on the attribute
        # assignment for the other.

        u1.unregister(obj)
        self.assertIsNone(obj.id1)
        self.assertEqual(obj.id2, uid2)
        self.assertIs(u2.getObject(uid2),obj)

    def test_duplicate_id_generation(self):
        # If an overridden ``generateId`` method generates an id that's
        # already used, the ``register`` method will detect that an
        # raise an exception.

        u = self.createIntIds()
        u.generateId = lambda ob: 42

        # Register an object, consuming the id our generator provides:
        obj = P()
        uid = u.register(obj)
        self.assertEqual(uid, 42)
        self.assertEqual(obj.iid, 42)

        # Check that the exception is raised:
        self.assertRaises(IntIdInUseError, u.register, P())

        # Verify that the original registration isn't compromised:
        self.assertIs(u.getObject(42), obj)
        self.assertIs(u.queryObject(42), obj)
        self.assertEqual(u.getId(obj), uid)
        self.assertEqual(u.queryId(obj), uid)

    def test_poskeyerror_propagates_getObject(self):
        from ZODB.POSException import POSKeyError

        class BadDict(object):
            def __getitem__(self, k):
                raise POSKeyError()

        u = self.createIntIds()
        u.refs = BadDict()

        self.assertRaises(POSKeyError, u.getObject, 1)

    def test_poskeyerror_propagates_queryId(self):
        from ZODB.POSException import POSKeyError

        class BadDict(object):
            def __getitem__(self, k):
                raise POSKeyError()

        u = self.createIntIds()
        obj = P()
        u.register(obj)
        u.refs = BadDict()

        self.assertRaises(POSKeyError, u.getId, obj)
        self.assertRaises(POSKeyError, u.queryId, obj)

    def test_unsettable_attr_doesnt_corrupt(self):
        # An error on setting the attribute doesn't leak a reference to
        # the object
        from ZODB.POSException import POSKeyError
        u = self.createIntIds()

        class WithSlots(object):
            __slots__ = ()

        obj = WithSlots()

        self.assertRaises(AttributeError, u.register, obj)
        self.assertEqual(0, len(u))

        class Broken(object):
            def __setattr__(self, name, value):

                raise POSKeyError()

        obj = Broken()
        self.assertRaises(POSKeyError, u.register, obj)
        self.assertEqual(0, len(u))


class TestIntIds64(TestIntIds):

    def createIntIds(self, attribute="iid"):
        return IntIds(attribute, family=BTrees.family64)


def test_suite():
    return unittest.TestSuite([
        unittest.makeSuite(TestIntIds),
        unittest.makeSuite(TestIntIds64),
    ])

test_suite() # coverage

if __name__ == '__main__': # pragma: no cover
    unittest.main()
