#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A set of subscribers for the object :mod:`zope.lifecycleevent` events.

These subscribers take care of registering and unregistering objects
with all available :class:`~zc.intid.interfaces.IIntIds` utilities
when :class:`~zope.lifecycleevent.interfaces.IObjectAddedEvent` and
:class:`~zope.lifecycleevent.interfaces.IObjectRemovedEvent` events are
fired, respectively.

These subscribers and events are modeled on those that come with
:mod:`zope.intid` and are intended to be used (optionally) as drop-in
replacements for them. This allows zc.intid to work in conjunction
with things written for :mod:`zope.intid`, such as
:mod:`zope.catalog`.

In particular, a few things are done just like :mod:`zope.intid`:

#. We do ensure that the object can be adapted to
   :class:`~zope.keyreference.interface.IKeyReference` before doing
   any processing (even though we don't register that in the utility
   or otherwise use it.) In the common case of persistent objects,
   this will ensure that the object is in the database and has a jar
   and oid, common needs.

#. We do broadcast the events from :mod:`zope.intid.interfaces`, even though
   the utility will broadcast its own events. Thus these subscribers
   generate at least three events for every lifecycle event.
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
    fire :class:`zc.intid.interfaces.IIdAddedEvent`; this subscriber
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
    :class:`zc.intid.interfaces.IIdRemovedEvent`. This gives a
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
