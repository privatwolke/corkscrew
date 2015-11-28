# coding: utf-8

import json
from common import *
from jsonapi import *
from bottle import response


def fn_get(model):
	id_field = model._meta.primary_key.name
	endpoint = model_to_endpoint(model)

	def jsonp_get(_id):
		response.content_type = CONTENT_TYPE
		doc = JsonAPIResponse()
		try:
			entry = model.select().where(model._meta.primary_key == _id).get()
			doc.data = entry_to_resource(entry)
		except Exception as e:
			if e.__class__.__name__.endswith("DoesNotExist"):
				abort(404, "The requested {} resource with id {} does not exist.".format(endpoint, _id))

			abort(500, e.message)

		return json.dumps(dict(doc))
	return jsonp_get
