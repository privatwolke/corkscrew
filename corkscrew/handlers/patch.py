# coding: utf-8

import json
from common import *
from jsonapi import *
from bottle import request, response, abort
from peewee import IntegrityError


def fn_patch(model, endpoint, relationship = None):

	def jsonp_patch(_id):
		response.content_type = CONTENT_TYPE
		response.status = 202
		doc = JsonAPIResponse()

		try:
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
				for key, data in request_doc["data"]["attributes"].iteritems():
					setattr(entry, key, data["data"]["id"])

			entry.save()
			doc.data = entry_to_resource(entry)

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
			if e.__class__.__name__.endswith("DoesNotExist"):
				abort(404, "The requested {} resource with id {} does not exist.".format(endpoint, _id))

			abort(400, e.message)

		return json.dumps(dict(doc))
	return jsonp_patch


def fn_patch_relationship(model, relationship):
	def jsonp_patch_relationship(_id):
		response.content_type = CONTENT_TYPE
		response.status = 204
		doc = JsonAPIResponse()

		try:
			request_doc = json.loads(request.body.getvalue())
			assert "data" in request_doc, JsonAPIException("The request MUST include a single resource object as primary data.")
			assert type(request_doc["data"]) is type({}), JsonAPIException("The request MUST include a single resource object as primary data.")
			assert "type" in request_doc["data"], JsonAPIException("The request MUST include a single resource object as primary data.")
			assert "id" in request_doc["data"], JsonAPIException("The request MUST include a single resource object as primary data.")

			entry = model.select().where(model._meta.primary_key == _id).get()
			setattr(entry, relationship, request_doc["data"]["id"])
			entry.save()

		except ValueError:
			abort(400, "Could not parse request document. Be sure to use valid JSON.")

		except IntegrityError as e:
			if e.message.startswith("NOT NULL constraint"):
				field = e.message.split(": ")[1]
				if field.endswith("_id"):
					field = field[len(endpoint) + 1 : -3]
				abort(400, field + " cannot be null")

			abort(400, e)

		except Exception as e:
			if e.__class__.__name__.endswith("DoesNotExist"):
				abort(404, "The requested {} resource with id {} does not exist.".format(endpoint, _id))

			abort(400, e)

	return jsonp_patch_relationship
