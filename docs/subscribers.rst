=============================
 Lifecycle Event Subscribers
=============================

.. automodule:: zc.intid.subscribers
                :no-members:

.. _configuring:

Configuring
===========

To configure, you need to include ``subscribers.zcml``, while being
careful about how ``zope.intid`` is configured:

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

    <!-- Make sure the default IKeyReference adapters are in place -->
    <include package="zope.keyreference" />

    <include package="zc.intid" />

    <!--
    Make zc.intid utilities compatible with zope.intid utilities.
    -->
    <include package="zc.intid" file="zope-intid.zcml" />

    <!-- To hook them up to the Object events, we need to include the file -->
    <include package="zc.intid" file="subscribers.zcml" />



KeyReferences and zope.intid
============================

These subscribers do not register/unregister a :class:`~zope.keyreference.IKeyReference`
with the intid utilities. Instead, it registers the actual object, and the
events that are broadcast are broadcast holding the actual object.

``IKeyReferenceces``, especially
:class:`~zope.keyreference.persistent.KeyReferenceToPersistent`, are
used for a few reasons. First, they provide a stable,
object-identity-based pointer to objects. To be identity based, this
pointer is independent of the equality and hashing algorithms of the
underlying object. Identity-based comparisons are necessary for the
classic :mod:`zope.intid` utility implementation which uses a second
``OIBTree`` to maintain the backreferece from object to assigned intid
(clearly you don't want two non-identical objects which happen to
compare equally *now* to get the same intid as that condition may
change). Likewise, these references are all defined to be mutually
comparable, no matter how they are implemented, a condition necessary
for them to all work together in a ``OIBTree``. Lastly, these
references are meant to be comparable during ZODB conflict resolution
(the original persistent objects probably won't be), which, again, is
a condition of the implementation using a ``OIBTree.``

A consequence of avoiding these references is that generally
persistent objects that are expected to have intids assigned *should
not* be used as keys in an ``OxBTree`` or stored in an ``OOSet.``
Instead, all such data structures *should* use the integer
variations (e.g., ``IISet``), with the intid as the key.

Subscriber Functions
====================

.. autofunction:: zc.intid.subscribers.addIntIdSubscriber
.. autofunction:: zc.intid.subscribers.removeIntIdSubscriber
.. autofunction:: zc.intid.subscribers.intIdEventNotify
