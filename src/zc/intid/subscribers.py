#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A set of subscribers for the object :mod:`zope.lifecycle` events.

There are two key differences from the subscribers that come with the
:mod:`zope.intid` package.

This does not register/unregister a :class:`zope.keyreference.IKeyReference`
with the intid utilities. Instead, it registers the actual object, and the
events that are broadcast are broadcast holding the actual object.

``IKeyReferenceces``, especially
:class:`~zope.keyreference.persistent.KeyReferenceToPersistent`, are
used for a few reasons. First, they provide a stable,
object-identity-based pointer to objects. To be identity based, this
pointer is independent of the equality and hashing algorithms of the
underlying object. Identity-based comparisons are necessary for the
classic :mod:`zope.intid` utility implementation which uses a second
``OIBTree`` to maintain the backreferece from object to assigned
intid (clearly you don't want two non-identical objects which happen
to compare equally *now* to get the same intid as that condition may
change). Likewise, these references are all defined to be mutually
comparable, no matter how they are implemented, a condition
necessary for them to all work together in a ``OIBTree``. Lastly,
these references are meant to be comparable during ZODB conflict
resolution (the original persistent objects probably won't be),
which, again, is a condition of the implementation using a
``OIBTree.``

A consequence of avoiding these references is that generally
persistent objects that are expected to have intids assigned *should
not* be used as keys in an ``OxBTree`` or stored in an ``OOSet.``
Instead, all such data structures *should* use the integer
variations (e.g., ``IISet``), with the intid as the key.

As a corollary to the previous point, this module *must* be used
with the intid utility from :mod:`zc.intid.utility`, (one
implementing :class:`zc.intid.interfaces.IIntIds`), which does not
depend on being able to use objects as keys in a BTree.

Therefore, this module looks for utilities registered for that
interface, not the :class:`zope.intid.interfaces.IIntIds`.

We do, however, keep a few things in common:

#. We do ensure that the object can be adapted to :class:`zope.keyreference.interface.IKeyReference`
    In the common case of persistent objects, this will ensure that the
    object is in the database and has a jar and oid, common needs.
#. We do broadcast the events from :mod:`zope.intid.interfaces`, even though
    the :mod:`zc.intid` package will broadcast its own events.
    There seems to be no reason not to and things like zope.catalog
    need them.

Configuring
===========

To configure, you need to include ``subscribers.zcml``:

.. code-block:: xml

    <!-- configure.zcml -->
    <!--
    If we load zope.intid, we get subscribers for the Object events
    that ensure all ILocation objects are registered/unregistered when
    they are added/removed, plus another set of events when they
    get/lose intids. This second set of events is meant to update
    zope.catalog. A consequence of this is that ILocation objects must
    be adaptable to KeyReferences when they are ObjectAdded (for
    purposes of zope.intid, which we don't care about, but this also
    ensures that they have ZODB Connections, which is good).

    We cannot use these subscribers as-is due to the way the use IKeyReference
    and try to register that. However, our subscribers *do* make sure that
    the given objects can be adapted to IKeyReference because that's useful and
    may be required by catalogs or other subscribers.
    -->
    <exclude package="zope.intid" file="subscribers.zcml" />
    <include package="zope.intid" />

    <include package="zope.keyreference" />

    <!--
    zc.intid fires a different set of events when objects gain/lose
    intids.
    -->
    <include package="zc.intid" />

    <!--
    Make zc.intid utilities compatible with zope.intid utilities.
    -->
    <include package="zc.intid" file="zope-intid.zcml" />

    <!-- To hook them up to the Object events, we need to include the file -->
    <include package="zc.intid" file="subscribers.zcml" />

"""
from __future__ import print_function, absolute_import, division

from zope import component

from zope.component import handle

from zope.lifecycleevent.interfaces import IObjectAddedEvent
from zope.lifecycleevent.interfaces import IObjectRemovedEvent

from zope.location.interfaces import ILocation

from zope.event import notify

from zope.intid.interfaces import IntIdAddedEvent
from zope.intid.interfaces import IntIdRemovedEvent

from zope.keyreference.interfaces import IKeyReference

from zc.intid.interfaces import IIntIds
from zc.intid.interfaces import BeforeIdRemovedEvent
from zc.intid.interfaces import AfterIdAddedEvent

def _utilities_and_key(ob):
    utilities = tuple(component.getAllUtilitiesRegisteredFor(IIntIds))
    # Don't even bother trying to adapt if no utilities
    return utilities, IKeyReference(ob, None) if utilities else None


@component.adapter(ILocation, IObjectAddedEvent)
def addIntIdSubscriber(ob, event):
    """
    Registers the object in all unique id utilities and fires
    an event for the catalogs. Notice that each utility will
    fire :class:`zc.intid.interfaces.IIntIdAddedEvent`; this subscriber
    will then fire one single :class:`zope.intid.interfaces.IIntIdAddedEvent`,
    followed by one single :class:`zc.intid.interfaces.IAfterIdAddedEvent`; this
    gives a guaranteed order such that :mod:`zope.catalog` and other Zope
    event listeners will have fired.
    """
    utilities, key = _utilities_and_key(ob)
    if not utilities or key is None:
        return

    idmap = {}

    for utility in utilities:
        idmap[utility] = utility.register(ob)

    # Notify the catalogs that this object was added.
    notify(IntIdAddedEvent(ob, event, idmap))
    notify(AfterIdAddedEvent(ob, event, idmap))

@component.adapter(ILocation, IObjectRemovedEvent)
def removeIntIdSubscriber(ob, event):
    """
    Removes the unique ids registered for the object in all the unique
    id utilities.

    Just before this happens (for the first time), an
    :class:`zc.intid.interfaces.IBeforeIdRemovedEvent` is fired,
    followed by an :class:`zope.intid.interfaces.IIntIdRemovedEvent`.
    Notice that this is fired before the id is actually removed from
    any utility, giving other subscribers time to do their cleanup.

    Before each utility removes its registration, it will fire
    :class:`zc.intid.interfaces.IIntIdRemovedEvent`. This gives a
    guaranteed order such that :mod:`zope.catalog` and other Zope
    event listeners will have fired.
    """
    utilities, key = _utilities_and_key(ob)
    if not utilities or key is None:
        return

    # Notify the catalogs that this object is about to be removed,
    # if we actually find something to remove
    fired_event = False

    for utility in utilities:
        if not fired_event and utility.queryId(ob) is not None:
            fired_event = True
            notify(BeforeIdRemovedEvent(ob, event))
            notify(IntIdRemovedEvent(ob, event))
        try:
            utility.unregister(ob)
        except KeyError: # pragma: no cover
            # Ignoring POSKeyError and broken registrations
            pass

def intIdEventNotify(event):
    """
    Event subscriber to dispatch IntIdEvent to interested adapters.

    See subscribers.zcml for its registrations (it handles two types of events).
    """
    handle(event.object, event)
