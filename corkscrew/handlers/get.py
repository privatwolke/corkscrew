# coding: utf-8

import json
from common import *
from error import ErrorHandler
from jsonapi import *
from bottle import response


def fn_get(model, related, endpoints):
	foreign_keys = filter(lambda x: isinstance(x, ForeignKeyField), model._meta.sorted_fields)

	@ErrorHandler
	@ContentType
	def jsonp_get(_id):
		include = request.query.get("include")
		doc = JsonAPIResponse()

		entry = model.select().where(model._meta.primary_key == _id).get()

		if include:
			include = include.split(",")
			included = [
				entry_to_resource(getattr(entry, inc)) for inc in include
			]

			doc.included = included

		doc.data = entry_to_resource(entry, related, endpoints)
		return json.dumps(dict(doc))

	return jsonp_get
