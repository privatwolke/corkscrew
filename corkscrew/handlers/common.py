# coding: utf-8

from peewee import ForeignKeyField
from jsonapi import JsonAPIResource

def model_to_endpoint(model):
	return model.__name__.lower()


def get_primary_key(entry):
	return getattr(entry, entry.__class__._meta.primary_key.name)


def entry_to_resource(entry):
	meta = entry.__class__._meta
	primary_key_field = meta.primary_key
	primary_key = get_primary_key(entry)

	attributes = {}
	for field in meta.get_fields():
		if type(field) is ForeignKeyField:
			attributes[field.name] = get_primary_key(getattr(entry, field.name))
		elif not field is primary_key_field:
			attributes[field.name] = getattr(entry, field.name)

	return JsonAPIResource(primary_key, model_to_endpoint(entry.__class__), attributes = attributes)
