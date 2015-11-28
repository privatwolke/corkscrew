# coding: utf-8

import unittest
from webtest import TestApp
from peewee import SqliteDatabase
from corkscrew import BottleApplication
from fixtures import database, Person, Test


class TestCorkscrew(unittest.TestSuite):

	def setUp(self):
		database.initialize(SqliteDatabase(":memory:"))
		database.create_tables([Person, Test])
		p = Person.create(name = "John Doe")
		Test.create(value = "First Entry", person = p)
		Test.create(value = "Second Entry", person = p)
		app = BottleApplication()
		app.register(Test)
		self.app = TestApp(app)


	def tearDown(self):
		database.close()


	def testList(self):
		result = self.app.get("/test")
		assert result.status == "200 OK"
		assert result.content_type == "application/vnd.api+json"
		assert result.json

		assert "data" in result.json
		assert type(result.json["data"]) == type([])
		assert len(result.json["data"]) is 2
		for row in result.json["data"]:
			assert "id" in row
			assert "type" in row
			assert "attributes" in row
			assert row["type"] == "test"
			assert len(row["attributes"]) is 2
			assert "value" in row["attributes"]
			assert "person" in row["attributes"]
			assert row["attributes"]["value"] in ["First Entry", "Second Entry"]


	def testGet(self):
		result = self.app.get("/test/1")
		assert result.status == "200 OK"
