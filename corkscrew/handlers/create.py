# coding: utf-8

import json
from common import *
from jsonapi import *
from bottle import request, response, abort
from peewee import IntegrityError


def fn_create(model, endpoint):
	def jsonp_create():
		response.content_type = CONTENT_TYPE
		doc = JsonAPIResponse()

		try:
			request_doc = json.loads(request.body.getvalue())
			assert "data" in request_doc, JsonAPIException("The request MUST include a single resource object as primary data.")
			assert type(request_doc["data"]) is type({}), JsonAPIException("The request MUST include a single resource object as primary data.")
			assert "type" in request_doc["data"], JsonAPIException("The resource object MUST contain at least a type member.")

			if not endpoint.endswith(request_doc["data"]["type"]):
				abort(409, JsonAPIException("Cannot create resources of type '{}'.".format(request_doc["data"]["type"])))

			# TODO: If a relationship is provided in the relationships member of the resource object, its value MUST be a relationship object with a data member. The value of this key represents the linkage the new resource is to have.

			if "attributes" in request_doc["data"]:
				attributes = request_doc["data"]["attributes"]
			else:
				attributes = {}

			if "relationships" in request_doc["data"]:
				for key, data in request_doc["data"]["relationships"].iteritems():
					assert "id" in data["data"], JsonAPIException("If a relationship is provided in the relationships member of the resource object, its value MUST be a relationship object with a data member.")
					attributes[key] = data["data"]["id"]

			if "id" in request_doc["data"]:
				attributes["id"] = request_doc["data"]["id"]

			created = model.create(**attributes)
			doc.data = entry_to_resource(created)

		except ValueError:
			abort(400, "Could not parse request document. Be sure to use valid JSON.")

		except IntegrityError as e:
			if e.message.startswith("NOT NULL constraint"):
				field = e.message.split(": ")[1]
				if field.endswith("_id"):
					field = field[len(endpoint) + 1 : -3]
				abort(400, field + " cannot be null")

			if "UNIQUE constraint" in e.message:
				abort(409, "This id is already taken.")

			abort(400, e)

		except Exception as e:
			if e.message.startswith("Instance matching query"):
				abort(400, "Trying to set relationship with non-existant resource.")

			abort(400, e)

		response.set_header("Location", "{}/{}".format(get_endpoint(), get_primary_key(created)))
		return json.dumps(dict(doc))
	return jsonp_create
