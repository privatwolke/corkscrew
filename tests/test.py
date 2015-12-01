# coding: utf-8

import re
import unittest, warnings
from urlparse import urlparse
from webtest import TestApp
from peewee import SqliteDatabase
from corkscrew import BottleApplication
from corkscrew.fixtures import database, Person, Test


def validate_content_type(content_type):
	assert content_type == "application/vnd.api+json", "Servers MUST send all JSON API data in response documents with the header Content-Type: application/vnd.api+json without any media type parameters."


def validate_member_names(doc):
	for key, value in doc.iteritems():
		assert len(key) > 0, "Member names MUST contain at least one character."
		assert re.match(r"^[0-9A-Za-z]$", key[0]) or ord(unicode(key[0])) > 0x7F, "Member names MUST start with a 'globally allowed character'."

		if len(key) > 2:
			for character in key[1:-1]:
				assert re.match(r"^[0-9A-Za-z\-_ ]$", character) or ord(unicode(character)) > 0x7F, "Member names MUST contain only the allowed characters."

		assert re.match(r"^[0-9A-Za-z]$", key[-1:]) or ord(unicode(key[-1:])) > 0x7F, "Member names MUST end with a 'globally allowed character'"

		if isinstance(value, dict):
			validate_member_names(value)


def validate_jsonapi(doc, is_client_generated = False):
	assert isinstance(doc, dict), "A JSON object MUST be at the root of every JSON API request and response containing data."
	validate_member_names(doc)

	assert "data" in doc or "errors" in doc or "meta" in doc, "A document MUST contain at least one of the following top-level members: data, errors, meta."
	assert not ("data" in doc and "errors" in doc), "The members data and errors MUST NOT coexist in the same document."

	if "data" in doc:
		assert doc["data"] is None or isinstance(doc["data"], dict) or isinstance(doc["data"], list), "Primary data MUST be either: null, dict or list."

		if isinstance(doc["data"], list):
			for res in doc["data"]:
				validate_resource(res, is_client_generated)

		elif isinstance(doc["data"], dict):
			validate_resource(doc["data"], is_client_generated)

	if "links" in doc:
		validate_links(doc["links"])

	if "included" in doc:
		assert isinstance(doc["included"], list), "included: an array of resource objects that are related to the primary data and/or each other ('included resources')."
		for resource in doc["included"]:
			validate_resource(resource)

	if "included" in doc and not "data" in doc:
		assert False, "If a document does not contain a top-level data key, the included member MUST NOT be present either."

	if "jsonapi" in doc:
		assert isinstance(doc["jsonapi"], dict), "If present, the value of the jsonapi member MUST be an object (a 'jsonapi object')."
		if "meta" in doc["jsonapi"]:
			assert isinstance(doc["jsonapi"]["meta"], dict), "This object MAY also contain a meta member, whose value is a meta object that contains non-standard meta-information."

	if "meta" in doc:
		assert isinstance(doc["meta"], dict), "The value of each meta member MUST be an object (a 'meta object')."

	if "errors" in doc:
		assert isinstance(doc["errors"], list), "errors: an array of error objects"
		for errors in doc["errors"]:
			validate_error(error)


def validate_links(links):
	assert isinstance(links, dict), "The value of each links member MUST be an object (a 'links object')."
	for key, link in links.iteritems():
		assert isinstance(link, unicode) or isinstance(link, dict), "A link MUST be represented as either: unicode, dict."
		if isinstance(link, unicode):
			assert urlparse(link), "Invalid link member. Could not parse URL."
		else:
			if "href" in link:
				assert urlparse(link["href"]), "Invalid link[href] member. Could not parse URL."


def validate_resource(resource, is_client_generated = False):
	assert "type" in resource, "A resource object MUST contain at least the following top-level member: type."
	assert isinstance(resource["type"], unicode), "The value of the type member MUST be a unicode."

	if not is_client_generated:
		assert "id" in resource, "A resource object MUST contain at least the following top-level member: id."
		assert isinstance(resource["id"], unicode), "The value of the id member MUST be a unicode."

	if "attributes" in resource:
		validate_attributes(resource["attributes"])

	if "relationships" in resource:
		validate_relationships(resource["relationships"])

	if "links" in resource:
		validate_links(resource["links"])

	if "attributes" in resource and "relationships" in resource:
		validate_attributes_relationships(resource["attributes"], resource["relationships"])

	if "meta" in resource:
		assert isinstance(doc["meta"], dict), "The value of each meta member MUST be an object (a 'meta object')."


def validate_attributes_relationships(attributes, relationships):
	for key in attributes.keys():
		assert not key in relationships, "Fields for a resource object MUST share a common namespace with each other."


def validate_attributes(attributes):
	assert isinstance(attributes, dict), "The value of the attributes key MUST be an object (an 'attributes object')."

	for key, value in attributes.iteritems():
		assert key != "id", "A resource cannot have an attribute named 'id'."
		assert key != "type", "A resource cannot have an attribute named 'type'."

		if isinstance(value, dict):
			assert not "relationships" in value.keys(), "The name 'relationships' is reserved for future use."
			assert not "links" in value.keys(), "The name 'links' is reserved for future use."

		if key.endswith("_id"):
			warning.warn("bad-practice", "Foreign keys SHOULD NOT be represented as attributes.")


def validate_relationships(relationships):
	assert isinstance(relationships, dict), "The value of the relationships key MUST be an object (a 'relationships object')."

	for key, relationship in relationships.iteritems():
		assert "links" in relationship or "data" in relationship or "meta" in relationship, "A 'relationship object' MUST contain at least one of the following: links, data, meta."

		if "links" in relationship:
			assert "self" in relationship["links"] or "related" in relationship["links"], "A 'links object' in this context contains at least one of: self, related."
			validate_links(relationship["links"])

		if "data" in relationship:
			assert relationship["data"] is None or isinstance(relationship["data"], list) or isinstance(relationship["data"], dict), "Resource linkage MUST be represented as one of the following: null, list, dict."
			if isinstance(relationship["data"], list):
				for res in relationship["data"]:
					validate_resource_identifier(res)

			elif isinstance(relationship["data"], dict):
				validate_resource_identifier(relationship["data"])


def validate_resource_identifier(identifier):
	assert isinstance(identifier, dict), "A 'resource identifier object' is an object that identifies an individual resource."
	assert "type" in identifier, "A 'resource identifier object' MUST contain type and id members."
	assert "id" in identifier, "A 'resource identifier object' MUST contain type and id members."


def validate_error(error):
	assert isinstance(error, dict), "An error must be an object."
	if "links" in error:
		validate_links(error["links"], fields = ["about"])

	if "status" in error:
		assert isinstance(error["status"], unicode), "status: the HTTP status code applicable to this problem, expressed as a unicode value."

	if "code" in error:
		assert isinstance(error["code"], unicode), "code: an application-specific error code, expressed as a unicode value."

	if "source" in error:
		assert isinstance(error["source"], dict), "source: an object containing references to the source of the error"
		for key in error["source"].keys():
			assert key in ["pointer", "parameter"], "source: optionally including any of the following members: pointer, parameter"

	if "meta" in error:
		assert isinstance(error["meta"], dict), "The value of each meta member MUST be an object (a 'meta object')."


class TestCorkscrew(unittest.TestSuite):

	def setUp(self):
		database.initialize(SqliteDatabase(":memory:"))
		database.create_tables([Person, Test])
		p = Person.create(name = "John Doe")
		Person.create(name = "Jane Doe")
		Test.create(value = "First Entry", author = p)
		Test.create(value = "Second Entry", author = p)
		app = BottleApplication()
		app.register(Test)
		self.app = TestApp(app)


	def tearDown(self):
		database.close()


	def testList(self):
		result = self.app.get("/test")
		assert result.status == "200 OK"

		validate_content_type(result.content_type)
		assert result.json

		validate_jsonapi(result.json)

		assert "data" in result.json
		assert len(result.json["data"]) is 2
		for row in result.json["data"]:
			assert row["type"] == "test"
			assert "attributes" in row
			assert len(row["attributes"]) is 1
			assert "value" in row["attributes"]
			assert not "person" in row["attributes"]
			assert row["attributes"]["value"] in ["First Entry", "Second Entry"]
			assert "relationships" in row
			assert len(row["relationships"]) is 1
			assert "author" in row["relationships"]
			assert "links" in row["relationships"]["author"]
			assert "related" in row["relationships"]["author"]["links"]
			assert "self" in row["relationships"]["author"]["links"]


	def testGet(self):
		result = self.app.get("/test/1")
		assert result.status == "200 OK"
		assert result.json

		validate_jsonapi(result.json)

		assert "data" in result.json

		# we want a single result
		assert type(result.json["data"]) == type({})
		assert "attributes" in result.json["data"]

		attributes = result.json["data"]["attributes"]
		assert attributes["value"] == "First Entry"

		assert "relationships" in result.json["data"]
		relationships = result.json["data"]["relationships"]
		assert len(relationships) is 1
		assert "author" in relationships
		assert "links" in relationships["author"]
		assert "related" in relationships["author"]["links"]
		assert "self" in relationships["author"]["links"]


	def testPost(self):
		request = {
			u"data": {
				u"type": u"test",
				u"attributes": {
					u"value": u"Test entry"
				},
				u"relationships": {
					u"author": {
						u"data": { u"id": u"1", u"type": u"person" }
					}
				}
			}
		}

		validate_jsonapi(request, True)

		result = self.app.post_json("/test", params = request)
		assert result.status == "200 OK"
		validate_content_type(result.content_type)

		assert result.json
		validate_jsonapi(result.json)

		assert "relationships" in result.json["data"]
		relationships = result.json["data"]["relationships"]
		assert len(relationships) is 1
		assert "author" in relationships
		assert "links" in relationships["author"]
		assert "related" in relationships["author"]["links"]
		assert "self" in relationships["author"]["links"]


	def testPatch(self):
		request = {
			u"data": {
				u"type": u"test",
				u"id": u"1",
				u"attributes": {
					u"value": u"Changed First Entry"
				}
			}
		}

		validate_jsonapi(request)

		result = self.app.patch_json("/test/1", params = request)
		assert result.status == "202 Accepted" or result.status == "200 OK"
		validate_content_type(result.content_type)

		assert result.json
		validate_jsonapi(result.json)

		assert result.json["data"]["attributes"]["value"] == "Changed First Entry"

		assert "relationships" in result.json["data"]
		relationships = result.json["data"]["relationships"]
		assert len(relationships) is 1
		assert "author" in relationships
		assert "links" in relationships["author"]
		assert "related" in relationships["author"]["links"]
		assert "self" in relationships["author"]["links"]


	def testDelete(self):
		result = self.app.delete("/test/1")
		assert result.status in ["202 Accepted", "204 No Content", "200 OK"]


	def testGetRelated(self):
		result = self.app.get("/test/1")
		assert result.status == "200 OK"
		validate_content_type(result.content_type)

		assert result.json
		validate_jsonapi(result.json)

		result = self.app.get(result.json["data"]["relationships"]["author"]["links"]["related"])
		assert result.status == "200 OK"
		validate_content_type(result.content_type)

		assert result.json
		validate_jsonapi(result.json)

		assert "data" in result.json
		assert type(result.json["data"]) == type({})
		assert result.json["data"]["type"] == "person"
		assert result.json["data"]["id"] == "1"


	def testGetRelationship(self):
		result = self.app.get("/test/1")
		assert result.status == "200 OK"
		validate_content_type(result.content_type)

		assert result.json
		validate_jsonapi(result.json)

		result = self.app.get(result.json["data"]["relationships"]["author"]["links"]["self"])
		assert result.status == "200 OK"
		validate_content_type(result.content_type)

		assert result.json
		validate_jsonapi(result.json)

		assert "data" in result.json
		assert type(result.json["data"]) == type({})
		assert result.json["data"]["type"] == "person"
		assert result.json["data"]["id"] == "1"


	def testPatchRelationship(self):
		result = self.app.get("/test/1")
		assert result.status == "200 OK"
		validate_content_type(result.content_type)

		assert result.json
		validate_jsonapi(result.json)

		relation = result.json["data"]["relationships"]["author"]["links"]["self"]

		request = {
			u"data": { u"type": u"person", u"id": u"2" }
		}

		validate_jsonapi(request)

		result = self.app.patch_json(relation, params = request)
		assert result.status in ["200 OK", "202 Accepted", "204 No Content"]
		if result.status == "204 No Content":
			assert len(result.body) is 0
		elif result.status == "200 OK":
			assert result.json
			validate_jsonapi(result.json)
