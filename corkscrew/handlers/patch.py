# coding: utf-8

import json
from common import *
from error import ErrorHandler
from jsonapi import *
from bottle import request, response


def fn_patch(model, related):

	@ErrorHandler
	@ContentType
	def jsonp_patch(_id):
		endpoint = get_endpoint()
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
			for key, data in request_doc["data"]["relationships"].iteritems():
				if data:
					assert "data" in data, JsonAPIException("If a relationship is provided in the relationships member of a resource object in a PATCH request, its value MUST be a relationship object with a data member.")

					if isinstance(data["data"], list) and key in related:
						reverse_field = get_reverse_field(related[key], model)
						# remove all existing links
						related[key].delete().where(reverse_field == entry).execute()

						# add new links
						for linkage in data["data"]:
							child_row = related[key].select().where(related[key]._meta.primary_key == linkage["id"]).get()
							setattr(child_row, reverse_field.name, entry)
							child_row.save()

					else:
						assert "id" in data["data"], JsonAPIException("A 'resource identifier object' MUST contain type and id members.")
						setattr(entry, key, data["data"]["id"])
				else:
					setattr(entry, key, None)

		entry.save()

	return jsonp_patch
