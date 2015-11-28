# coding: utf-8

import json
from jsonapi import JsonAPIResponse, JsonAPIError, CONTENT_TYPE

def fn_error(error):
	error.content_type = CONTENT_TYPE
	doc = JsonAPIResponse()
	err = JsonAPIError(code = error.status, title = error.body)
	doc.errors.append(err)
	return json.dumps(dict(doc))
