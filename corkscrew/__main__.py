#!/usr/bin/env python
# coding: utf-8

from peewee import Model, PrimaryKeyField, CharField, ForeignKeyField, SqliteDatabase
from corkscrew import CorkscrewApplication, HandlerFactory
from corkscrew.fixtures import *


if __name__ == "__main__":
	database.initialize(SqliteDatabase(":memory:"))
	insertFixtures()

	app = CorkscrewApplication()
	app.register2(HandlerFactory(Tag), endpoint = "/tags")
	#app.register(Tag,     endpoint = "/tags")
	#app.register(Comment, endpoint = "/comments")
	app.register2(HandlerFactory(Comment), endpoint = "/comments")
	app.register2(HandlerFactory(Person),  endpoint = "/people")

	app.register2(
		HandlerFactory(Photo, related = {"tags": (Tag, PhotoTag)}),
		endpoint = "/photos"
	)
	app.register2(
		HandlerFactory(Article, related = {"comments": Comment}),
		endpoint = "/articles"
	)

	app.run()
