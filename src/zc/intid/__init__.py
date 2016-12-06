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
"""
Interfaces for the unique id utility.

Note that most of these interfaces present identical method signatures
to those of their :mod:`zope.intid` counterparts.  This includes everything
that comprises the :class:`IIntIds` interface.

Note that the contracts for these APIs differs, primarily in not
requiring :class:`zope.keyreference.interfaces.IKeyReference` support.

The :class:`IIntIdsSubclass` and event interfaces are new.

"""

import zope.interface


class IIntIdsQuery(zope.interface.Interface):

    def getObject(uid):
        """Return an object by its unique id"""

    def getId(ob):
        """Get a unique id of an object.
        """

    def queryObject(uid, default=None):
        """Return an object by its unique id

        Return the default if the uid isn't registered
        """

    def queryId(ob, default=None):
        """Get a unique id of an object.

        Return the default if the object isn't registered
        """

    def __iter__():
        """Return an iteration on the ids"""


class IIntIdsSet(zope.interface.Interface):

    def register(ob):
        """Register an object and returns a unique id generated for it.

        If the object is already registered, its id is returned anyway.

        If not already registered, the registration is made and an
        ``IIdAddedEvent`` is generated.

        """

    def unregister(ob):
        """Remove the object from the indexes.

        KeyError is raised if ob is not registered previously.

        An ``IIdRemovedEvent`` is triggered for successful
        unregistrations.

        """

class IIntIdsManage(zope.interface.Interface):
    """Some methods used by the view."""

    def __len__():
        """Return the number of objects indexed."""

    def items():
        """Return a list of (id, object) pairs."""


class IIntIds(IIntIdsSet, IIntIdsQuery, IIntIdsManage):
    """A utility that assigns unique ids to objects.

    Allows to query object by id and id by object.
    """


class IIntIdsSubclass(zope.interface.Interface):
    """Additional interface that subclasses can usefully use."""

    family = zope.interface.Attribute(
        """BTree family used for this id utility.

        This will be either BTree.family32 or BTree.family64.

        This may not be modified, but may be used to create additional
        structures of the same integer family as the ``refs`` structure.

        """)

    refs = zope.interface.Attribute(
        """BTree mapping from id to object.

        Subclasses can use this to determine whether an id has already
        been assigned.

        This should not be directly modified by subclasses.

        """)

    def generateId(ob):
        """Return a new iid that isn't already used.

        ``ob`` is the object the id is being generated for.

        The default behavior is to generate arbitrary integers without
        reference to the objects they're generated for.

        This method may be overriden.

        """


class IIdEvent(zope.interface.Interface):
    """Generic base interface for IntId-related events"""

    object = zope.interface.Attribute(
        "The object related to this event")

    idmanager = zope.interface.Attribute(
        "The int id utility generating the event.")

    id = zope.interface.Attribute(
        "The id that is being assigned or unassigned.")


class IIdRemovedEvent(IIdEvent):
    """
    A unique id will be removed.

    The event is published before the unique id is removed
    from the utility so that the indexing objects can unindex the object.
    """


class IIdAddedEvent(IIdEvent):
    """
    A unique id has been added.

    The event gets sent when an object is registered in a unique id
    utility.
    """

class ISubscriberEvent(zope.interface.Interface):
    """
    An event fired by the subscribers in relation to another event.
    """

    object = zope.interface.Attribute(
        "The object related to this event")

    original_event = zope.interface.Attribute(
        "The ObjectEvent related to this event")

class IAfterIdAddedEvent(ISubscriberEvent):
    """
    Fired after all utilities have registered unique ids.

    This event is guaranteed to be the last event fired by the
    subscribers that register ids. It will be fired exactly once, no
    matter how many utilities registered ids.
    """

    idmap = zope.interface.Attribute(
        "The dictionary that holds an (utility -> id) mapping of created ids")

class IBeforeIdRemovedEvent(ISubscriberEvent):
    """
    Fired before any utility removes an object's unique ID.

    This event is guaranteed to be the first event fired by the
    subscriber that removes IDs. It will only be fired if at least
    one utility will remove an ID.
    """

@zope.interface.implementer(IBeforeIdRemovedEvent)
class BeforeIdRemovedEvent(object):
    """
    The event which is published before the unique id is removed
    from the utility so that the catalogs can unindex the object.
    """

    def __init__(self, o, event):
        self.object = o
        self.original_event = event

@zope.interface.implementer(IAfterIdAddedEvent)
class AfterIdAddedEvent(object):
    """
    The event which gets sent when an object is registered in a
    unique id utility.
    """

    def __init__(self, o, event, idmap=None):
        self.object = o
        self.idmap = idmap
        self.original_event = event
