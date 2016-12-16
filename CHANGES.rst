=========
 Changes
=========

2.0.0 (2016-12-16)
==================

- Add zope.lifecycleevent subscribers. You must include ``subscribers.zcml``
  to use these and have :mod:`zope.intid` installed. See :issue:`5`.
- Documentation is now hosted at http://zcintid.readthedocs.io
- Add continuous integration testing for supported Python versions.
- Add PyPy support.
- Add Python 3 support.
- Drop support for Python less than 2.7.
- Remove ZODB3 dependency in favor of explicit dependencies on BTrees.
- The zope-intid.zcml file included in this package now works to make
  the IntId utility from this package implement the zope.intids
  interface, if that package is installed.
- Interfaces and event implementations have been refactored into the
  new module :mod:`zc.intid.interfaces`. Backwards compatibility
  aliases remain for the old names. See :issue:`9`.
- Raise more informative KeyError subclasses from the utility when intids
  or objects cannot be found. This distinguishes them from errors
  raised by normal dictionaries or BTrees, and is useful in unit
  testing or when persisting intids or sharing them among processes
  for later or concurrent use. See :issue:`8`
- Propagate ``POSKeyError`` from ``queryId`` instead of returning the
  default object. This exception indicates a corrupt database, not a
  missing object. The ``queryObject`` function already behaved this way.
- Attempting to ``register`` an object that cannot have the utility's
  attribute set on it (for example, it has restrictive ``__slots__``)
  no longer corrupts the utility's state.

1.0.1 (2011-06-27)
==================

- Make the behavior of the utility's `getId` method consistent with
  zope.intid in regard to its handling of proxied objects.

1.0.0 (2011-02-21)
==================

- Initial release.
