# coding: utf-8

import json
from common import *
from error import ErrorHandler
from jsonapi import *
from bottle import request, response, abort
from peewee import IntegrityError


def fn_create(model, related, endpoints):

	@ErrorHandler
	@ContentType
	def jsonp_create():
		doc = JsonAPIResponse()

		request_doc = json.loads(request.body.getvalue())
		assert "data" in request_doc, JsonAPIException("The request MUST include a single resource object as primary data.")
		assert type(request_doc["data"]) is type({}), JsonAPIException("The request MUST include a single resource object as primary data.")
		assert "type" in request_doc["data"], JsonAPIException("The resource object MUST contain at least a type member.")

		if not model._meta.name == request_doc["data"]["type"]:
			abort(409, JsonAPIException("Cannot create resources of type '{}'.".format(request_doc["data"]["type"])))

		if "attributes" in request_doc["data"]:
			attributes = request_doc["data"]["attributes"]
		else:
			attributes = {}

		if "relationships" in request_doc["data"]:
			for key, data in request_doc["data"]["relationships"].iteritems():
				assert "id" in data["data"], JsonAPIException("If a relationship is provided in the relationships member of the resource object, its value MUST be a relationship object with a data member.")
				attributes[key] = data["data"]["id"]

		# accept client generated ids
		if "id" in request_doc["data"]:
			attributes["id"] = request_doc["data"]["id"]

		created = model.create(**attributes)
		doc.data = entry_to_resource(created, related, endpoints)

		response.set_header("Location", "{}/{}".format(request.url, get_primary_key(created)))
		return json.dumps(dict(doc))

	return jsonp_create
