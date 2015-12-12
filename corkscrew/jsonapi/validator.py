import re, warnings
from urlparse import urlparse
from corkscrew.jsonapi import JsonAPIException

class JsonAPIValidator(object):

	@staticmethod
	def validate(doc, is_client_generated = False):
		try:
			JsonAPIValidator.validate_jsonapi(doc, is_client_generated)

		except AssertionError as e:
			raise JsonAPIException(str(e))


	@staticmethod
	def validate_create(doc, _type):
		JsonAPIValidator.validate(doc, is_client_generated = True)

		if not "data" in doc:
			raise JsonAPIException("The request MUST include a single resource object as primary data.")

		if not type(doc["data"]) is type({}):
			raise JsonAPIException("The request MUST include a single resource object as primary data.")

		if not "type" in doc["data"]:
			raise JsonAPIException("The resource object MUST contain at least a type member.")

		if not _type == doc["data"]["type"]:
			JsonAPIException("Cannot create resources of type '{}' here.".format(doc["data"]["type"]))

		if "relationships" in doc["data"]:
			for _, data in doc["data"]["relationships"].iteritems():
				if not "id" in data["data"]:
					raise JsonAPIException("If a relationship is provided in the relationships member of the resource object, its value MUST be a relationship object with a data member.")


	@staticmethod
	def validate_patch(doc, _id, _type):
		JsonAPIValidator.validate(doc)

		if not "data" in doc:
			raise JsonAPIException("The request MUST include a single resource object as primary data.")

		if not type(doc["data"]) is type({}):
			raise JsonAPIException("The request MUST include a single resource object as primary data.")

		if not "type" in doc["data"]:
			raise JsonAPIException("The resource object MUST contain type and id members.")

		if not "id" in doc["data"]:
			raise JsonAPIException("The resource object MUST contain type and id members.")

		if not _type == doc["data"]["type"]:
			JsonAPIException("Cannot patch resources of type '{}' here.".format(doc["data"]["type"]))

		if not doc["data"]["id"] == _id:
			JsonAPIException("The values for 'id' in the URI and the request document do not match.")


	@staticmethod
	def validate_content_type(content_type):
		assert content_type == "application/vnd.api+json", "Servers MUST send all JSON API data in response documents with the header Content-Type: application/vnd.api+json without any media type parameters."


	@staticmethod
	def validate_member_names(doc):
		for key, value in doc.iteritems():
			assert len(key) > 0, "Member names MUST contain at least one character."
			assert re.match(r"^[0-9A-Za-z]$", key[0]) or ord(unicode(key[0])) > 0x7F, "Member names MUST start with a 'globally allowed character'."

			if len(key) > 2:
				for character in key[1:-1]:
					assert re.match(r"^[0-9A-Za-z\-_ ]$", character) or ord(unicode(character)) > 0x7F, "Member names MUST contain only the allowed characters."

			assert re.match(r"^[0-9A-Za-z]$", key[-1:]) or ord(unicode(key[-1:])) > 0x7F, "Member names MUST end with a 'globally allowed character'"

			if isinstance(value, dict):
				JsonAPIValidator.validate_member_names(value)


	@staticmethod
	def validate_jsonapi(doc, is_client_generated = False):
		assert isinstance(doc, dict), "A JSON object MUST be at the root of every JSON API request and response containing data."
		JsonAPIValidator.validate_member_names(doc)

		assert "data" in doc or "errors" in doc or "meta" in doc, "A document MUST contain at least one of the following top-level members: data, errors, meta."
		assert not ("data" in doc and "errors" in doc), "The members data and errors MUST NOT coexist in the same document."

		for key in doc.keys():
			assert key in ["data", "errors", "meta"], "objects defined by this specification MUST NOT contain any additional members"

		if "data" in doc:
			assert doc["data"] is None or isinstance(doc["data"], dict) or isinstance(doc["data"], list), "Primary data MUST be either: null, dict or list."

			if isinstance(doc["data"], list):
				for res in doc["data"]:
					JsonAPIValidator.validate_resource(res, is_client_generated)

			elif isinstance(doc["data"], dict):
				JsonAPIValidator.validate_resource(doc["data"], is_client_generated)

		if "links" in doc:
			JsonAPIValidator.validate_links(doc["links"])

		if "included" in doc:
			assert isinstance(doc["included"], list), "included: an array of resource objects that are related to the primary data and/or each other ('included resources')."
			for resource in doc["included"]:
				JsonAPIValidator.validate_resource(resource)

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
				JsonAPIValidator.validate_error(error)


	@staticmethod
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


	@staticmethod
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
			JsonAPIValidator.validate_attributes(resource["attributes"])

		if "relationships" in resource:
			JsonAPIValidator.validate_relationships(resource["relationships"])

		if "links" in resource:
			JsonAPIValidator.validate_links(resource["links"])

		if "attributes" in resource and "relationships" in resource:
			JsonAPIValidator.validate_attributes_relationships(resource["attributes"], resource["relationships"])

		if "meta" in resource:
			assert isinstance(doc["meta"], dict), "The value of each meta member MUST be an object (a 'meta object')."


	@staticmethod
	def validate_attributes_relationships(attributes, relationships):
		for key in attributes.keys():
			assert not key in relationships, "Fields for a resource object MUST share a common namespace with each other."


	@staticmethod
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


	@staticmethod
	def validate_relationships(relationships):
		assert isinstance(relationships, dict), "The value of the relationships key MUST be an object (a 'relationships object')."

		for key, relationship in relationships.iteritems():
			assert isinstance(relationship, dict), "A relationship object must be a dict."
			assert "links" in relationship or "data" in relationship or "meta" in relationship, "A 'relationship object' MUST contain at least one of the following: links, data, meta."

			for key in relationship.keys():
				assert key in ["links", "data", "meta"], "objects defined by this specification MUST NOT contain any additional member"

			if "links" in relationship:
				assert "self" in relationship["links"] or "related" in relationship["links"], "A 'links object' in this context contains at least one of: self, related."
				JsonAPIValidator.validate_links(relationship["links"])

			if "data" in relationship:
				assert relationship["data"] is None or isinstance(relationship["data"], list) or isinstance(relationship["data"], dict), "Resource linkage MUST be represented as one of the following: null, list, dict."
				if isinstance(relationship["data"], list):
					for res in relationship["data"]:
						JsonAPIValidator.validate_resource_identifier(res)

				elif isinstance(relationship["data"], dict):
					JsonAPIValidator.validate_resource_identifier(relationship["data"])


	@staticmethod
	def validate_resource_identifier(identifier):
		assert isinstance(identifier, dict), "A 'resource identifier object' is an object that identifies an individual resource."
		assert "type" in identifier, "A 'resource identifier object' MUST contain type and id members."
		assert "id" in identifier, "A 'resource identifier object' MUST contain type and id members."

		for key in identifier.keys():
			assert key in ["type", "id"]


	@staticmethod
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
