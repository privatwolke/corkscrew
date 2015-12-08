# coding: utf-8

import json
from common import *
from error import ErrorHandler
from jsonapi import *
from bottle import response, abort


def fn_list(model, related = None):
	foreign_keys = filter(lambda x: isinstance(x, ForeignKeyField), model._meta.sorted_fields)

	@ErrorHandler
	@ContentType
	def jsonp_list():
		doc = JsonAPIResponse()

		for entry in model.select():
			doc.data.append(entry_to_resource(entry))

		return json.dumps(dict(doc), sort_keys = True)

	return jsonp_list
