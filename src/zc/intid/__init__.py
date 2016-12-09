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
Conflict-reducing unique integer ID utility.

See :mod:`zc.intid.interfaces`.
"""
# BWC imports/re-exports
from zc.intid.interfaces import IIntIdsQuery
from zc.intid.interfaces import IIntIdsSet
from zc.intid.interfaces import IIntIdsManage
from zc.intid.interfaces import IIntIds

from zc.intid.interfaces import IIntIdsSubclass

from zc.intid.interfaces import IIdEvent
from zc.intid.interfaces import IIdRemovedEvent
from zc.intid.interfaces import IIdAddedEvent
