##############################################################################
#
# Copyright (c) 2001, 2002, 2009 Zope Foundation and Contributors.
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
"""\
Tests for the unique id utility.

"""

import BTrees
import unittest
import zc.intid
import zc.intid.utility
import zope.event
import zope.interface.verify


class P(object):
    pass


class TestIntIds(unittest.TestCase):

    def createIntIds(self, attribute="iid"):
        return zc.intid.utility.IntIds(attribute)

    def setUp(self):
        self.events = []
        zope.event.subscribers.append(self.events.append)

    def tearDown(self):
        zope.event.subscribers.remove(self.events.append)

    def test_interface(self):
        u = self.createIntIds()
        zope.interface.verify.verifyObject(zc.intid.IIntIds, u)
        zope.interface.verify.verifyObject(zc.intid.IIntIdsSubclass, u)

    def test_non_keyreferences(self):
        #
        # This test, copied from zope.intid, was used in that context to
        # determine that failed adaptaions to IKeyReference did not
        # cause unexpected behaviors from the API.
        #
        # In zc.intid, this simple ensures that the behaviors don't
        # differ from that of zope.intid.
        #
        u = self.createIntIds()
        obj = object()

        self.assert_(u.queryId(obj) is None)
        self.assert_(u.unregister(obj) is None)
        self.assertRaises(KeyError, u.getId, obj)

    def test(self):
        u = self.createIntIds()
        obj = P()

        self.assertRaises(KeyError, u.getId, obj)
        self.assertRaises(KeyError, u.getId, P())

        self.assert_(u.queryId(obj) is None)
        self.assert_(u.queryId(obj, 42) is 42)
        self.assert_(u.queryId(P(), 42) is 42)
        self.assert_(u.queryObject(42) is None)
        self.assert_(u.queryObject(42, obj) is obj)

        uid = u.register(obj)
        self.assert_(u.getObject(uid) is obj)
        self.assert_(u.queryObject(uid) is obj)
        self.assertEquals(u.getId(obj), uid)
        self.assertEquals(u.queryId(obj), uid)
        self.assertEquals(obj.iid, uid)

        # Check the id-added event:
        self.assertEquals(len(self.events), 1)
        event = self.events[-1]
        self.assert_(zc.intid.IIdAddedEvent.providedBy(event))
        self.assert_(event.object is obj)
        self.assert_(event.idmanager is u)
        self.assertEquals(event.id, uid)

        uid2 = u.register(obj)
        self.assertEquals(uid, uid2)

        u.unregister(obj)
        self.assert_(obj.iid is None)
        self.assertRaises(KeyError, u.getObject, uid)
        self.assertRaises(KeyError, u.getId, obj)

        # Check the id-removed event:
        self.assertEquals(len(self.events), 3)
        event = self.events[-1]
        self.assert_(zc.intid.IIdRemovedEvent.providedBy(event))
        self.assert_(event.object is obj)
        self.assert_(event.idmanager is u)
        self.assertEquals(event.id, uid)

    def test_btree_long(self):
        # This is a somewhat arkward test, that *simulates* the border case
        # behaviour of the generateId method
        u = self.createIntIds()
        u._randrange = lambda x,y:int(2**31-1)

        # The chosen int is exactly the largest number possible that is
        # delivered by the randint call in the code
        obj = P()
        uid = u.register(obj)
        self.assertEquals(2**31-1, uid)
        # Make an explicit tuple here to avoid implicit type casts on 2**31-1
        # by the btree code
        self.failUnless(2**31-1 in tuple(u.refs.keys()))

    def test_len_items(self):
        u = self.createIntIds()
        obj = P()

        self.assertEquals(len(u), 0)
        self.assertEquals(u.items(), [])
        self.assertEquals(list(u), [])

        uid = u.register(obj)
        self.assertEquals(len(u), 1)
        self.assertEquals(u.items(), [(uid, obj)])
        self.assertEquals(list(u), [uid])

        obj2 = P()
        obj2.__parent__ = obj

        uid2 = u.register(obj2)
        self.assertEquals(len(u), 2)
        result = u.items()
        expected = [(uid, obj), (uid2, obj2)]
        result.sort()
        expected.sort()
        self.assertEquals(result, expected)
        result = list(u)
        expected = [uid, uid2]
        result.sort()
        expected.sort()
        self.assertEquals(result, expected)

        u.unregister(obj)
        u.unregister(obj2)
        self.assertEquals(len(u), 0)
        self.assertEquals(u.items(), [])

    def test_getenrateId(self):
        u = self.createIntIds()
        self.assertEquals(u._v_nextid, None)
        id1 = u.generateId(None)
        self.assert_(u._v_nextid is not None)
        id2 = u.generateId(None)
        self.assert_(id1 + 1, id2)
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
        self.assertEquals(obj.id1, uid1)
        self.assertEquals(obj.id2, uid2)

        self.assert_(u1.queryObject(uid2) is None)
        self.assert_(u2.queryObject(uid1) is None)

        # Unregistering from on utility has no affect on the attribute
        # assignment for the other.

        u1.unregister(obj)
        self.assert_(obj.id1 is None)
        self.assertEquals(obj.id2, uid2)
        self.assert_(u2.getObject(uid2) is obj)

    def test_duplicate_id_generation(self):
        # If an overridden ``generateId`` method generates an id that's
        # already used, the ``register`` method will detect that an
        # raise an exception.

        u = self.createIntIds()
        u.generateId = lambda ob: 42

        # Register an object, consuming the id our generator provides:
        obj = P()
        uid = u.register(obj)
        self.assertEquals(uid, 42)
        self.assertEquals(obj.iid, 42)

        # Check that the exception is raised:
        self.assertRaises(ValueError, u.register, P())

        # Verify that the original registration isn't compromised:
        self.assert_(u.getObject(42) is obj)
        self.assert_(u.queryObject(42) is obj)
        self.assertEquals(u.getId(obj), uid)
        self.assertEquals(u.queryId(obj), uid)


class TestIntIds64(TestIntIds):

    def createIntIds(self, attribute="iid"):
        return zc.intid.utility.IntIds(attribute, family=BTrees.family64)


def test_suite():
    return unittest.TestSuite([
        unittest.makeSuite(TestIntIds),
        unittest.makeSuite(TestIntIds64),
        ])

if __name__ == '__main__':
    unittest.main()
