# coding: utf-8

import json
from common import *
from jsonapi import *
from bottle import response


def fn_list(model):
	id_field = model._meta.primary_key.name
	endpoint = model_to_endpoint(model)

	def jsonp_list():
		response.content_type = CONTENT_TYPE
		doc = JsonAPIResponse()

		try:
			for entry in model.select():
				doc.data.append(entry_to_resource(entry))

		except Exception as e:
			abort(500, e.message)

		return json.dumps(dict(doc))
	return jsonp_list
