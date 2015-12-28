#!/usr/bin/env python
# coding: utf-8

from setuptools import setup, find_packages
from io import open

d = 'Integrates peewee and bottle to produce JSON API compatible web services.'
version = '0.0.1'

setup(
    name='corkscrew',
    version=version,
    description=d,
    long_description=open('README.rst', 'r', encoding='utf-8').read(),
    author='Stephan Klein',
    url='https://github.com/privatwolke/corkscrew',
    license='MIT',
    packages=find_packages(),
    install_requires=['bottle', 'peewee'],
    extras_require={
        "testing": ['webtest', 'nose', 'nosetests-json-extended', 'coverage']
    },
    zip_safe=True
)
