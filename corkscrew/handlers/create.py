# coding: utf-8

import json
from common import *
from jsonapi import *
from bottle import request, response, abort


def fn_create(model):
	endpoint = model_to_endpoint(model)
	def jsonp_create():
		response.content_type = CONTENT_TYPE
		doc = JsonAPIResponse()

		try:
			request_doc = json.loads(request.body.getvalue())
			assert "data" in request_doc, JsonAPIException("The request MUST include a single resource object as primary data.")
			assert type(request_doc["data"]) is type({}), JsonAPIException("The request MUST include a single resource object as primary data.")
			assert "type" in request_doc["data"], JsonAPIException("The resource object MUST contain at least a type member.")
			assert request_doc["data"]["type"] == endpoint, JsonAPIException("Cannot create resources of type '{}'.".format(request_doc["data"]["type"]))

			# TODO: If a relationship is provided in the relationships member of the resource object, its value MUST be a relationship object with a data member. The value of this key represents the linkage the new resource is to have.

			if "attributes" in request_doc["data"]:
				created = model.create(**request_doc["data"]["attributes"])

			else:
				created = model.create()

			doc.data = entry_to_resource(created)

		except ValueError:
			abort(400, "Could not parse request document. Be sure to use valid JSON.")

		except IntegrityError as e:
			if e.message.startswith("NOT NULL constraint"):
				field = e.message.split(": ")[1]
				if field.endswith("_id"):
					field = field[len(endpoint) + 1 : -3]
				abort(400, field + " cannot be null")

			abort(400, e.message)

		except Exception as e:
			abort(400, e.message)

		return json.dumps(dict(doc))
	return jsonp_create
