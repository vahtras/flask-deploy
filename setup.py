#!/usr/bin/env python

from setuptools import setup

setup(
    py_modules=['fabfile', 'fabinit', 'template', 'file_and_stream'],
    entry_points={
        'console_scripts': [
            'fabinit = fabinit:fabinit',
        ]
    },
)
