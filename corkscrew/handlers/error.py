# coding: utf-8

import sys
import json
import logging
import traceback

from bottle import abort, request, response
from peewee import IntegrityError
from corkscrew.jsonapi import JsonAPIResponse, JsonAPIError, JsonAPIException
from corkscrew.jsonapi import CONTENT_TYPE


def fn_error(error):
    try:
        error.content_type = CONTENT_TYPE
        doc = JsonAPIResponse(request.url)
        err = JsonAPIError(code=error.status, title=error.body)
        doc.errors.append(err)
        return json.dumps(dict(doc), sort_keys=True)
    except:
        logging.error("".join(traceback.format_exception(*sys.exc_info())))


def ErrorHandler(fn):
    def outer(*args, **kwargs):
        response.content_type = CONTENT_TYPE

        try:
            return fn(*args, **kwargs)

        except ValueError:
            logging.error("".join(traceback.format_exception(*sys.exc_info())))
            abort(400, "Could not parse request. Be sure to use valid JSON.")

        except IntegrityError as e:
            if str(e).startswith("NOT NULL constraint"):
                field = e.message.split(": ")[1]
                if field.endswith("_id"):
                    field = field[:-3]

                abort(400, field + " cannot be null")

            if "UNIQUE constraint" in str(e):
                abort(409, "This id is already taken.")

            abort(400, e)

        except AssertionError as e:
            abort(400, e)

        except JsonAPIException as e:
            abort(e.status, e)

        except Exception as e:
            if e.__class__.__name__.endswith("DoesNotExist"):
                abort(404, "The requested resource does not exist.")

            if str(e).startswith("Instance matching query"):
                abort(400, "Trying to set relationship with invalid resource.")

            # log this unknown error
            logging.error("".join(traceback.format_exception(*sys.exc_info())))

            abort(500, e)

    return outer
