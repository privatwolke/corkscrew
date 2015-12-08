# coding: utf-8

import json
from common import *
from error import ErrorHandler
from jsonapi import *
from bottle import response


def fn_delete(model):
	endpoint = get_endpoint()

	@ErrorHandler
	@ContentType
	def jsonp_delete(_id):
		response.status = 204

		entry = model.select().where(model._meta.primary_key == _id).get()
		entry.delete_instance()

	return jsonp_delete
