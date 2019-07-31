#!/usr/bin/python3
# -*- coding: latin-1 -*-
"""
Sanic Plugins Framework
~~~~~~~~~~~~~~~~~~~~~~~
Doing all of the boilerplate to create a Sanic Plugin, so you don't have to.

:copyright: (c) 2017 by Ashley Sommer.
:license: MIT, see LICENSE for more details.
"""
import codecs
import os
import re
from setuptools import setup


def open_local(paths, mode='r', encoding='utf8'):
    path = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        *paths
    )

    return codecs.open(path, mode, encoding)


with open_local(['spf', '__init__.py'], encoding='latin1') as fp:
    try:
        version = re.findall(r"^__version__ = '([^']+)'\r?$",
                             fp.read(), re.M)[0]
    except IndexError:
        raise RuntimeError('Unable to determine version.')

with open_local(['README.rst']) as readme:
    long_description = readme.read()


with open_local(['requirements.txt']) as req:
    install_requires = req.read().split("\n")

setup(
    name='Sanic-Plugins-Framework',
    version=version,
    url='https://github.com/ashleysommer/sanicpluginsframework',
    license='MIT',
    author='Ashley Sommer',
    author_email='ashleysommer@gmail.com',
    description="Doing all of the boilerplate to create a Sanic Plugin, "
                "so you don't have to.",
    long_description=long_description,
    packages=['spf', 'spf.plugins'],
    entry_points={
        'sanic_plugins':
            ['Contextualize = spf.plugins.contextualize:instance']
    },
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    install_requires=install_requires,
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
