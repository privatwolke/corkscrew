# coding: utf-8

import unittest, warnings
from pprint import pprint
from webtest import TestApp
from peewee import SqliteDatabase
from corkscrew import CorkscrewApplication
from corkscrew.fixtures import *

from validator import *


class TestCorkscrew(unittest.TestSuite):

	def setUp(self):
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

		self.app = TestApp(app)


	def tearDown(self):
		database.close()


	def testList(self):
		result = self.app.get("/articles")
		assert result.status == "200 OK"

		validate_content_type(result.content_type)
		assert result.json

		validate_jsonapi(result.json)

		assert "data" in result.json
		assert len(result.json["data"]) is len(ARTICLE_TITLES)
		for row in result.json["data"]:
			assert row["type"] == "article"
			assert "attributes" in row
			assert len(row["attributes"]) is 1
			assert "title" in row["attributes"]
			assert not "author" in row["attributes"]
			assert row["attributes"]["title"] in ARTICLE_TITLES
			assert "relationships" in row

			for key, relationship in row["relationships"].iteritems():
				assert key in ["comments", "cover", "author"]
				assert "links" in relationship
				assert "related" in relationship["links"]
				assert "self" in relationship["links"]


	def testGet(self):
		result = self.app.get("/articles/1")
		assert result.status == "200 OK"
		assert result.json

		validate_jsonapi(result.json)

		assert "data" in result.json

		# we want a single result
		assert type(result.json["data"]) == type({})
		assert "attributes" in result.json["data"]

		attributes = result.json["data"]["attributes"]
		assert attributes["title"] == ARTICLE_TITLES[0]

		assert "relationships" in result.json["data"]

		for key, relationship in result.json["data"]["relationships"].iteritems():
			assert key in ["comments", "cover", "author"]
			assert "links" in relationship
			assert "related" in relationship["links"]
			assert "self" in relationship["links"]

		assert isinstance(result.json["data"]["relationships"]["comments"]["data"], list)


	def testPost(self):
		request = {
			u"data": {
				u"type": u"article",
				u"attributes": {
					u"title": u"Test entry"
				},
				u"relationships": {
					u"author": {
						u"data": { u"id": u"1", u"type": u"person" }
					}
				}
			}
		}

		validate_jsonapi(request, True)

		result = self.app.post_json("/articles", params = request)
		assert result.status == "200 OK"
		validate_content_type(result.content_type)

		assert result.json
		validate_jsonapi(result.json)

		assert "relationships" in result.json["data"]

		for key, relationship in result.json["data"]["relationships"].iteritems():
			assert key in ["comments", "cover", "author"]
			assert "links" in relationship
			assert "related" in relationship["links"]
			assert "self" in relationship["links"]


	def testPatch(self):
		request = {
			u"data": {
				u"type": u"article",
				u"id": u"1",
				u"attributes": {
					u"title": u"Changed First Entry"
				}
			}
		}

		validate_jsonapi(request)

		result = self.app.patch_json("/articles/1", params = request)
		assert result.status == "202 Accepted" or result.status == "200 OK" or result.status == "204 No Content"

		if result.status == "204 No Content":
			# nothing more to test
			return

		validate_content_type(result.content_type)

		assert result.json
		validate_jsonapi(result.json)

		assert result.json["data"]["attributes"]["title"] == "Changed First Entry"


	def testDelete(self):
		result = self.app.delete("/articles/1")
		assert result.status in ["202 Accepted", "204 No Content", "200 OK"]


	def testGetRelated(self):
		result = self.app.get("/articles/1")
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
		result = self.app.get("/articles/1")
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
		assert isinstance(result.json["data"], dict)
		assert result.json["data"]["type"] == "person"
		assert result.json["data"]["id"] == "1"


	def testPatchRelationship(self):
		result = self.app.get("/articles/1")
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
		validate_jsonapi(result.json)

		assert len(result.json["data"]) is 2
		for entry in result.json["data"]:
			assert entry["type"] == "article"
			assert isinstance(entry["id"], unicode)
			assert entry["attributes"]["title"] in ARTICLE_TITLES

		Article.delete().where(True).execute()
		result = self.app.get("/articles")
		validate_content_type(result.content_type)

		assert result.status == "200 OK"
		assert result.json
		validate_jsonapi(result.json)

		assert len(result.json["data"]) is 0


	def testFetchingNullRelationship(self):
		result = self.app.get("/articles/1")
		rel = result.json["data"]["relationships"]["cover"]["links"]["related"]

		result = self.app.get(rel)
		validate_content_type(result.content_type)

		assert result.status == "200 OK"
		assert result.json
		validate_jsonapi(result.json)

		assert result.json["data"] is None


	def testFetchingMissingSingleResource(self):
		result = self.app.get("/article/1337", status = 404)
		assert result.json
		validate_jsonapi(result.json)


	def testCreatingResourceWithReferences(self):
		request = {
			u"data": {
				u"type": u"photo",
				u"attributes": {
					u"title": u"Ember Hamster",
					u"src": u"http://example.com/images/productivity.png"
				},
				u"relationships": {
					u"photographer": {
						u"data": { u"type": u"people", u"id": u"2" }
					}
				}
			}
		}

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
		request = {
			u"data": {
				u"type": u"person",
				u"id": u"1",
				u"attributes": {
					u"name": "Jimmy Cricket"
				}
			}
		}

		validate_jsonapi(request)

		# expect this to fail
		result = self.app.post_json("/people", params = request, status = 409)
		validate_jsonapi(result.json)


	def testUpdatingResourceViaSelfLink(self):
		UPDATE_TITLE = u"Five Ways You Have Never Tried To Access Your Data"

		result = self.app.get("/articles/1")
		update_uri = result.json["data"]["links"]["self"]

		request = {
			u"data": {
				u"type": u"article",
				u"id": u"1",
				u"attributes": {
					u"title": UPDATE_TITLE
				}
			}
		}

		validate_jsonapi(request)
		res = self.app.patch_json(update_uri, params = request)

		if not "204" in res.status:
			validate_content_type(res.content_type)

		res = self.app.get("/articles/1")
		assert res.json["data"]["attributes"]["title"] == UPDATE_TITLE


	def testUpdatingResourceRelationships(self):
		result = self.app.get("/articles/1")
		request = result.json

		# Person(1) is the current author
		assert result.json["data"]["relationships"]["author"]["data"]["id"] == "1"

		# do not update attributes, server must leave missing attributes unchanged
		del request["data"]["attributes"]

		# do not update the 'comments' and 'cover' relationships
		del request["data"]["relationships"]["comments"]
		del request["data"]["relationships"]["cover"]

		# change author to Person(2)
		request["data"]["relationships"]["author"] = {
			u"data": {
				u"id": u"2",
				u"type": request["data"]["relationships"]["author"]["data"]["type"]
			}
		}
		validate_jsonapi(request)

		result = self.app.patch_json("/articles/1", params = request)
		result = self.app.get("/articles/1")

		assert result.json["data"]["relationships"]["author"]["data"]["id"] != "1"
		assert result.json["data"]["relationships"]["author"]["data"]["id"] == "2"
		assert result.json["data"]["attributes"]["title"] == ARTICLE_TITLES[0]


	def testDeletingIndividualResource(self):
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
		result = self.app.get("/articles/1/comments")
		validate_jsonapi(result.json)

		for entry in result.json["data"]:
			assert entry["attributes"]["body"] in COMMENT_BODIES
			assert entry["relationships"]["author"]["data"]["id"] == "2"
			assert entry["relationships"]["article"]["data"]["id"] == "1"


	def testListingRelatedOneToNResource(self):
		result = self.app.get("/articles/1/relationships/comments")
		validate_jsonapi(result.json)

		for entry in result.json["data"]:
			validate_resource_identifier(entry)


	def testPatchingRelatedOneToNResourceShouldFail(self):
		result = self.app.get("/articles/1/comments")

		assert len(result.json["data"]) is 2
		for entry in result.json["data"]:
			assert entry["attributes"]["body"] in COMMENT_BODIES

		# it is not allowed to orphan a comment
		request = {
			u"data": {
				u"id": u"1",
				u"type": u"article",
				u"relationships": {
					u"comments": {
						u"data": [
							{u"id": u"1", u"type": "comment"}
						]
					}
				}
			}
		}

		validate_jsonapi(request)

		result = self.app.patch_json("/articles/1", params = request, status = 400)
		validate_jsonapi(result.json)
		assert "cannot be null" in result.json["errors"][0]["title"]


	def testPatchingRelatedOneToNResourceShouldSucceed(self):
		result = self.app.get("/articles/2/cover")
		assert isinstance(result.json["data"], dict)

		request = {
			u"data": {
				u"id": u"2",
				u"type": u"article",
				u"relationships": {
					u"cover": {
						u"data": None
					}
				}
			}
		}

		validate_jsonapi(request)

		result = self.app.patch_json("/articles/2", params = request)

		result = self.app.get("/articles/2/cover")
		assert result.json["data"] is None
