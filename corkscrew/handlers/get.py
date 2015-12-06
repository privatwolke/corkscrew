# coding: utf-8

import json
from common import *
from jsonapi import *
from bottle import response, abort


def fn_get(model, endpoint, relationship = None):
	foreign_keys = filter(lambda x: isinstance(x, ForeignKeyField), model._meta.sorted_fields)

	def jsonp_get(_id):
		response.content_type = CONTENT_TYPE
		doc = JsonAPIResponse()
		try:
			entry = model.select().where(model._meta.primary_key == _id).get()

			if relationship:
				rel = getattr(entry, relationship)
				# non existant relationships must return successful with data: null
				doc.data = entry_to_resource(rel) if rel else None
			else:
				doc.data = entry_to_resource(entry)

			return json.dumps(dict(doc))

		except Exception as e:
			if e.__class__.__name__.endswith("DoesNotExist"):
				if relationship:
					doc.data = None
					return json.dumps(dict(doc))

				abort(404, "The requested {} resource with id {} does not exist.".format(endpoint, _id))

			abort(500, e)

	return jsonp_get
