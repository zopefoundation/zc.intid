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
Tests for the lifecycle subscribers.
"""

from persistent.interfaces import IPersistent
import unittest

import zc.intid

from zc.intid.interfaces import AddedEvent
from zc.intid.interfaces import AfterIdAddedEvent
from zc.intid.interfaces import BeforeIdRemovedEvent
from zc.intid.interfaces import IIdEvent
from zc.intid.interfaces import IIntIds
from zc.intid.interfaces import ISubscriberEvent
from zc.intid.interfaces import RemovedEvent

from zc.intid.subscribers import addIntIdSubscriber
from zc.intid.subscribers import removeIntIdSubscriber

from zc.intid.utility import IntIds

from zope.component import getSiteManager
from zope.component import getGlobalSiteManager
from zope.component import handle
from zope.component import provideAdapter
from zope.component import provideHandler
from zope.component import testing as componenttesting
from zope.component import eventtesting

from zope.component.interfaces import ISite, IComponentLookup

from zope.configuration import xmlconfig

from zope.interface import Interface

from zope.intid.interfaces import IIntIdEvent
from zope.intid.interfaces import IntIdAddedEvent
from zope.intid.interfaces import IntIdRemovedEvent
from zope.intid.interfaces import ObjectMissingError

from zope.keyreference.interfaces import IKeyReference

from zope.lifecycleevent import ObjectAddedEvent
from zope.lifecycleevent import ObjectRemovedEvent


from zope.site.folder import rootFolder, Folder
from zope.site.hooks import setSite, setHooks, resetHooks
from zope.site.interfaces import IFolder
from zope.site.site import SiteManagerAdapter, LocalSiteManager

from zope.traversing.testing import setUp as traversingSetUp


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
        componenttesting.setUp()
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
        componenttesting.tearDown()
        self.assertIs(getSiteManager(), getGlobalSiteManager())


class TestSubscribers(ReferenceSetupMixin, unittest.TestCase):

    __parent__ = None
    __name__ = None

    def setUp(self):
        ReferenceSetupMixin.setUp(self)

        # Install the event handlers
        xmlconfig.file('subscribers.zcml', package=zc.intid)

        sm = getSiteManager(self.root)
        self.utility = IntIds("iid")
        sm.registerUtility(self.utility, name='1', provided=IIntIds)

        self.root['folder1'] = Folder()
        self.root['folder1']['folder1_1'] = self.folder1_1 = Folder()
        self.root['folder1']['folder1_1']['folder1_1_1'] = self.child_folder = Folder()

        sm1_1 = createSiteManager(self.folder1_1)
        self.utility1 = IntIds("liid")
        sm1_1.registerUtility(self.utility1, name='2', provided=IIntIds)


        self.raw_events = []
        self.obj_events = []

        def obj_event(*args):
            self.obj_events.append(args)

        provideHandler(self.raw_events.append, [IIntIdEvent])
        provideHandler(self.raw_events.append, [IIdEvent])

        provideHandler(obj_event, [IFolder, IIntIdEvent])
        provideHandler(obj_event, [IFolder, IIdEvent])

        provideHandler(self.raw_events.append, [ISubscriberEvent])

        setSite(self.folder1_1)

    def test_no_KeyReference(self):
        # Nothing happens for something that can't be a KeyReference
        addIntIdSubscriber(self, ObjectAddedEvent(self))
        removeIntIdSubscriber(self, ObjectRemovedEvent(self))

        self.assertEqual([], self.raw_events)
        self.assertEqual([], self.obj_events)

    def test_removeIntIdSubscriber(self):
        # Register, so we have something to remove
        utility_id = self.utility.register(self.child_folder)
        utility1_id = self.utility1.register(self.child_folder)
        self.assertEqual(self.utility.getObject(utility_id), self.child_folder)
        self.assertEqual(self.utility1.getObject(utility1_id), self.child_folder)
        # Clear events
        del self.raw_events[:]
        del self.obj_events[:]

        # This should unregister the object in all utilities, not just the
        # nearest one. Go through "handle" instead of directly calling `removeIntIdSubscriber`
        # to be sure the ZCML is correct
        handle(self.child_folder, ObjectRemovedEvent(self.folder1_1))

        self.assertRaises(ObjectMissingError, self.utility.getObject, utility_id)
        self.assertRaises(ObjectMissingError, self.utility1.getObject, utility1_id)

        self.assertEqual([BeforeIdRemovedEvent,
                          IntIdRemovedEvent,
                          RemovedEvent,
                          RemovedEvent],
                         [type(x) for x in self.raw_events])
        for e in self.raw_events:
            self.assertEqual(e.object, self.child_folder)

        for e in self.raw_events[:2]:
            self.assertEqual(e.original_event.object, self.folder1_1)

        self.assertEqual([IntIdRemovedEvent,
                          RemovedEvent,
                          RemovedEvent],
                         [type(x[1]) for x in self.obj_events])
        self.assertEqual(self.obj_events[0][0], self.child_folder)
        self.assertEqual(self.obj_events[0][1].object, self.child_folder)
        self.assertEqual(self.obj_events[0][1].original_event.object, self.folder1_1)

    def test_addIntIdSubscriber(self):
        # This should register the object in all utilities, not just the
        # nearest one. Go through "handle" instead of directly calling `addIntIdSubscriber`
        # to be sure the ZCML is correct
        handle(self.child_folder, ObjectAddedEvent(self.folder1_1))

        # Check that the folder got registered
        utility_id = self.utility.getId(self.child_folder)
        utility1_id = self.utility1.getId(self.child_folder)


        self.assertEqual([AddedEvent,
                          AddedEvent,
                          IntIdAddedEvent,
                          AfterIdAddedEvent,],
                         [type(x) for x in self.raw_events])
        for e in self.raw_events:
            self.assertEqual(e.object, self.child_folder)

        for e in self.raw_events[2:]:
            self.assertEqual(e.original_event.object, self.folder1_1)

        self.assertEqual([AddedEvent,
                          AddedEvent,
                          IntIdAddedEvent,],
                         [type(x[1]) for x in self.obj_events])

        for e in self.obj_events:
            self.assertEqual(e[1].object, self.child_folder)
            self.assertEqual(e[0], self.child_folder)

        self.assertEqual(self.obj_events[2][1].original_event.object, self.folder1_1)

        idmap = self.raw_events[2].idmap
        self.assertEqual(len(idmap), 2)
        self.assertEqual(idmap[self.utility], utility_id)
        self.assertEqual(idmap[self.utility1], utility1_id)

        for e in self.raw_events[:2]:
            self.assertIn(e.idmanager, idmap)
            self.assertEqual(e.id, e.idmanager.getId(e.object))


def test_suite():
    return unittest.TestSuite([
        unittest.makeSuite(TestSubscribers),
    ])

test_suite() # coverage

if __name__ == '__main__': # pragma: no cover
    unittest.main()
