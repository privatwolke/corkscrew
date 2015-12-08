# coding: utf-8

import re
import unittest, warnings
from pprint import pprint
from urlparse import urlparse
from webtest import TestApp
from peewee import SqliteDatabase
from corkscrew import BottleApplication
from corkscrew.fixtures import database, Person, Test, Tag, TestTag, Article, People, Photos, Comment


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

	for key in doc.keys():
		assert key in ["data", "errors", "meta"], "objects defined by this specification MUST NOT contain any additional members"

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
		for key in doc["jsonapi"].keys():
			assert key in ["version", "meta"]

		if "meta" in doc["jsonapi"]:
			assert isinstance(doc["jsonapi"]["meta"], dict), "This object MAY also contain a meta member, whose value is a meta object that contains non-standard meta-information."

		if "version" in doc["jsonapi"]:
			assert isinstance(doc["jsonapi"]["version"], unicode), "The jsonapi object MAY contain a version member whose value is a string indicating the highest JSON API version supported."

	if "meta" in doc:
		assert isinstance(doc["meta"], dict), "The value of each meta member MUST be an object (a 'meta object')."

	if "errors" in doc:
		assert isinstance(doc["errors"], list), "errors: an array of error objects"
		for error in doc["errors"]:
			validate_error(error)


def validate_links(links):
	assert isinstance(links, dict), "The value of each links member MUST be an object (a 'links object')."
	for key, link in links.iteritems():
		assert isinstance(link, unicode) or isinstance(link, dict), "A link MUST be represented as either: unicode, dict."
		if isinstance(link, unicode):
			assert urlparse(link), "Invalid link member. Could not parse URL."
		else:
			for key in link.keys():
				assert key in ["href", "meta"], "objects defined by this specification MUST NOT contain any additional members"

			if "href" in link:
				assert urlparse(link["href"]), "Invalid link[href] member. Could not parse URL."


def validate_resource(resource, is_client_generated = False):
	assert isinstance(resource, dict), "A resource object must be of type dict."
	assert "type" in resource, "A resource object MUST contain at least the following top-level member: type."
	assert isinstance(resource["type"], unicode), "The value of the type member MUST be a unicode."

	for key in resource.keys():
		assert key in ["id", "type", "attributes", "relationships", "links", "meta"], "objects defined by this specification MUST NOT contain any additional member"

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
		assert isinstance(relationship, dict), "A relationship object must be a dict."
		assert "links" in relationship or "data" in relationship or "meta" in relationship, "A 'relationship object' MUST contain at least one of the following: links, data, meta."

		for key in relationship.keys():
			assert key in ["links", "data", "meta"], "objects defined by this specification MUST NOT contain any additional member"

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

	for key in identifier.keys():
		assert key in ["type", "id"]


def validate_error(error):
	assert isinstance(error, dict), "An error must be an object."

	for key in error.keys():
		assert key in ["id", "links", "status", "code", "title", "detail", "source", "meta"], "objects defined by this specification MUST NOT contain any additional member"

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
		database.create_tables([Person, Test, Tag, TestTag, Article, People, Photos, Comment])
		p = Person.create(name = "John Doe")
		Person.create(name = "Jane Doe")
		Test.create(value = "First Entry", author = p)
		Test.create(value = "Second Entry", author = p)
		app = BottleApplication()
		app.register(Test)
		app.register(Article, endpoint = "/articles", related = {"comments": Comment})
		app.register(Photos)
		app.register(People)
		app.register(Comment)
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
		assert result.status == "202 Accepted" or result.status == "200 OK" or result.status == "204 No Content"

		if result.status == "204 No Content":
			# nothing more to test
			return

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


	def testFetchingDataCollection(self):
		result = self.app.get("/articles")
		validate_content_type(result.content_type)

		assert result.status == "200 OK"
		assert result.json
		validate_jsonapi(result.json)

		assert len(result.json["data"]) is 0

		Article.create(title = "JSON API paints my bikeshed!")
		Article.create(title = "Rails is Omakase")

		result = self.app.get("/articles")
		validate_content_type(result.content_type)

		assert result.status == "200 OK"
		assert result.json
		validate_jsonapi(result.json)

		assert len(result.json["data"]) is 2
		for entry in result.json["data"]:
			assert entry["type"] == "article"
			assert "id" in entry
			assert isinstance(entry["id"], unicode)
			assert "attributes" in entry
			assert "title" in entry["attributes"]


	def testFetchingIndividualArticle(self):
		Article.create(title = "JSON API paints my bikeshed!")

		result = self.app.get("/articles/1")
		validate_content_type(result.content_type)

		assert result.status == "200 OK"
		assert result.json
		validate_jsonapi(result.json)

		assert isinstance(result.json["data"], dict)
		assert result.json["data"]["id"] == "1"
		assert result.json["data"]["attributes"]["title"] == "JSON API paints my bikeshed!"
		assert "relationships" in result.json["data"]
		assert "author" in result.json["data"]["relationships"]
		assert result.json["data"]["relationships"]["author"]["links"]["related"]


	def testFetchingMissingAuthor(self):
		Article.create(title = "JSON API paints my bikeshed!")
		result = self.app.get("/articles/1")
		rel = result.json["data"]["relationships"]["author"]["links"]["related"]

		result = self.app.get(rel)
		validate_content_type(result.content_type)

		assert result.status == "200 OK"
		assert result.json
		validate_jsonapi(result.json)

		assert result.json["data"] is None


	def testFetchingMissingSingleResource(self):
		result = self.app.get("/article/1", status = 404)
		assert result.json
		validate_jsonapi(result.json)


	def testCreatingResourceWithReferences(self):
		People.create(id = 9)

		request = {u"data": {
			u"type": u"photos",
			u"attributes": {
				u"title": u"Ember Hamster",
				u"src": u"http://example.com/images/productivity.png"
			},
			u"relationships": {
				u"photographer": {
					u"data": { u"type": u"people", u"id": u"9" }
				}
			}
		}}

		validate_jsonapi(request, True)

		result = self.app.post_json("/photos", params = request)
		validate_content_type(result.content_type)
		validate_jsonapi(result.json)

		if not result.location:
			warnings.warn("The response SHOULD include a Location header identifying the location of the newly created resource.")

		else:
			res = self.app.get(result.location)
			assert res.json
			validate_jsonapi(res.json)


	def testCreateResourceWithAlreadyExistingId(self):
		People.create(id = 1)

		request = {
			u"data": {
				u"type": u"people",
				u"id": u"1"
			}
		}

		validate_jsonapi(request)

		# expect this to fail
		result = self.app.post_json("/people", params = request, status = 409)
		validate_jsonapi(result.json)


	def testUpdatingResource(self):
		Article.create(id = 1, title = "Five Ways You Have Never Tried To Access Your Data")
		result = self.app.get("/articles/1")
		update_uri = result.json["data"]["links"]["self"]

		request = {
			u"data": {
				u"type": u"article",
				u"id": u"1",
				u"attributes": {
					u"title": u"To TDD or Not"
				}
			}
		}

		validate_jsonapi(request)
		res = self.app.patch_json(update_uri, params = request)
		if not "204" in res.status:
			validate_content_type(res.content_type)

		res = self.app.get("/articles/1")
		assert res.json["data"]["attributes"]["title"] == "To TDD or Not"


	def testUpdatingResourceRelationships(self):
		a = Person.create(name = "John Doe")
		b = Person.create(name = "Jane Doe")
		Article.create(id = 1, title = "Seven Things That Will Make You Go WTF?!", author = a)

		result = self.app.get("/articles/1")
		request = result.json

		# John Doe is the current author
		assert result.json["data"]["relationships"]["author"]["data"]["id"] == a.id

		# do not update attributes, server must leave missing attributes unchanged
		del request["data"]["attributes"]

		# do not update the 'comments' relationship
		del request["data"]["relationships"]["comments"]

		# change author to Jane Doe
		request["data"]["relationships"]["author"] = {
			u"data": {
				u"id": unicode(b.id),
				u"type": request["data"]["relationships"]["author"]["data"]["type"]
			}
		}
		validate_jsonapi(request)

		result = self.app.patch_json("/articles/1", params = request)
		result = self.app.get("/articles/1")

		assert result.json["data"]["relationships"]["author"]["data"]["id"] != a.id
		assert result.json["data"]["relationships"]["author"]["data"]["id"] == b.id
		assert result.json["data"]["attributes"]["title"] == "Seven Things That Will Make You Go WTF?!"


	def testDeletingIndividualResource(self):
		Photos.create(id = 1, title = "Test photo", src = "http://example.com/test.png", photographer = People.create())

		result = self.app.get("/photos/1")
		validate_jsonapi(result.json)

		result = self.app.delete("/photos/1")

		if not result.status_int in [202, 204, 200]:
			warnings.warn("Delete: A server MAY respond with other HTTP status codes. This code is unknown to the specification.")

		if result.status_int == 200:
			validate_jsonapi(result.json)

		# the resource should be gone now
		self.app.get("/photos/1", status = 404)


	def testFetchingRelatedOneToNResource(self):
		a = Article.create(id = 1, title = "Inclusion: The Way Forward?")
		p = People.create()
		Comment.create(article = a, body = "Good Stuff!", author = p)
		Comment.create(article = a, body = "First!", author = p)

		result = self.app.get("/articles/1/comments")
		validate_jsonapi(result.json)

		for entry in result.json["data"]:
			assert entry["attributes"]["body"] in ["Good Stuff!", "First!"]
			assert entry["relationships"]["author"]["data"]["id"] == p.id
			assert entry["relationships"]["article"]["data"]["id"] == a.id


	def testListingRelatedOneToNResource(self):
		a = Article.create(id = 1, title = "Inclusion: The Way Forward?")
		p = People.create()
		Comment.create(article = a, body = "Good Stuff!", author = p)
		Comment.create(article = a, body = "First!", author = p)

		result = self.app.get("/articles/1/relationships/comments")
		validate_jsonapi(result.json)

		for entry in result.json["data"]:
			validate_resource_identifier(entry)


	def testPatchingRelatedOneToNResource(self):
		a = Article.create(id = 1, title = "Inclusion: The Way Forward?")
		a2 = Article.create(title = "Exclusion: It's A New Thing!")
		p = People.create()
		c1 = Comment.create(article = a, body = "Good Stuff!", author = p)
		c2 = Comment.create(article = a2, body = "First!", author = p)

		result = self.app.get("/articles/1/comments")

		assert len(result.json["data"]) is 1
		assert result.json["data"][0]["attributes"]["body"] == "Good Stuff!"

		request = {
			u"data": {
				u"id": u"1",
				u"type": u"article",
				u"relationships": {
					u"comments": {
						u"data": [
							{u"id": unicode(c2.id), u"type": "comment"}
						]
					}
				}
			}
		}

		validate_jsonapi(request)

		self.app.patch_json("/articles/1", params = request)
		result = self.app.get("/articles/1/comments")

		assert len(result.json["data"]) is 1
		assert result.json["data"][0]["attributes"]["body"] == "First!"
