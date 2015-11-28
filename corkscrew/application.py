# coding: utf-8

from bottle import Bottle
from corkscrew.handlers import *
from collections import defaultdict

class BottleApplication(Bottle):

	def register(self, model, endpoint = None):
		endpoint = "/" + model.__name__.lower()
		self.get(endpoint)(fn_list(model))
		self.get(endpoint + "/<_id>")(fn_get(model))
		self.post(endpoint)(fn_create(model))
		self.route(endpoint + "/<_id>", ["POST", "PATCH"])(fn_patch(model))
		self.delete(endpoint + "/<_id>")(fn_delete(model))
		self.error_handler = { x: fn_error for x in xrange(400, 601) }
