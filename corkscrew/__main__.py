#!/usr/bin/env python
# coding: utf-8

from peewee import Model, PrimaryKeyField, CharField, ForeignKeyField, SqliteDatabase
from corkscrew import CorkscrewApplication
from corkscrew.fixtures import *


if __name__ == "__main__":
	database.initialize(SqliteDatabase(":memory:"))
	insertFixtures()

	app = CorkscrewApplication()
	app.register(Tag,     endpoint = "/tags")
	app.register(Comment, endpoint = "/comments")
	app.register(Person,  endpoint = "/people")

	app.register(Photo,   endpoint = "/photos", related = {
		"tags": (Tag, PhotoTag)
	})
	app.register(Article, endpoint = "/articles", related = {
		"comments": Comment
	})

	app.run()
