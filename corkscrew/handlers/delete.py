# coding: utf-8

import json
from common import *
from jsonapi import *
from bottle import response, abort


def fn_delete(model):
	endpoint = model_to_endpoint(model)

	def jsonp_delete(_id):
		response.content_type = CONTENT_TYPE
		response.status = 204
		try:
			entry = model.select().where(model._meta.primary_key == _id).get()
			entry.delete_instance()

		except Exception as e:
			if e.__class__.__name__.endswith("DoesNotExist"):
				abort(404, "The requested {} resource with id {} does not exist.".format(endpoint, _id))

			abort(400, e.message)

	return jsonp_delete
