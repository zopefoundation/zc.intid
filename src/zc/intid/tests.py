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
import sys

import BTrees
from persistent.interfaces import IPersistent
import unittest

from zc.intid import AfterIdAddedEvent
from zc.intid import BeforeIdRemovedEvent
from zc.intid import IIdAddedEvent
from zc.intid import IIdEvent
from zc.intid import IIdRemovedEvent
from zc.intid import IIntIds
from zc.intid import IIntIdsSubclass
from zc.intid import ISubscriberEvent

from zc.intid.subscribers import addIntIdSubscriber
from zc.intid.subscribers import intIdEventNotify
from zc.intid.subscribers import removeIntIdSubscriber

from zc.intid.utility import AddedEvent
from zc.intid.utility import IntIds
from zc.intid.utility import RemovedEvent

from zope.component import getSiteManager
from zope.component import getGlobalSiteManager
from zope.component import provideAdapter
from zope.component import provideHandler
from zope.component import testing, eventtesting

from zope.component.interfaces import ISite, IComponentLookup

from zope.interface import Interface
from zope.interface.verify import verifyObject

from zope.intid.interfaces import IIntIdEvent
from zope.intid.interfaces import IntIdAddedEvent
from zope.intid.interfaces import IntIdRemovedEvent
try:
    from zope.intid.interfaces import ObjectMissingError
except ImportError:
    ObjectMissingError = KeyError

from zope.keyreference.interfaces import IKeyReference

from zope.lifecycleevent import ObjectAddedEvent
from zope.lifecycleevent import ObjectRemovedEvent

from zope.security.checker import CheckerPublic
from zope.security.proxy import Proxy

from zope.site.folder import rootFolder
from zope.site.hooks import setSite, setHooks, resetHooks
from zope.site.interfaces import IFolder
from zope.site.site import SiteManagerAdapter, LocalSiteManager

from zope.traversing.testing import setUp as traversingSetUp

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
        with self.assertRaises(KeyError) as ex:
            u.getId(proxied)
        self.assertIs(ex.exception.args[0], proxied)

        obj.iid = -1
        with self.assertRaises(KeyError) as ex:
            u.getId(proxied)
        self.assertIs(ex.exception.args[0], proxied)


        obj = P()
        obj.iid = iid
        proxied = Proxy(obj,
                        CheckerPublic)
        with self.assertRaises(KeyError) as ex:
            u.getId(proxied)
        self.assertIs(ex.exception.args[0], proxied)

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

        self.assertIsNone(u.queryId(obj))
        self.assertIsNone(u.unregister(obj))
        self.assertRaises(KeyError, u.getId, obj)

    def test(self):
        u = self.createIntIds()
        obj = P()

        self.assertRaises(KeyError, u.getId, obj)
        self.assertRaises(KeyError, u.getId, P())

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
        self.assertRaises(KeyError, u.getObject, uid)
        self.assertRaises(KeyError, u.getId, obj)

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
        self.assertRaises(ValueError, u.register, P())

        # Verify that the original registration isn't compromised:
        self.assertIs(u.getObject(42), obj)
        self.assertIs(u.queryObject(42), obj)
        self.assertEqual(u.getId(obj), uid)
        self.assertEqual(u.queryId(obj), uid)


class TestIntIds64(TestIntIds):

    def createIntIds(self, attribute="iid"):
        return IntIds(attribute, family=BTrees.family64)


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

def createSiteManager(folder, setsite=False):
    if not ISite.providedBy(folder):
        folder.setSiteManager(LocalSiteManager(folder))
    if setsite:
        setSite(folder)
    return folder.getSiteManager()

class KeyReferenceStub(object):

    def __init__(self, obj):
        self.obj = obj

class ReferenceSetupMixin(object):
    """Registers adapters ILocation->IConnection and IPersistent->IReference"""

    def setUp(self):
        testing.setUp()
        eventtesting.setUp()
        traversingSetUp()
        setHooks()
        provideAdapter(SiteManagerAdapter, (Interface,), IComponentLookup)

        self.root = rootFolder()
        createSiteManager(self.root, setsite=True)

        provideAdapter(
            KeyReferenceStub, (IPersistent, ), IKeyReference)

    def tearDown(self):
        resetHooks()
        setSite()
        testing.tearDown()
        self.assertIs(getSiteManager(), getGlobalSiteManager())


class TestSubscribers(ReferenceSetupMixin, unittest.TestCase):

    __parent__ = None
    __name__ = None

    def setUp(self):
        from zope.site.folder import Folder

        ReferenceSetupMixin.setUp(self)

        sm = getSiteManager(self.root)
        self.utility = IntIds("iid")
        sm.registerUtility(self.utility, name='1', provided=IIntIds)

        self.root['folder1'] = Folder()
        self.root['folder1']['folder1_1'] = self.folder1_1 = Folder()
        self.root['folder1']['folder1_1']['folder1_1_1'] = Folder()

        sm1_1 = createSiteManager(self.folder1_1)
        self.utility1 = IntIds("liid")
        sm1_1.registerUtility(self.utility1, name='2', provided=IIntIds)

        provideHandler(intIdEventNotify, (IIdEvent,))
        provideHandler(intIdEventNotify, (IIntIdEvent,))

        self.raw_events = []
        self.obj_events = []

        def obj_event(*args):
            self.obj_events.append(args)

        provideHandler(self.raw_events.append, [IIntIdEvent])
        provideHandler(self.raw_events.append, [IIdEvent])

        provideHandler(obj_event, [IFolder, IIntIdEvent])
        provideHandler(obj_event, [IFolder, IIdEvent])

        provideHandler(self.raw_events.append, [ISubscriberEvent])

    def test_no_KeyReference(self):
        # Nothing happens for something that can't be a KeyReference
        addIntIdSubscriber(self, ObjectAddedEvent(self))
        removeIntIdSubscriber(self, ObjectRemovedEvent(self))

        self.assertEqual([], self.raw_events)
        self.assertEqual([], self.obj_events)

    def test_removeIntIdSubscriber(self):
        parent_folder = self.root['folder1']['folder1_1']
        folder = self.root['folder1']['folder1_1']['folder1_1_1']
        id = self.utility.register(folder)
        id1 = self.utility1.register(folder)
        self.assertEqual(self.utility.getObject(id), folder)
        self.assertEqual(self.utility1.getObject(id1), folder)
        setSite(self.folder1_1)

        events = self.raw_events
        objevents = self.obj_events

        del events[:]
        del objevents[:]

        # This should unregister the object in all utilities, not just the
        # nearest one.
        removeIntIdSubscriber(folder, ObjectRemovedEvent(parent_folder))

        self.assertRaises(ObjectMissingError, self.utility.getObject, id)
        self.assertRaises(ObjectMissingError, self.utility1.getObject, id1)

        self.assertEqual([BeforeIdRemovedEvent,
                          IntIdRemovedEvent,
                          RemovedEvent,
                          RemovedEvent],
                         [type(x) for x in events])
        for e in events:
            self.assertEqual(e.object, folder)

        for e in events[:2]:
            self.assertEqual(e.original_event.object, parent_folder)

        self.assertEqual([IntIdRemovedEvent,
                          RemovedEvent,
                          RemovedEvent],
                         [type(x[1]) for x in objevents])
        self.assertEqual(objevents[0][0], folder)
        self.assertEqual(objevents[0][1].object, folder)
        self.assertEqual(objevents[0][1].original_event.object, parent_folder)

    def test_addIntIdSubscriber(self):
        parent_folder = self.root['folder1']['folder1_1']
        folder = self.root['folder1']['folder1_1']['folder1_1_1']
        setSite(self.folder1_1)

        events = self.raw_events
        objevents = self.obj_events

        del events[:]
        del objevents[:]

        # This should register the object in all utilities, not just the
        # nearest one.
        addIntIdSubscriber(folder, ObjectAddedEvent(parent_folder))

        # Check that the folder got registered
        id = self.utility.getId(folder)
        id1 = self.utility1.getId(folder)


        self.assertEqual([AddedEvent,
                          AddedEvent,
                          IntIdAddedEvent,
                          AfterIdAddedEvent,],
                         [type(x) for x in events])
        for e in events:
            self.assertEqual(e.object, folder)

        for e in events[2:]:
            self.assertEqual(e.original_event.object, parent_folder)

        self.assertEqual([AddedEvent,
                          AddedEvent,
                          IntIdAddedEvent,],
                         [type(x[1]) for x in objevents])

        for e in objevents:
            self.assertEqual(e[1].object, folder)
            self.assertEqual(e[0], folder)

        self.assertEqual(objevents[2][1].original_event.object, parent_folder)

        idmap = events[2].idmap
        self.assertEqual(len(idmap), 2)
        self.assertEqual(idmap[self.utility], id)
        self.assertEqual(idmap[self.utility1], id1)

        for e in events[:2]:
            self.assertIn(e.idmanager, idmap)
            self.assertEqual(e.id, e.idmanager.getId(e.object))


def test_suite():
    return unittest.TestSuite([
        unittest.makeSuite(TestIntIds),
        unittest.makeSuite(TestIntIds64),
        unittest.makeSuite(TestZopeIntidZcml),
        unittest.makeSuite(TestSubscribers),
    ])

test_suite() # coverage

if __name__ == '__main__': # pragma: no cover
    unittest.main()
