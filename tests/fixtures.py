# coding: utf-8

from peewee import *

database = Proxy()

class Person(Model):
	id = PrimaryKeyField()
	name = CharField()

	class Meta:
		database = database


class Test(Model):
	id = PrimaryKeyField()
	value = CharField(max_length = 64)
	person = ForeignKeyField(Person)

	class Meta:
		database = database
