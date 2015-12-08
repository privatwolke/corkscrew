# coding: utf-8

import sys
import json
import logging, traceback
from bottle import abort
from peewee import IntegrityError
from jsonapi import JsonAPIResponse, JsonAPIError, CONTENT_TYPE
from common import get_endpoint

def fn_error(error):
	error.content_type = CONTENT_TYPE
	doc = JsonAPIResponse()
	err = JsonAPIError(code = error.status, title = error.body)
	doc.errors.append(err)
	return json.dumps(dict(doc))


def ErrorHandler(fn):
	def outer(*args, **kwargs):
		try:
			return fn(*args, **kwargs)

		except ValueError:
			abort(400, "Could not parse request document. Be sure to use valid JSON.")

		except IntegrityError as e:
			if e.message.startswith("NOT NULL constraint"):
				field = e.message.split(": ")[1]
				if field.endswith("_id"):
					field = field[len(get_endpoint()["path"]) + 1 : -3]
				abort(400, field + " cannot be null")

			if "UNIQUE constraint" in e.message:
				abort(409, "This id is already taken.")

			abort(400, e)

		except AssertionError as e:
			abort(400, e.message)

		except Exception as e:
			if e.__class__.__name__.endswith("DoesNotExist"):
				abort(404, "The requested resource {} does not exist.".format(get_endpoint()["path"]))

			if e.message.startswith("Instance matching query"):
				abort(400, "Trying to set relationship with non-existant resource.")

			# log this unknown error
			logging.error("".join(traceback.format_exception(*sys.exc_info())))

			abort(500, e)

	return outer
