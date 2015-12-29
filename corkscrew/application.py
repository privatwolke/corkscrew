# coding: utf-8

from bottle import Bottle
from peewee import ForeignKeyField
from corkscrew.handlers import fn_error
from corkscrew.handlers.util import Link


class CorkscrewApplicationContext(object):

    def __init__(self, app):
        self.app = app
        self.endpoints = {}
        self.factories = {}

    def get_factory(self, model):
        return self.factories[model] if model in self.factories else None

    def get_endpoint(self, factory_or_model):
        try:
            return self.endpoints[factory_or_model]
        except KeyError:
            try:
                return self.endpoints[self.get_factory(factory_or_model)]
            except KeyError:
                return None

    def add_factory(self, factory, endpoint):
        self.factories[factory.model] = factory
        self.endpoints[factory] = endpoint


class CorkscrewApplication(Bottle):

    def __init__(self, handler_factory):
        super(CorkscrewApplication, self).__init__()

        self.handler_factory = handler_factory
        self.context = CorkscrewApplicationContext(self)

        # setup default error handling
        self.error_handler = {x: fn_error for x in xrange(400, 601)}

    def register(self, model, related=None, endpoint=None, listener=None):
        endpoint = endpoint or "/" + model._meta.name
        related = related or {}
        factory = self.handler_factory(model, related, listener)

        self.context.add_factory(factory, endpoint)
        factory.context = self.context

        self.route(endpoint, ["GET", "OPTIONS"])(factory.list())
        self.route(endpoint + "/<_id>", ["GET", "OPTIONS"])(factory.get())
        self.route(endpoint, ["POST", "OPTIONS"])(factory.create())
        self.route(endpoint + "/<_id>", ["PATCH", "OPTIONS"])(factory.patch())

        self.route(
            endpoint + "/<_id>",
            ["DELETE", "OPTIONS"]
        )(factory.delete())

        # add forward relationships to single resources (1:1, n:1)
        for f in factory.model._meta.sorted_fields:
            if isinstance(f, ForeignKeyField):
                self.register_relation(factory, f.name, endpoint)

        # add reverse relationships (1:n, n:m)
        for name, target in factory.related.iteritems():
            if not isinstance(target, Link):
                target = Link(target)

            self.register_reverse_relation(factory, name, endpoint, target)

    def register_relation(self, factory, name, endpoint):
        ep = "{}/<_id>/{}".format(endpoint, name)
        self.route(ep, ["GET", "OPTIONS"])(factory.get_relationship(name))

        ep = "{}/<_id>/relationships/{}".format(endpoint, name)
        self.route(
            ep,
            ["GET", "OPTIONS"]
        )(factory.get_relationship(name, linkage=True))

        self.route(ep, ["PATCH", "OPTIONS"])(factory.patch_relationship(name))

    def register_reverse_relation(self, factory, name, endpoint, target):
        ep = "{}/<_id>/{}".format(endpoint, name)
        self.route(
            ep,
            ["GET", "OPTIONS"]
        )(factory.get_reverse_relationship(target))

        ep = "{}/<_id>/relationships/{}".format(endpoint, name)
        self.route(ep, ["PATCH", "OPTIONS"])(factory.patch_relationship(name))
        self.route(
            ep,
            ["GET", "OPTIONS"]
        )(factory.get_reverse_relationship(target, linkage=True))
