# coding: utf-8

from peewee import *

database = Proxy()

class BaseModel(Model):
	class Meta:
		database = database


class Person(BaseModel):
	id = PrimaryKeyField()
	name = CharField()


class Test(BaseModel):
	id = PrimaryKeyField()
	value = CharField(max_length = 64)
	author = ForeignKeyField(Person)


class Tag(BaseModel):
	id = PrimaryKeyField()
	name = CharField(unique = True)


class TestTag(BaseModel):
	test = ForeignKeyField(Test)
	tag = ForeignKeyField(Tag)
