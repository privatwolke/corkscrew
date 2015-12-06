# coding: utf-8

from bottle import Bottle
from peewee import ForeignKeyField
from corkscrew.handlers import *
from collections import defaultdict
from urlparse import urljoin

class BottleApplication(Bottle):

	def __init__(self, base_uri = None):
		self.base_uri = base_uri
		super(BottleApplication, self).__init__()


	def register(self, model, endpoint = None, relationships = []):
		endpoint = endpoint or "/" + model._meta.name
		abs_endpoint = urljoin(self.base_uri, endpoint)

		self.get(endpoint)(fn_list(model, abs_endpoint))
		self.get(endpoint + "/<_id>")(fn_get(model, abs_endpoint))
		self.post(endpoint)(fn_create(model, abs_endpoint))
		self.route(endpoint + "/<_id>", ["POST", "PATCH"])(fn_patch(model, abs_endpoint))
		self.delete(endpoint + "/<_id>")(fn_delete(model))
		self.error_handler = { x: fn_error for x in xrange(400, 601) }

		for f in model._meta.sorted_fields:
			if isinstance(f, ForeignKeyField):
				self.register_relation(endpoint, abs_endpoint, model, f.name)

		for name, relation in relationships:
			field = filter(lambda x: x.rel_model != model, filter(lambda x: isinstance(x, ForeignKeyField), relation._meta.sorted_fields))[0]
			self.register_relation(endpoint, abs_endpoint, relation, name)


	def register_relation(self, endpoint, abs_endpoint, model, name):
		ep = "{}/<_id>/{}".format(endpoint, name)
		self.get(ep)(fn_get(model, abs_endpoint, relationship = name))

		ep = "{}/<_id>/relationships/{}".format(endpoint, name)
		self.get(ep)(fn_get(model, abs_endpoint, relationship = name))
		self.route(ep, ["PATCH"])(fn_patch_relationship(model, relationship = name))
