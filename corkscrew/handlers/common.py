# coding: utf-8

import datetime
from bottle import request, response
from urlparse import urljoin
from peewee import ForeignKeyField, PrimaryKeyField
from jsonapi import JsonAPIResource, JsonAPIRelationships, CONTENT_TYPE

def model_to_endpoint(model):
	return model.__name__.lower()


def get_endpoint():
	return {
		"full": urljoin(request.urlparts.scheme + "://" + request.urlparts.netloc, request.urlparts.path),
		"path": request.urlparts.path
	}


def get_primary_key(entry):
	return getattr(entry, entry.__class__._meta.primary_key.name)


def entry_to_resource(entry, linkage = False, related = []):
	meta = entry.__class__._meta
	primary_key_field = meta.primary_key
	primary_key = get_primary_key(entry)

	if linkage:
		return {
			u"id": unicode(primary_key),
			u"type": model_to_endpoint(entry.__class__)
		}

	attributes = {}
	relationships = JsonAPIRelationships(get_endpoint()["full"])

	for field in meta.sorted_fields:
		if isinstance(field, ForeignKeyField):
			obj = getattr(entry, field.name)
			if obj:
				relationships.add(field.name, obj.__class__._meta.name, get_primary_key(obj))
			else:
				relationships.add(field.name)

		elif not isinstance(field, PrimaryKeyField):
			attr = getattr(entry, field.name)
			if isinstance(attr, datetime.date):
				attr = str(attr)

			attributes[field.name] = attr

	if related:
		for field, rel in related.iteritems():
			if isinstance(rel, tuple):
				rel, via = rel

			relationships.add(field)

	res = JsonAPIResource(primary_key, model_to_endpoint(entry.__class__), attributes = attributes)
	res.links = { "self": get_endpoint()["full"] }

	if len(relationships):
		res.relationships = relationships

	return res


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
