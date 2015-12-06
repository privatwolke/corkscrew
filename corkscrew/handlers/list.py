# coding: utf-8

import json
from common import *
from jsonapi import *
from bottle import response, abort


def fn_list(model, endpoint):
	foreign_keys = filter(lambda x: isinstance(x, ForeignKeyField), model._meta.sorted_fields)

	def jsonp_list():
		response.content_type = CONTENT_TYPE
		doc = JsonAPIResponse()

		try:
			for entry in model.select():
				doc.data.append(entry_to_resource(entry))

			return json.dumps(dict(doc), sort_keys = True)

		except Exception as e:
			abort(500, e)

	return jsonp_list
