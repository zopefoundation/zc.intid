##############################################################################
#
# Copyright (c) 2006, 2009 Zope Foundation and Contributors.
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

import os
import setuptools


def read(*rnames):
    with open(os.path.join(os.path.dirname(__file__), *rnames)) as f:
        return f.read()

version = read("version.txt").strip()

tests_require = [
    'zope.configuration',
    'zope.site',
]

setuptools.setup(
    name="zc.intid",
    version=version,
    author="Zope Corporation and Contributors",
    author_email="zope-dev@zope.org",
    description="Reduced-conflict Integer Id Utility",
    long_description=read("README.rst"),
    keywords="zope3 integer id utility",
    classifiers=[
        #"Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Zope Public License",
        "Programming Language :: Python",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Topic :: Internet :: WWW/HTTP",
        "Framework :: Zope3",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
    url="http://zcintid.readthedocs.io",
    license="ZPL 2.1",
    packages=setuptools.find_packages("src"),
    package_dir={"": "src"},
    namespace_packages=["zc"],
    install_requires=[
        "setuptools",
        "BTrees",
        "zope.component",
        "zope.event",
        "zope.interface",
        "zope.security",
        # Subscribers
        "zope.lifecycleevent",
        "zope.intid >= 4.2",
        "zope.keyreference",
    ],
    tests_require=tests_require,
    extras_require={
        'test': tests_require,
    },
    include_package_data=True,
    zip_safe=False,
    test_suite="zc.intid.tests",
)
