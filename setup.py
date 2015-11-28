#!/usr/bin/env python
# coding: utf-8

from setuptools import setup
from io import open

version = '0.0.1'

setup(name = 'corkscrew',
	version = version,
	description = 'Integrates peewee and bottle to produce a JSON API compatible web service.',
	long_description = open('README.rst', 'r', encoding = 'utf-8').read(),
	author = 'Stephan Klein',
	url = 'https://github.com/privatwolke/corkscrew',
	license = 'MIT',
	packages = ['corkscrew', 'corkscrew.handlers'],
	install_requires = ['bottle', 'peewee'],
	extras_require = {
		"testing": ['webtest', 'nose']
	},
	zip_safe = True
)
