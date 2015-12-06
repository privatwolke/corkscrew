# coding: utf-8

import datetime
from bottle import request
from urlparse import urljoin
from peewee import ForeignKeyField, PrimaryKeyField
from jsonapi import JsonAPIResource, JsonAPIRelationships

def model_to_endpoint(model):
	return model.__name__.lower()


def get_endpoint():
	return urljoin(request.urlparts.scheme + "://" + request.urlparts.netloc, request.urlparts.path)


def get_primary_key(entry):
	return getattr(entry, entry.__class__._meta.primary_key.name)

def entry_to_resource(entry):
	meta = entry.__class__._meta
	primary_key_field = meta.primary_key
	primary_key = get_primary_key(entry)

	attributes = {}
	relationships = JsonAPIRelationships(get_endpoint())

	for field in meta.get_fields():
		if isinstance(field, ForeignKeyField):
			obj = getattr(entry, field.name)
			if obj:
				relationships.add(field.name, obj.__class__._meta.name, get_primary_key(obj))
			else:
				relationships.add(field.name, None, None)

		elif not isinstance(field, PrimaryKeyField):
			attr = getattr(entry, field.name)
			if isinstance(attr, datetime.date):
				attr = str(attr)

			attributes[field.name] = attr

	res = JsonAPIResource(primary_key, model_to_endpoint(entry.__class__), attributes = attributes)

	if len(relationships):
		res.relationships = relationships

	return res
