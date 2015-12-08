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


	def register(self, model, endpoint = None, related = {}):
		endpoint = endpoint or "/" + model._meta.name

		# GET /{endpoint} -> List resources.
		self.get(endpoint)(fn_list(model, related))

		# GET /{endpoint}/{_id} -> Retrieve individual resource.
		self.get(endpoint + "/<_id>")(fn_get(model, related))

		# POST /{endpoint} -> Create a new resource.
		self.post(endpoint)(fn_create(model))

		# PATCH /{endpoint}/{_id} -> Patch an individual resource.
		self.route(endpoint + "/<_id>", "PATCH")(fn_patch(model, related))

		# DELETE /{endpoint}/{_id} -> Delete an individual resource.
		self.delete(endpoint + "/<_id>")(fn_delete(model))

		# Set up error handling.
		self.error_handler = { x: fn_error for x in xrange(400, 601) }

		# add forward relationships to single resources (1:1, n:1)
		for f in model._meta.sorted_fields:
			if isinstance(f, ForeignKeyField):
				self.register_relation(endpoint, f.name, model)

		# add reverse relationships (1:n, n:m)
		for field, rel in related.iteritems():
			if isinstance(rel, tuple):
				(child, via) = rel
				self.register_reverse_relation(endpoint, field, model, child, via)

			else:
				self.register_reverse_relation(endpoint, field, model, rel)


	def register_relation(self, endpoint, name, target):
		ep = "{}/<_id>/{}".format(endpoint, name)
		self.get(ep)(fn_get_relationship(target, name))

		ep = "{}/<_id>/relationships/{}".format(endpoint, name)
		self.get(ep)(fn_get_relationship(target, name, linkage = True))
		self.route(ep, "PATCH")(fn_patch_relationship(target, name))


	def register_reverse_relation(self, endpoint, name, parent, child, via = None):
		ep = "{}/<_id>/{}".format(endpoint, name)
		self.get(ep)(fn_get_reverse_relationship(child, parent))

		ep = "{}/<_id>/relationships/{}".format(endpoint, name)
		self.get(ep)(fn_get_reverse_relationship(child, parent, linkage = True))
