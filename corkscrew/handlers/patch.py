# coding: utf-8

import json
from common import *
from error import ErrorHandler
from jsonapi import *
from bottle import request, response


def fn_patch(model, related, endpoints):

	@ErrorHandler
	def jsonp_patch(_id):
		endpoint = endpoints[model]
		response.status = 204

		request_doc = json.loads(request.body.getvalue())
		assert "data" in request_doc, JsonAPIException("The request MUST include a single resource object as primary data.")
		assert type(request_doc["data"]) is type({}), JsonAPIException("The request MUST include a single resource object as primary data.")
		assert "type" in request_doc["data"], JsonAPIException("The resource object MUST contain type and id members.")
		assert "id" in request_doc["data"], JsonAPIException("The resource object MUST contain type and id members.")
		assert request_doc["data"]["id"] == _id, JsonAPIException("The values for 'id' in the URI and the request document do not match.")

		entry = model.select().where(model._meta.primary_key == _id).get()

		if "attributes" in request_doc["data"]:
			for key, value in request_doc["data"]["attributes"].iteritems():
				setattr(entry, key, value)

		if "relationships" in request_doc["data"]:
			for key, relationship in request_doc["data"]["relationships"].iteritems():
				assert relationship, JsonAPIException("If a relationship is provided in the relationships member of a resource object in a PATCH request, its value MUST be a relationship object with a data member.")

				if isinstance(relationship["data"], list) and key in related:
					reverse_field = get_reverse_field(related[key], model)

					with related[key]._meta.database.atomic() as txn:
						# remove all existing links
						for child_row in related[key].select().where(reverse_field == entry):
							setattr(child_row, reverse_field.name, None)
							child_row.save()

						# add new links
						for linkage in relationship["data"]:
							child_row = related[key].select().where(related[key]._meta.primary_key == int(linkage["id"])).get()
							setattr(child_row, reverse_field.name, entry)
							child_row.save()

				elif relationship["data"] is None:
					setattr(entry, key, None)

				else:
					assert "id" in relationship["data"], JsonAPIException("A 'resource identifier object' MUST contain type and id members.")
					setattr(entry, key, relationship["data"]["id"])

		entry.save()

	return jsonp_patch
