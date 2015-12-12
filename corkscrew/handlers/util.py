# coding: utf-8

import datetime
from bottle import request, response
from urlparse import urljoin
from peewee import ForeignKeyField, PrimaryKeyField
from corkscrew.jsonapi import JsonAPIResource, JsonAPIRelationships, CONTENT_TYPE

def model_to_endpoint(model):
	return model.__name__.lower()


def get_primary_key(entry):
	return getattr(entry, entry.__class__._meta.primary_key.name)


def entry_to_resource(entry, related, endpoints, linkage = False):
	model = entry.__class__
	meta = model._meta
	primary_key_field = meta.primary_key
	primary_key = get_primary_key(entry)

	if linkage:
		# we only want resource linkage
		return {
			u"id": unicode(primary_key),
			u"type": meta.name
		}

	# prepare the attribute dict and a relationship container
	attributes = {}
	base_uri = request.urlparts.scheme + "://" + request.urlparts.netloc
	relationships = JsonAPIRelationships(base_uri)

	for field in meta.sorted_fields:
		# for each field

		if isinstance(field, ForeignKeyField):
			# we have a reference to another model, retrieve it
			obj = getattr(entry, field.name)

			if obj:
				# the reference is not null
				relationships.add(
					field.name, # name of the relation
					endpoints[model], # the current endpoint to generate links
					entry_to_resource(obj, [], endpoints, linkage = True), # resource linkage
					primary_key # the current primary key
				)

			else:
				# the reference is null
				relationships.add(field.name, endpoints[model], None, key = primary_key)

		elif not isinstance(field, PrimaryKeyField):
			# the field is anything else than a primary key (we keep these out of the attributes dict)
			attr = getattr(entry, field.name)
			if isinstance(attr, datetime.date):
				# handle datetime instances
				attr = str(attr)

			# save the attribute
			attributes[field.name] = attr

	if related:
		# we have 1:n or n:m relations
		for field, rel in related.iteritems():
			if isinstance(rel, tuple):
				rel, via = rel

			data = []

			# retrieve the related resources
			for child_row in rel.select().where(get_reverse_field(rel, model) == primary_key):
				data.append(dict(entry_to_resource(child_row, [], endpoints, linkage = True)))

			relationships.add(field, endpoints[model], data, key = primary_key)

	# construct a resource object
	resource = JsonAPIResource(primary_key, meta.name, attributes = attributes)
	resource.links = { "self": request.url }

	if len(relationships):
		resource.relationships = relationships

	return resource


def get_reverse_field(child, parent):
	for field in child._meta.sorted_fields:
		if isinstance(field, ForeignKeyField) and field.rel_model == parent:
			return field


## DECORATORS

def ContentType(fn):
	def outer(*args, **kwargs):
		response.content_type = CONTENT_TYPE
		return fn(*args, **kwargs)
	return outer
