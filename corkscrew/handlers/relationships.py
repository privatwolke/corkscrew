# coding: utf-8

import json
from common import *
from error import ErrorHandler
from jsonapi import *
from bottle import request, response




def fn_get_relationship(model, relationship, linkage = False):

	@ErrorHandler
	@ContentType
	def jsonp_get_relationship(_id):
		doc = JsonAPIResponse()
		endpoint = get_endpoint()

		entry = model.select().where(model._meta.primary_key == _id).get()

		rel = getattr(entry, relationship)
		# non existant relationships must return successful with data: null
		doc.data = entry_to_resource(rel, linkage) if rel else None

		return json.dumps(dict(doc))

	return jsonp_get_relationship


def fn_get_reverse_relationship(child, parent, linkage = False):

	reverse_field = get_reverse_field(child, parent)

	@ErrorHandler
	@ContentType
	def jsonp_get_reverse_relationship(_id):
		doc = JsonAPIResponse()
		endpoint = get_endpoint()

		for entry in child.select().where(reverse_field == _id):
			doc.data.append(entry_to_resource(entry, linkage))

		return json.dumps(dict(doc))

	return jsonp_get_reverse_relationship


def fn_patch_relationship(model, relationship):

	@ErrorHandler
	@ContentType
	def jsonp_patch_relationship(_id):
		response.status = 204
		doc = JsonAPIResponse()
		endpoint = get_endpoint()

		request_doc = json.loads(request.body.getvalue())
		assert "data" in request_doc, JsonAPIException("The request MUST include a single resource object as primary data.")
		assert type(request_doc["data"]) is type({}), JsonAPIException("The request MUST include a single resource object as primary data.")
		assert "type" in request_doc["data"], JsonAPIException("The request MUST include a single resource object as primary data.")
		assert "id" in request_doc["data"], JsonAPIException("The request MUST include a single resource object as primary data.")

		entry = model.select().where(model._meta.primary_key == _id).get()
		setattr(entry, relationship, request_doc["data"]["id"])
		entry.save()

	return jsonp_patch_relationship
