#!/usr/bin/env python
# coding: utf-8

from peewee import Model, PrimaryKeyField, CharField, ForeignKeyField, SqliteDatabase
from corkscrew import BottleApplication
from corkscrew.fixtures import Test, Person, Tag, TestTag, Article, database


if __name__ == "__main__":
	database.initialize(SqliteDatabase(":memory:"))
	database.create_tables([Test, Person, TestTag, Article])
	p = Person.create(name = "John Doe")
	Test.create(value = "First Entry", author = p)
	Test.create(value = "Second Entry", author = p)
	Article.create(title = "JSON API paints my bikeshed!")
	Article.create(title = "Rails is Omakase")

	app = BottleApplication(base_uri = "http://localhost:8080")
	app.register(Test, endpoint = "/tests", relationships = [("tags", TestTag)])
	app.register(Person, endpoint = "/people")
	app.register(Tag, endpoint = "/tags")
	app.register(Article, endpoint = "/articles")
	app.run()

# {"data":{"type":"test", "attributes": { "value": "Third Entry", "person": 1 } } }
