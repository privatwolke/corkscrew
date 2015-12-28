# coding: utf-8

import re
import logging
from urlparse import urlparse

from corkscrew.jsonapi import JsonAPIException
from corkscrew.jsonapi.strings import M


class JsonAPIValidator(object):
    """A collection of functions that validates JsonAPI structures."""

    @staticmethod
    def validate(doc, is_client_generated=False):
        """The main entry point for validating complete and generic JSON API
        structures.
        """

        try:
            JsonAPIValidator.validate_jsonapi(doc, is_client_generated)

        except AssertionError as e:
            raise JsonAPIException(str(e))

    @staticmethod
    def validate_create(doc, _type):
        """Validates a JsonAPI structure that can be used for creating a new
        resource.
        """

        # first, let's make sure that the overall format is correct
        JsonAPIValidator.validate(doc, is_client_generated=True)

        # also, make sure that these stricter requirements are also met

        if "data" not in doc:
            raise JsonAPIException(M.PRIMARY_MUST_BE_OBJECT)

        if not isinstance(doc["data"], dict):
            raise JsonAPIException(M.REQ_MUST_BE_SINGLE_OBJECT)

        if "type" not in doc["data"]:
            raise JsonAPIException(M.MUST_CONTAIN_TYPE)

        if not _type == doc["data"]["type"]:
            JsonAPIException(M.ILLEGAL_TYPE.format(doc["data"]["type"]))

        if "relationships" in doc["data"]:
            for _, data in doc["data"]["relationships"].iteritems():
                if "id" not in data["data"]:
                    raise JsonAPIException(M.REL_WITH_NO_DATA_MEMBER)

    @staticmethod
    def validate_patch(doc, _id, _type):
        """Validates a JsonAPI structure that can be used for patching a
        resource.
        """

        # first, let's make sure that the overall format is correct
        JsonAPIValidator.validate(doc)

        # also, make sure that these stricter requirements are also met

        if "data" not in doc:
            raise JsonAPIException(M.PRIMARY_MUST_BE_OBJECT)

        if not isinstance(doc["data"], dict):
            raise JsonAPIException(M.PRIMARY_MUST_BE_OBJECT)

        if "type" not in doc["data"]:
            raise JsonAPIException(M.TYPE_AND_ID_REQUIRED)

        if "id" not in doc["data"]:
            raise JsonAPIException(M.TYPE_AND_ID_REQUIRED)

        if not _type == doc["data"]["type"]:
            JsonAPIException(M.ILLEGAL_TYPE_PATCH.format(doc["data"]["type"]))

        if not doc["data"]["id"] == _id:
            JsonAPIException(M.ID_REQUEST_URI_MISMATCH)

    @staticmethod
    def validate_content_type(content_type):
        """Validates the Content-Type of a response."""

        if not content_type == "application/vnd.api+json":
            JsonAPIException(M.ILLEGAL_CONTENT_TYPE)

    @staticmethod
    def validate_member_names(doc):
        """Validates the characters used in member names against the JSON API
        specification.
        """

        for key, value in doc.iteritems():
            assert len(key) > 0, M.AT_LEAST_ONE_CHAR

            is_allowed_char = re.match(r"^[0-9A-Za-z]$", key[0])
            is_other_char = ord(unicode(key[0])) > 0x7F

            assert is_allowed_char or is_other_char, M.ONLY_ALLOWED_CHARS

            if len(key) > 2:
                for character in key[1:-1]:
                    is_allowed_char = re.match(r"^[0-9A-Za-z\-_ ]$", character)
                    is_other_char = ord(unicode(character)) > 0x7F
                    assert (
                        is_allowed_char or is_other_char
                    ), M.NAMES_MUST_USE_ALLOWED_CHARS

            assert (
                re.match(r"^[0-9A-Za-z]$", key[-1:])
                or ord(unicode(key[-1:])) > 0x7F
            ), M.NAMES_MUST_END_WITH_ALLOWED

            if isinstance(value, dict):
                JsonAPIValidator.validate_member_names(value)

    @staticmethod
    def validate_jsonapi(doc, is_client_generated=False):
        """Validates the root level of a JsonAPI structure."""

        assert isinstance(doc, dict), M.MUST_BE_OBJECT
        JsonAPIValidator.validate_member_names(doc)

        assert (
            "data" in doc or "errors" in doc or "meta" in doc
        ), M.ILLEGAL_TOPLEVEL

        assert (
            not ("data" in doc and "errors" in doc)
        ), M.DATA_AND_ERROR_MUST_NOT_COEXIST

        for key in doc.keys():
            assert key in [
                "data",
                "errors",
                "meta",
                "links",
                "jsonapi",
                "included"
            ], M.NO_ADDITIONAL_MEMBERS

        if "data" in doc:
            assert (
                doc["data"] is None or isinstance(doc["data"], dict)
                or isinstance(doc["data"], list)
            ), M.ILLEGAL_DATA_VALUE

            if isinstance(doc["data"], list):
                for res in doc["data"]:
                    JsonAPIValidator.validate_resource(
                        res,
                        is_client_generated
                    )

            elif isinstance(doc["data"], dict):
                JsonAPIValidator.validate_resource(
                    doc["data"],
                    is_client_generated
                )

        if "links" in doc:
            JsonAPIValidator.validate_links(doc["links"])

        if "included" in doc:
            assert isinstance(doc["included"], list), M.ILLEGAL_INCLUDED
            for resource in doc["included"]:
                JsonAPIValidator.validate_resource(resource)

        if "included" in doc and "data" not in doc:
            assert False, M.IF_NO_DATA_NO_INCLUDED

        if "jsonapi" in doc:
            assert isinstance(doc["jsonapi"], dict), M.ILLEGAL_JSONAPI
            for key in doc["jsonapi"].keys():
                assert key in ["version", "meta"]

            if "meta" in doc["jsonapi"]:
                assert isinstance(doc["jsonapi"]["meta"], dict), M.ILLEGAL_META

            if "version" in doc["jsonapi"]:
                assert (
                    isinstance(doc["jsonapi"]["version"], unicode)
                ), M.ILLEGAL_VERSION

        if "meta" in doc:
            assert isinstance(doc["meta"], dict), M.ILLEGAL_META

        if "errors" in doc:
            assert isinstance(doc["errors"], list), M.ILLEGAL_ERROR
            for error in doc["errors"]:
                JsonAPIValidator.validate_error(error)

    @staticmethod
    def validate_links(links):
        """Validates a links object."""

        assert isinstance(links, dict), M.ILLEGAL_LINKS
        for key, link in links.iteritems():
            assert (
                isinstance(link, unicode) or isinstance(link, dict)
            ), M.ILLEGAL_LINK

            if isinstance(link, unicode):
                assert urlparse(link), M.INVALID_LINK
            else:
                for key in link.keys():
                    assert key in ["href", "meta"], M.NO_ADDITIONAL_MEMBERS

                if "href" in link:
                    assert urlparse(link["href"]), M.INVALID_LINK

    @staticmethod
    def validate_resource(resource, is_client_generated=False):
        """Validates a resource object."""

        assert isinstance(resource, dict), M.ILLEGAL_RESOURCE_OBJECT
        assert "type" in resource, M.TYPE_REQUIRED
        assert isinstance(resource["type"], unicode), M.ILLEGAL_TYPE_VALUE

        for key in resource.keys():
            assert key in [
                "id",
                "type",
                "attributes",
                "relationships",
                "links",
                "meta"
            ], M.NO_ADDITIONAL_MEMBERS

        if not is_client_generated:
            assert "id" in resource, M.ID_REQUIRED
            assert isinstance(resource["id"], unicode), M.ILLEGAL_ID_VALUE

        if "attributes" in resource:
            JsonAPIValidator.validate_attributes(resource["attributes"])

        if "relationships" in resource:
            JsonAPIValidator.validate_relationships(resource["relationships"])

        if "links" in resource:
            JsonAPIValidator.validate_links(resource["links"])

        if "attributes" in resource and "relationships" in resource:
            JsonAPIValidator.validate_attributes_relationships(
                resource["attributes"],
                resource["relationships"]
            )

        if "meta" in resource:
            assert isinstance(resource["meta"], dict), M.ILLEGAL_META

    @staticmethod
    def validate_attributes_relationships(attributes, relationships):
        """Validates that the attributes and relationships members don't use
        overlapping names."""

        for key in attributes.keys():
            assert key not in relationships, M.COMMON_NAMESPACE

    @staticmethod
    def validate_attributes(attributes):
        """Validates an attributes object."""

        assert isinstance(attributes, dict), M.ILLEGAL_ATTRIBUTES

        for key, value in attributes.iteritems():
            assert key != "id", M.ATTRIBUTE_ID_FORBIDDEN
            assert key != "type", M.ATTRIBUTE_TYPE_FORBIDDEN

            if isinstance(value, dict):
                assert "links" not in value.keys(), M.RESERVED_LINKS
                assert (
                    "relationships" not in value.keys()
                ), M.RESERVED_RELATIONSHIP

            if key.endswith("_id"):
                logging.warn(M.FOREIGN_KEYS_SHOULD_BE_ATTRIBUTES)

    @staticmethod
    def validate_relationships(relationships):
        """Validates a relationships object."""

        assert isinstance(relationships, dict), M.ILLEGAL_RELATIONSHIPS

        for key, relationship in relationships.iteritems():
            assert isinstance(relationship, dict), M.ILLEGAL_RELATIONSHIP_VALUE
            assert (
                "links" in relationship or "data" in relationship
                or "meta" in relationship
            ), M.INVALID_RELATIONSHIP_FIELDS

            for key in relationship.keys():
                assert key in [
                    "links",
                    "data",
                    "meta"
                ], M.NO_ADDITIONAL_MEMBERS

            if "links" in relationship:
                assert (
                    "self" in relationship["links"]
                    or "related" in relationship["links"]
                ), M.INVALID_LINK_ATTRIBUTES

                JsonAPIValidator.validate_links(relationship["links"])

            if "data" in relationship:
                assert (
                    relationship["data"] is None
                    or isinstance(relationship["data"], list)
                    or isinstance(relationship["data"], dict)
                ), M.INVALID_LINKAGE_ATTRIBUTES

                if isinstance(relationship["data"], list):
                    for res in relationship["data"]:
                        JsonAPIValidator.validate_resource_identifier(res)

                elif isinstance(relationship["data"], dict):
                    JsonAPIValidator.validate_resource_identifier(
                        relationship["data"]
                    )

    @staticmethod
    def validate_resource_identifier(identifier):
        """Validates a resource identifier object."""

        assert isinstance(identifier, dict), M.INVALID_LINKAGE
        assert "type" in identifier, M.LINKAGE_TYPE_ID_REQUIRED
        assert "id" in identifier, M.LINKAGE_TYPE_ID_REQUIRED

        for key in identifier.keys():
            assert key in ["type", "id"]

    @staticmethod
    def validate_error(error):
        """Validates an error object."""

        assert isinstance(error, dict), "An error must be an object."

        for key in error.keys():
            assert key in [
                "id",
                "links",
                "status",
                "code",
                "title",
                "detail",
                "source",
                "meta"
            ], M.NO_ADDITIONAL_MEMBERS

        if "links" in error:
            JsonAPIValidator.validate_links(error["links"], fields=["about"])

        if "status" in error:
            assert isinstance(error["status"], unicode), M.ILLEGAL_STATUS

        if "code" in error:
            assert isinstance(error["code"], unicode), M.ILLEGAL_CODE

        if "source" in error:
            assert isinstance(error["source"], dict), M.ILLEGAL_SOURCE
            for key in error["source"].keys():
                assert key in ["pointer", "parameter"], M.NO_ADDITIONAL_MEMBERS

        if "meta" in error:
            assert isinstance(error["meta"], dict), M.ILLEGAL_META
