#!/usr/bin/env python
# coding: utf-8

from peewee import Model, PrimaryKeyField, CharField, ForeignKeyField, SqliteDatabase
from corkscrew import BottleApplication
from corkscrew.fixtures import Test, Person, Tag, TestTag, database


if __name__ == "__main__":
	database.initialize(SqliteDatabase(":memory:"))
	database.create_tables([Test, Person, TestTag])
	p = Person.create(name = "John Doe")
	Test.create(value = "First Entry", author = p)
	Test.create(value = "Second Entry", author = p)

	app = BottleApplication(base_uri = "http://localhost:8080")
	app.register(Test, endpoint = "/tests", relationships = [("tags", TestTag)])
	app.register(Person, endpoint = "/people")
	app.register(Tag, endpoint = "/tags")
	app.run()

# {"data":{"type":"test", "attributes": { "value": "Third Entry", "person": 1 } } }
