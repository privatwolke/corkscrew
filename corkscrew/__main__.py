#!/usr/bin/env python
# coding: utf-8

if __name__ == "__main__":

	database.create_tables([Person, Test])
	p = Person.create(name = "John Doe")
	p = Person.select().where(Person.name == "John Doe").get()
	Test.create(value = "First Entry", person = p)
	Test.create(value = "Second Entry", person = p)

	app = BottleApplication()
	app.register(Test)
	app.run()

# {"data":{"type":"test", "attributes": { "value": "Third Entry", "person": 1 } } }
