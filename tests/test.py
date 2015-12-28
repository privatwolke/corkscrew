# coding: utf-8

import unittest
import warnings

from webtest import TestApp
from peewee import SqliteDatabase

from corkscrew import CorkscrewApplication, Link
from corkscrew.jsonapi import JsonAPIValidator
from corkscrew.handlers import PeeweeHandlerFactory as PHF
from corkscrew.fixtures import insertFixtures, database
from corkscrew.fixtures import Comment, Person, Photo, Article, Tag, PhotoTag
from corkscrew.fixtures import Revision
from corkscrew.fixtures import ARTICLE_TITLES, COMMENT_BODIES, TAG_NAMES


class TestCorkscrew(unittest.TestCase):

    def setUp(self):
        database.initialize(SqliteDatabase(":memory:"))
        insertFixtures()

        app = CorkscrewApplication(PHF)
        app.register(Comment, endpoint="/comments")

        app.register(
            Person,
            related={"articles": Article},
            endpoint="/people"
        )

        app.register(
            Photo,
            related={"tags": Link(Tag, via=PhotoTag)},
            endpoint="/photos"
        )

        app.register(
            Article,
            related={
                "comments": Comment,
                "revisions": Link(Revision, on="parent")
            },
            endpoint="/articles"
        )

        self.app = TestApp(app)

    def tearDown(self):
        database.close()

    def testList(self):
        result = self.app.get("/articles")
        self.assertEqual(result.status, "200 OK")

        JsonAPIValidator.validate_content_type(result.content_type)
        self.assertIsNotNone(result.json)

        JsonAPIValidator.validate_jsonapi(result.json)

        self.assertIn("data", result.json)
        self.assertIs(len(result.json["data"]), len(ARTICLE_TITLES))
        for row in result.json["data"]:
            self.assertEqual(row["type"], "article")
            self.assertIn("attributes", row)

            # expected attributes: title, created
            self.assertIs(len(row["attributes"]), 2)
            self.assertIn("title", row["attributes"])
            self.assertIn("created", row["attributes"])
            self.assertNotIn("author", row["attributes"])
            self.assertIn(row["attributes"]["title"], ARTICLE_TITLES)
            self.assertIn("relationships", row)

            for key, relationship in row["relationships"].iteritems():
                self.assertIn(
                    key,
                    ["comments", "cover", "author", "revisions"]
                )
                self.assertIn("links", relationship)
                self.assertIn("related", relationship["links"])
                self.assertIn("self", relationship["links"])

    def testGet(self):
        result = self.app.get("/articles/1")
        self.assertEqual(result.status, "200 OK")
        self.assertIsNotNone(result.json)

        JsonAPIValidator.validate_jsonapi(result.json)

        self.assertIn("data", result.json)

        # we want a single result
        self.assertEqual(type(result.json["data"]), type({}))
        self.assertIn("attributes", result.json["data"])

        attributes = result.json["data"]["attributes"]
        self.assertEqual(attributes["title"], ARTICLE_TITLES[0])

        self.assertIn("relationships", result.json["data"])

        for key, rel in result.json["data"]["relationships"].iteritems():
            self.assertIn(key, ["comments", "cover", "author", "revisions"])
            self.assertIn("links", rel)
            self.assertIn("related", rel["links"])
            self.assertIn("self", rel["links"])

        self.assertIsInstance(
            result.json["data"]["relationships"]["comments"]["data"],
            list
        )

    def testPost(self):
        request = {
            u"data": {
                u"type": u"article",
                u"attributes": {
                    u"title": u"Test entry"
                },
                u"relationships": {
                    u"author": {
                        u"data": {u"id": u"1", u"type": u"person"}
                    }
                }
            }
        }

        JsonAPIValidator.validate_jsonapi(request, True)

        result = self.app.post_json("/articles", params=request)
        self.assertEqual(result.status, "200 OK")
        JsonAPIValidator.validate_content_type(result.content_type)

        self.assertIsNotNone(result.json)
        JsonAPIValidator.validate_jsonapi(result.json)

        self.assertIn("relationships", result.json["data"])

        for key, rel in result.json["data"]["relationships"].iteritems():
            self.assertIn(key, ["comments", "cover", "author", "revisions"])
            self.assertIn("links", rel)
            self.assertIn("related", rel["links"])
            self.assertIn("self", rel["links"])

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

        JsonAPIValidator.validate_jsonapi(request)

        result = self.app.patch_json("/articles/1", params=request)
        self.assertIn(
            result.status,
            ["202 Accepted", "200 OK", "204 No Content"]
        )

        if result.status == "204 No Content":
            # nothing more to test
            return

        JsonAPIValidator.validate_content_type(result.content_type)

        self.assertIsNotNone(result.json)
        JsonAPIValidator.validate_jsonapi(result.json)

        self.assertEqual(
            result.json["data"]["attributes"]["title"],
            "Changed First Entry"
        )

    def testDelete(self):
        result = self.app.delete("/articles/1")
        self.assertIn(
            result.status,
            ["202 Accepted", "204 No Content", "200 OK"]
        )

    def testGetRelated(self):
        result = self.app.get("/articles/1")
        self.assertEqual(result.status, "200 OK")
        JsonAPIValidator.validate_content_type(result.content_type)

        self.assertIsNotNone(result.json)
        JsonAPIValidator.validate_jsonapi(result.json)

        result = self.app.get(
            result.json["data"]["relationships"]["author"]["links"]["related"]
        )

        self.assertEqual(result.status, "200 OK")
        JsonAPIValidator.validate_content_type(result.content_type)

        self.assertIsNotNone(result.json)
        JsonAPIValidator.validate_jsonapi(result.json)

        self.assertIn("data", result.json)
        self.assertEqual(type(result.json["data"]), type({}))
        self.assertEqual(result.json["data"]["type"], "person")
        self.assertEqual(result.json["data"]["id"], "1")

    def testGetRelationship(self):
        result = self.app.get("/articles/1")
        self.assertEqual(result.status, "200 OK")
        JsonAPIValidator.validate_content_type(result.content_type)

        self.assertIsNotNone(result.json)
        JsonAPIValidator.validate_jsonapi(result.json)

        result = self.app.get(
            result.json["data"]["relationships"]["author"]["links"]["self"]
        )

        self.assertEqual(result.status, "200 OK")
        JsonAPIValidator.validate_content_type(result.content_type)

        self.assertIsNotNone(result.json)
        JsonAPIValidator.validate_jsonapi(result.json)

        self.assertIn("data", result.json)
        self.assertIsInstance(result.json["data"], dict)
        self.assertEqual(result.json["data"]["type"], "person")
        self.assertEqual(result.json["data"]["id"], "1")

    def testPatchRelationship(self):
        result = self.app.get("/articles/1")
        self.assertEqual(result.status, "200 OK")
        JsonAPIValidator.validate_content_type(result.content_type)

        self.assertIsNotNone(result.json)
        JsonAPIValidator.validate_jsonapi(result.json)

        rel = result.json["data"]["relationships"]["author"]["links"]["self"]

        request = {
            u"data": {u"type": u"person", u"id": u"2"}
        }

        JsonAPIValidator.validate_jsonapi(request)

        result = self.app.patch_json(rel, params=request)
        self.assertIn(
            result.status,
            ["200 OK", "202 Accepted", "204 No Content"]
        )

        if result.status == "204 No Content":
            self.assertIs(len(result.body), 0)
        elif result.status == "200 OK":
            self.assertIsNotNone(result.json)
            JsonAPIValidator.validate_jsonapi(result.json)

    def testFetchingDataCollection(self):
        result = self.app.get("/articles")
        JsonAPIValidator.validate_content_type(result.content_type)

        self.assertEqual(result.status, "200 OK")
        JsonAPIValidator.validate_jsonapi(result.json)

        self.assertIs(len(result.json["data"]), 2)
        for entry in result.json["data"]:
            self.assertEqual(entry["type"], "article")
            self.assertIsInstance(entry["id"], unicode)
            self.assertIn(entry["attributes"]["title"], ARTICLE_TITLES)

        Article.delete().where(True).execute()
        result = self.app.get("/articles")
        JsonAPIValidator.validate_content_type(result.content_type)

        self.assertEqual(result.status, "200 OK")
        self.assertIsNotNone(result.json)
        JsonAPIValidator.validate_jsonapi(result.json)

        self.assertIs(len(result.json["data"]), 0)

    def testFetchingNullRelationship(self):
        result = self.app.get("/articles/1")
        rel = result.json["data"]["relationships"]["cover"]["links"]["related"]

        result = self.app.get(rel)
        JsonAPIValidator.validate_content_type(result.content_type)

        self.assertEqual(result.status, "200 OK")
        self.assertIsNotNone(result.json)
        JsonAPIValidator.validate_jsonapi(result.json)

        self.assertIsNone(result.json["data"])

    def testFetchingMissingSingleResource(self):
        result = self.app.get("/article/1337", status=404)
        self.assertIsNotNone(result.json)
        JsonAPIValidator.validate_jsonapi(result.json)

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
                        u"data": {u"type": u"people", u"id": u"2"}
                    }
                }
            }
        }

        JsonAPIValidator.validate_jsonapi(request, True)

        result = self.app.post_json("/photos", params=request)
        JsonAPIValidator.validate_content_type(result.content_type)
        JsonAPIValidator.validate_jsonapi(result.json)

        if not result.location:
            warnings.warn(
                "The response SHOULD include a Location header identifying the"
                "location of the newly created resource."
            )

        else:
            res = self.app.get(result.location)
            self.assertIsNotNone(res.json)
            JsonAPIValidator.validate_jsonapi(res.json)

    def testCreatingResourceWithMissingRequiredAttributeShouldFail(self):
        request = {
            u"data": {
                u"type": u"person",
                u"attributes": {
                    u"name": u"Eve Bobbington"
                    # attribute 'age' is missing
                }
            }
        }

        JsonAPIValidator.validate_jsonapi(request, True)

        result = self.app.post_json("/people", params=request, status=400)
        JsonAPIValidator.validate_content_type(result.content_type)
        JsonAPIValidator.validate_jsonapi(result.json)

    def testCreateResourceWithAlreadyExistingId(self):
        request = {
            u"data": {
                u"type": u"person",
                u"id": u"1",
                u"attributes": {
                    u"name": "Jimmy Cricket",
                    u"age": 12
                }
            }
        }

        JsonAPIValidator.validate_jsonapi(request)

        # expect this to fail
        result = self.app.post_json("/people", params=request, status=409)
        JsonAPIValidator.validate_jsonapi(result.json)

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

        JsonAPIValidator.validate_jsonapi(request)
        res = self.app.patch_json(update_uri, params=request)

        if "204" not in res.status:
            JsonAPIValidator.validate_content_type(res.content_type)

        res = self.app.get("/articles/1")
        self.assertEqual(res.json["data"]["attributes"]["title"], UPDATE_TITLE)

    def testUpdatingResourceRelationships(self):
        result = self.app.get("/articles/1")
        request = result.json

        # Person(1) is the current author
        self.assertEqual(
            result.json["data"]["relationships"]["author"]["data"]["id"],
            "1"
        )

        # don't update attributes, server must ignore missing attributes
        del request["data"]["attributes"]

        # do not update the 'comments' and 'cover' relationships
        del request["data"]["relationships"]["comments"]
        del request["data"]["relationships"]["cover"]
        del request["data"]["relationships"]["revisions"]

        ptype = request["data"]["relationships"]["author"]["data"]["type"]

        # change author to Person(2)
        request["data"]["relationships"]["author"] = {
            u"data": {
                u"id": u"2",
                u"type": ptype
            }
        }

        JsonAPIValidator.validate_jsonapi(request)

        result = self.app.patch_json("/articles/1", params=request)
        result = self.app.get("/articles/1")

        self.assertNotEqual(
            result.json["data"]["relationships"]["author"]["data"]["id"],
            "1"
        )

        self.assertEqual(
            result.json["data"]["relationships"]["author"]["data"]["id"],
            "2"
        )

        self.assertEqual(
            result.json["data"]["attributes"]["title"],
            ARTICLE_TITLES[0]
        )

    def testDeletingIndividualResource(self):
        result = self.app.get("/photos/1")
        JsonAPIValidator.validate_jsonapi(result.json)

        result = self.app.delete("/photos/1")

        if result.status_int not in [202, 204, 200]:
            warnings.warn("Delete: A server MAY respond with other HTTP status"
                          "codes. This code is unknown to the specification.")

        if result.status_int == 200:
            JsonAPIValidator.validate_jsonapi(result.json)

        # the resource should be gone now
        self.app.get("/photos/1", status=404)

    def testFetchingRelatedOneToNResource(self):
        result = self.app.get("/articles/1/comments")
        JsonAPIValidator.validate_jsonapi(result.json)

        for entry in result.json["data"]:
            self.assertIn(entry["attributes"]["body"], COMMENT_BODIES)
            self.assertEqual(
                entry["relationships"]["author"]["data"]["id"],
                "2"
            )
            self.assertEqual(
                entry["relationships"]["article"]["data"]["id"],
                "1"
            )

    def testListingRelatedOneToNResource(self):
        result = self.app.get("/articles/1/relationships/comments")
        JsonAPIValidator.validate_jsonapi(result.json)

        for entry in result.json["data"]:
            JsonAPIValidator.validate_resource_identifier(entry)

    def testPatchingRelatedOneToNResourceShouldFail(self):
        result = self.app.get("/people/1/articles")

        self.assertIs(len(result.json["data"]), 2)
        for entry in result.json["data"]:
            self.assertIn(entry["attributes"]["title"], ARTICLE_TITLES)

        # it is not allowed to orphan an article
        request = {
            u"data": {
                u"id": u"1",
                u"type": u"person",
                u"relationships": {
                    u"articles": {
                        u"data": []
                    }
                }
            }
        }

        JsonAPIValidator.validate_jsonapi(request)

        result = self.app.patch_json("/people/1", params=request, status=400)
        JsonAPIValidator.validate_jsonapi(result.json)
        self.assertIn("orphan", result.json["errors"][0]["title"])

    def testPatchingRelatedOneToNResourceShouldSucceed(self):
        result = self.app.get("/articles/2/cover")
        self.assertIsInstance(result.json["data"], dict)

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

        JsonAPIValidator.validate_jsonapi(request)

        result = self.app.patch_json("/articles/2", params=request)

        result = self.app.get("/articles/2/cover")
        self.assertIsNone(result.json["data"])

    def testPatchingRelatedOneToMResource(self):
        result = self.app.get("/articles/1/relationships/comments")
        self.assertIsInstance(result.json["data"], list)

        del result.json["data"][0]

        request = {
            u"data": result.json["data"]
        }

        JsonAPIValidator.validate(request)
        result = self.app.patch_json(
            "/articles/1/relationships/comments",
            params=request
        )

    def testPatchingRelatedNToMResource(self):
        result = self.app.get("/photos/1/relationships/tags")
        self.assertIsInstance(result.json["data"], list)
        self.assertIs(len(result.json["data"]), 2)

        request = {
            u"data": result.json["data"]
        }

        # remove one tag
        request["data"].pop()

        self.app.patch_json("/photos/1/relationships/tags", params=request)

        result = self.app.get("/photos/1/relationships/tags")
        self.assertIsInstance(result.json["data"], list)
        self.assertIs(len(result.json["data"]), 1)

    def testGetNToMRelationship(self):
        result = self.app.get("/photos/1/tags")
        JsonAPIValidator.validate(result.json)

        self.assertIs(len(result.json["data"]), 2)

        for tag in result.json["data"]:
            self.assertIn(tag["attributes"]["name"], TAG_NAMES)

    def testValidateForwardRelationship(self):
        result = self.app.get("/photos")
        # Photo has a forward relationship to Person (photographer)
        for entry in result.json["data"]:
            self.assertIn("relationships", entry)
            for name, relationship in entry["relationships"].iteritems():
                self.assertIn(name, ["photographer", "tags"])

            relationship = entry["relationships"]["photographer"]
            data = relationship["data"]

            # retrieve the /relationships link
            subresult = self.app.get(relationship["links"]["self"])
            self.assertEqual(subresult.json["data"], data)

            # retrieve the related object
            subresult = self.app.get(relationship["links"]["related"])

            # type and id must match
            self.assertEqual(subresult.json["data"]["id"], data["id"])
            self.assertEqual(subresult.json["data"]["type"], data["type"])

            # retrieve the related self link and test if it's the same object
            subsubresult = self.app.get(
                subresult.json["data"]["links"]["self"]
            )
            self.assertEqual(subresult.json["data"], subsubresult.json["data"])

    def testValidateReverseRelationships(self):
        result = self.app.get("/photos")
        # Photo has a reverse relationship to Tag (tags, via PhotoTag)
        for entry in result.json["data"]:
            self.assertIn("relationships", entry)
            for name, relationship in entry["relationships"].iteritems():
                self.assertIn(name, ["photographer", "tags"])

            relationship = entry["relationships"]["tags"]
            data = relationship["data"]

            # retrieve the /relationships link
            subresult = self.app.get(relationship["links"]["self"])
            self.assertEqual(subresult.json["data"], data)

            # retrieve the related objects
            subresult = self.app.get(relationship["links"]["related"])

            # type and id must match
            for subentry in subresult.json["data"]:
                self.assertIn(
                    {"id": subentry["id"], "type": subentry["type"]},
                    data
                )

                if "links" in subentry and "self" in subentry["links"]:
                    subsubresult = self.app.get(subentry["links"]["self"])
                    self.assertEqual(subentry, subsubresult.json["data"])

    def testIncludeParameterForwardRelationship(self):
        result = self.app.get("/articles/2?include=cover")
        JsonAPIValidator.validate(result.json)
        self.assertIn("included", result.json)

        # the server must not return any other fields than requested
        self.assertIs(len(result.json["included"]), 1)

        ref = result.json["data"]["relationships"]["cover"]["data"]
        inc = result.json["included"][0]

        self.assertEqual(inc["type"], ref["type"])
        self.assertEqual(inc["id"], ref["id"])

        # the self link must be valid and refer to the same object
        subresult = self.app.get(inc["links"]["self"])
        self.assertEqual(subresult.json["data"], inc)

    def testIncludeParameterReverseRelationship(self):
        result = self.app.get("/articles/1?include=comments")
        JsonAPIValidator.validate(result.json)
        self.assertIn("included", result.json)

        # the server must not return any other fields than requested
        self.assertIs(len(result.json["included"]), len(COMMENT_BODIES))

        refs = result.json["data"]["relationships"]["comments"]["data"]

        for inc in result.json["included"]:
            self.assertIn({"id": inc["id"], "type": inc["type"]}, refs)

            # the self link must be valid and refer to the same object
            subresult = self.app.get(inc["links"]["self"])
            self.assertEqual(subresult.json["data"], inc)
            self.assertEqual(
                subresult.json["links"]["self"],
                inc["links"]["self"]
            )

    def testIncludeParameterWithInvalidFields(self):
        self.app.get("/articles/1?include=invalid-field", status=400)
        self.app.get("/articles/1?include=author,invalid-field", status=400)

    def testIncludeParameterWithCircularRelationships(self):
        self.app.get("/articles/1?include=comments.articles", status=400)
        self.app.get(
            "/articles/1?include=comments.articles.comments",
            status=400
        )

    def testSparseFieldsets(self):
        result = self.app.get("/people/1?fields[person]=age")
        JsonAPIValidator.validate(result.json)

        self.assertNotIn("name", result.json["data"]["attributes"])
        self.assertIn("age", result.json["data"]["attributes"])

    def testSparseFieldsetsWithIncludedObjects(self):
        result = self.app.get("/articles/1?include=comments&fields[comment]=")
        JsonAPIValidator.validate(result.json)

        for inc in result.json["included"]:
            self.assertNotIn("attributes", inc)

        result = self.app.get(
            "/comments/1?include=article.author&fields[person]=age"
        )
        JsonAPIValidator.validate(result.json)

        is_included = False
        for inc in result.json["included"]:
            if inc["type"] == "person":
                is_included = True
                self.assertIn("age", inc["attributes"])
                self.assertNotIn("name", inc["attributes"])

        self.assertIsNotNone(is_included)

    def testLinkWithSpecifiedField(self):
        result = self.app.get("/articles/1/revisions")
        JsonAPIValidator.validate(result.json)

        print(result.json)
