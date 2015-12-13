# coding: utf-8

import datetime
from bottle import request, response
from urlparse import urljoin
from peewee import ForeignKeyField, PrimaryKeyField
from corkscrew.jsonapi import JsonAPIResource, JsonAPIRelationships, JsonAPIException

def model_to_endpoint(model):
	return model.__name__.lower()


def get_primary_key(entry):
	return getattr(entry, entry.__class__._meta.primary_key.name)


def include_is_valid(include, entry, factory):
	related = factory.related if factory else {}

	for inc in include:
		if list(set(inc.split("."))) != inc.split("."):
			raise JsonAPIException("Circular include field specification detected.", status = 400)

		if len(inc):
			field = inc.split(".")[0]
			if not (hasattr(entry, field) or field in related.keys()):
				raise JsonAPIException("Unknown field to be included: " + field, status = 400)


def include_matches(include, field):
	matches = []
	for inc in include:
		if inc.startswith(field):
			matches.append(inc[len(field) + 1:])

	return matches


def entry_to_resource(entry, context, include = [], linkage = False):
	factory = context.get_factory(entry.__class__)
	model = entry.__class__
	meta = model._meta
	primary_key_field = meta.primary_key
	primary_key = get_primary_key(entry)

	# validate the include parameter
	include_is_valid(include, entry, factory)

	if linkage:
		# we only want resource linkage
		return ({
			u"id": unicode(primary_key),
			u"type": meta.name
		}, [])

	# prepare the attribute dict and a relationship container
	attributes = {}
	included = []
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
					context.get_endpoint(model), # the current endpoint to generate links
					entry_to_resource(obj, context, linkage = True)[0], # resource linkage
					primary_key # the current primary key
				)

				if include_matches(include, field.name):
					incdata, incinc = entry_to_resource(
						obj,
						context,
						include = include_matches(include, field.name)
					)

					included.append(incdata)
					included += incinc

			else:
				# the reference is null
				relationships.add(field.name, context.get_endpoint(model), None, key = primary_key)

		elif not isinstance(field, PrimaryKeyField):
			# the field is anything else than a primary key (we keep these out of the attributes dict)
			attr = getattr(entry, field.name)
			if isinstance(attr, datetime.date):
				# handle datetime instances
				attr = str(attr)

			# save the attribute
			attributes[field.name] = attr

	if factory and factory.related:
		# we have 1:n or n:m relations
		for field, rel in factory.related.iteritems():
			via = None

			if isinstance(rel, tuple):
				rel, via = rel

			data = []

			if via:
				query = rel.select().join(via).where(
					get_reverse_field(via, model) == primary_key
				)
			else:
				query = rel.select().where(
					get_reverse_field(rel, model) == primary_key
				)

			# retrieve the related resources
			for child_row in query:
				data.append(
					dict(entry_to_resource(child_row, context, linkage = True)[0])
				)

				if include_matches(include, field):
					incdata, incinc = entry_to_resource(
						child_row,
						context,
						include = include_matches(include, field)
					)

					included.append(incdata)
					included += incinc

			relationships.add(
				field,
				context.get_endpoint(model),
				data,
				key = primary_key
			)

	# construct a resource object
	resource = JsonAPIResource(primary_key, meta.name, attributes = attributes)

	# format self link
	if context.get_endpoint(model):
		resource.links = {
			"self": "{}://{}{}/{}".format(
				request.urlparts.scheme,
				request.urlparts.netloc,
				context.get_endpoint(model),
				primary_key
			)
		}

	if len(relationships):
		resource.relationships = relationships

	return (resource, included)


def get_reverse_field(child, parent):
	for field in child._meta.sorted_fields:
		if isinstance(field, ForeignKeyField) and field.rel_model == parent:
			return field
