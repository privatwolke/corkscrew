# coding: utf-8

from bottle import Bottle
from peewee import ForeignKeyField
from corkscrew.handlers import *


class CorkscrewApplication(Bottle):

	def __init__(self):
		super(CorkscrewApplication, self).__init__()
		self.endpoints = {}
		self.error_handler = { x: fn_error for x in xrange(400, 601) }


	def register(self, factory, endpoint = None):
		endpoint = endpoint or "/" + factory.model._meta.name

		self.endpoints[factory.model] = endpoint
		factory.endpoints = self.endpoints

		self.get(endpoint)(factory.list())
		self.get(endpoint + "/<_id>")(factory.get())
		self.post(endpoint)(factory.create())
		self.route(endpoint + "/<_id>", "PATCH")(factory.patch())
		self.delete(endpoint + "/<_id>")(factory.delete())

		# add forward relationships to single resources (1:1, n:1)
		for f in factory.model._meta.sorted_fields:
			if isinstance(f, ForeignKeyField):
				self.register_relation(factory, f.name, endpoint)

		# add reverse relationships (1:n, n:m)
		for name, target in factory.related.iteritems():
			if isinstance(target, tuple):
				(target, via) = target
				self.register_reverse_relation(
					factory, name, endpoint, target, via
				)

			else:
				self.register_reverse_relation(factory, name, endpoint, target)


	def register_relation(self, factory, name, endpoint):
		ep = "{}/<_id>/{}".format(endpoint, name)
		self.get(ep)(factory.get_relationship(name))

		ep = "{}/<_id>/relationships/{}".format(endpoint, name)
		self.get(ep)(factory.get_relationship(name, linkage = True))

		self.route(ep, "PATCH")(factory.patch_relationship(name))


	def register_reverse_relation(self, factory, name, endpoint, target, via = None):
		ep = "{}/<_id>/{}".format(endpoint, name)
		self.get(ep)(factory.get_reverse_relationship(target))

		ep = "{}/<_id>/relationships/{}".format(endpoint, name)
		self.get(ep)(factory.get_reverse_relationship(target, linkage = True))
