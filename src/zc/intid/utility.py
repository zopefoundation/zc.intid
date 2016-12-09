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

from zc.intid.interfaces import AddedEvent
from zc.intid.interfaces import IIntIds
from zc.intid.interfaces import IIntIdsSubclass
from zc.intid.interfaces import IntIdMismatchError
from zc.intid.interfaces import IntIdInUseError
from zc.intid.interfaces import RemovedEvent

from zope.event import notify

from zope.interface import implementer

from zope.intid.interfaces import IntIdMissingError
from zope.intid.interfaces import ObjectMissingError
try:
    # POSKeyError is a subclass of KeyError; in the cases where we
    # catch KeyError for an item missing from a BTree, we still
    # want to propagate this exception that indicates a corrupt database
    # (as opposed to a corrupt IntIds)
    from ZODB.POSException import POSKeyError as _POSKeyError
except ImportError: # pragma: no cover (we run tests with ZODB installed)
    # In practice, ZODB will probably be installed. But if not,
    # then POSKeyError can never be generated, so use a unique
    # exception that we'll never catch.
    class _POSKeyError(BaseException):
        pass

from zope.security.proxy import removeSecurityProxy as unwrap

import BTrees
import persistent
import random

@implementer(IIntIds, IIntIdsSubclass)
class IntIds(persistent.Persistent):
    """This utility provides a two way mapping between objects and
    integer ids.

    The objects are stored directly in the internal structures.

    """

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
        try:
            return self.refs[id]
        except _POSKeyError:
            raise
        except KeyError:
            raise ObjectMissingError(id)

    def queryObject(self, id, default=None):
        if id in self.refs:
            return self.refs[id]
        return default

    def getId(self, ob):
        unwrapped = unwrap(ob)
        uid = getattr(unwrapped, self.attribute, None)
        if uid is None:
            raise IntIdMissingError(ob)
        if uid not in self.refs or self.refs[uid] is not unwrapped:
            # not an id that matches
            raise IntIdMismatchError(ob)
        return uid

    def queryId(self, ob, default=None):
        try:
            return self.getId(ob)
        except _POSKeyError:
            raise
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
                raise IntIdInUseError("id generator returned used id")
        self.refs[uid] = ob
        try:
            setattr(ob, self.attribute, uid)
        except:
            # cleanup our mess
            del self.refs[uid]
            raise
        notify(AddedEvent(ob, self, uid))
        return uid

    def unregister(self, ob):
        ob = unwrap(ob)
        uid = self.queryId(ob)
        if uid is None:
            return
        # This should not raise KeyError, we checked that in queryId
        del self.refs[uid]
        setattr(ob, self.attribute, None)
        notify(RemovedEvent(ob, self, uid))
