# coding: utf-8

import json
from common import *
from jsonapi import *
from bottle import response, abort


def fn_get(model, endpoint, relationship = None):
	foreign_keys = filter(lambda x: isinstance(x, ForeignKeyField), model._meta.get_fields())

	def jsonp_get(_id):
		response.content_type = CONTENT_TYPE
		doc = JsonAPIResponse()
		try:
			entry = model.select().where(model._meta.primary_key == _id).get()

			if relationship:
				doc.data = entry_to_resource(getattr(entry, relationship), endpoint)
			else:
				doc.data = entry_to_resource(entry, endpoint)

			return json.dumps(dict(doc))

		except Exception as e:
			if e.__class__.__name__.endswith("DoesNotExist"):
				if relationship:
					doc.data = None
					return json.dumps(dict(doc))
				
				abort(404, "The requested {} resource with id {} does not exist.".format(endpoint, _id))

			abort(500, e)

	return jsonp_get
