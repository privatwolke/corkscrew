#!/usr/bin/env python
# coding: utf-8

from peewee import Model, PrimaryKeyField, CharField, ForeignKeyField, SqliteDatabase

from corkscrew import CorkscrewApplication
from corkscrew.handlers import PeeweeHandlerFactory as PHF
from corkscrew.fixtures import *


if __name__ == "__main__":
	database.initialize(SqliteDatabase(":memory:"))
	insertFixtures()

	app = CorkscrewApplication(PHF)
	app.register(Comment, endpoint = "/comments")
	app.register(Person,  endpoint = "/people")

	app.register(
		Photo,
		related = { "tags": (Tag, PhotoTag) },
		endpoint = "/photos"
	)
	app.register(
		Article,
		related = { "comments": Comment },
		endpoint = "/articles"
	)

	app.run()
