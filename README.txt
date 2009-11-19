==============================================
zc.intid - Reduced-conflict integer id utility
==============================================

This package provides an API to create integer ids for any object.
Objects can later be looked up by their id as well.  This functionality
is commonly used in situations where dealing with objects is
undesirable, such as in search indices or any code that needs an easy
hash of an object.

This is similar to the ``zope.intid`` package, but has fewer
dependencies and induces fewer conflict errors, since object ids are not
used as part of the stored data.  The id for an object is stored in an
attribute of the object itself, with the attribute name being configured
by the construction of the id utility.


Changes
=======

1.0.0 (unreleased)
------------------

- Initial release.
