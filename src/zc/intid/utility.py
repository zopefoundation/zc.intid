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
"""Unique id utility.

This utility assigns unique integer ids to objects and allows lookups
by object and by id.

This functionality can be used in cataloging.

"""

import BTrees
import persistent
import random
import zc.intid
import zope.event
import zope.interface
import zope.security.proxy


unwrap = zope.security.proxy.removeSecurityProxy


class IntIds(persistent.Persistent):
    """This utility provides a two way mapping between objects and
    integer ids.

    The objects are stored directly in the internal structures.

    """

    zope.interface.implements(
        zc.intid.IIntIds,
        zc.intid.IIntIdsSubclass)

    _v_nextid = None

    _randrange = random.randrange

    family = BTrees.family32

    def __init__(self, attribute, family=None):
        if family is not None:
            self.family = family
        self.attribute = attribute
        self.refs = self.family.IO.BTree()

    def __len__(self):
        return len(self.refs)

    def items(self):
        return list(self.refs.items())

    def __iter__(self):
        return self.refs.iterkeys()

    def getObject(self, id):
        return self.refs[id]

    def queryObject(self, id, default=None):
        if id in self.refs:
            return self.refs[id]
        return default

    def getId(self, ob):
        uid = getattr(unwrap(ob), self.attribute, None)
        if uid is None:
            raise KeyError(ob)
        if self.refs[uid] is not ob:
            # not an id that matches
            raise KeyError(ob)
        return uid

    def queryId(self, ob, default=None):
        try:
            return self.getId(ob)
        except KeyError:
            return default

    def generateId(self, ob):
        """Generate an id which is not yet taken.

        This tries to allocate sequential ids so they fall into the same
        BTree bucket, and randomizes if it stumbles upon a used one.

        """
        while True:
            if self._v_nextid is None:
                self._v_nextid = self._randrange(0, self.family.maxint)
            uid = self._v_nextid
            self._v_nextid += 1
            if uid not in self.refs:
                return uid
            self._v_nextid = None

    def register(self, ob):
        ob = unwrap(ob)
        uid = self.queryId(ob)
        if uid is None:
            uid = self.generateId(ob)
            if uid in self.refs:
                raise ValueError("id generator returned used id")
        self.refs[uid] = ob
        setattr(ob, self.attribute, uid)
        zope.event.notify(AddedEvent(ob, self, uid))
        return uid

    def unregister(self, ob):
        ob = unwrap(ob)
        uid = self.queryId(ob)
        if uid is None:
            return
        del self.refs[uid]
        setattr(ob, self.attribute, None)
        zope.event.notify(RemovedEvent(ob, self, uid))


class Event(object):

    def __init__(self, object, idmanager, id):
        self.object = object
        self.idmanager = idmanager
        self.id = id


class AddedEvent(Event):
    zope.interface.implements(zc.intid.IIdAddedEvent)


class RemovedEvent(Event):
    zope.interface.implements(zc.intid.IIdRemovedEvent)
