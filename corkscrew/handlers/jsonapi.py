# coding: utf-8

CONTENT_TYPE = "application/vnd.api+json"

class JsonAPIBase(object):
	def __init__(self, **kwargs):
		for key, value in kwargs.iteritems():
			setattr(self, key, value)

	def __iter__(self):
		return self.generator().__iter__()


class JsonAPIException(Exception):
	pass


class JsonAPIResponse(JsonAPIBase):
	def __init__(self, **kwargs):
		if not hasattr(self, "data"):     self.data = []
		if not hasattr(self, "errors"):   self.errors = []
		if not hasattr(self, "included"): self.included = []

	def generator(self):
		if hasattr(self, "meta") and self.meta:
			yield ("meta", dict(self.meta))

		if self.errors:
			yield ("errors", [dict(error) for error in self.errors])
			return

		if type(self.data) is type([]):
			yield ("data", [dict(d) for d in self.data])
		elif self.data is None:
			yield ("data", None)
		else:
			yield ("data", dict(self.data))

		if not ((hasattr(self, "meta") and self.meta) or hasattr(self, "data") or self.errors):
			raise JsonAPIException("A document MUST contain at least one of the following top-level members: data, errors, meta.")



class JsonAPIError(JsonAPIBase):
	def generator(self):
		if hasattr(self, "id")     and self.id:     yield ("id",     self.id)
		if hasattr(self, "links")  and self.links:  yield ("links",  dict(self.links))
		if hasattr(self, "status") and self.status: yield ("status", doc["status"])
		if hasattr(self, "code")   and self.code:   yield ("code",   str(self.code))
		if hasattr(self, "title")  and self.title:  yield ("title",  str(self.title))
		if hasattr(self, "detail") and self.detail: yield ("detail", str(self.detail))
		if hasattr(self, "source") and self.source: yield ("source", dict(self.source))
		if hasattr(self, "meta")   and self.meta:   yield ("meta",   dict(self.meta))


class JsonAPIResource(JsonAPIBase):
	def __init__(self, _id, _type, attributes = {}):
		self.id = _id
		self.type = _type
		self.attributes = attributes

	@property
	def attributes(self):
		return self.__attributes

	@attributes.setter
	def attributes(self, value):
		if "id" in value: del value["id"]
		if "type" in value: del value["type"]
		self.__attributes = value

	def generator(self):
		yield ("id", str(self.id))
		yield ("type", str(self.type))
		if hasattr(self, "attributes")    and self.attributes:    yield ("attributes",    dict(self.attributes))
		if hasattr(self, "relationships") and self.relationships: yield ("relationships", dict(self.relationships))
		if hasattr(self, "links")         and self.links:         yield ("links",         dict(self.links))
		if hasattr(self, "meta")          and self.meta:          yield ("meta",          dict(self.meta))


class JsonAPIRelationships(JsonAPIBase):
	def __init__(self, endpoint):
		self.data = {}
		self.endpoint =  endpoint

	def __len__(self):
		return len(self.data)

	def add(self, _id, relation, _type, value):
		self.data[relation] = {
			"links": {
				"related": "{}/{}/{}".format(self.endpoint, _id, relation),
				"self": "{}/{}/relationships/{}".format(self.endpoint, _id, relation)
			}
		}
		if _type and value:
			self.data[relation]["data"] = { "id": value, "type": _type }

	def generator(self):
		for key, value in self.data.iteritems():
			yield (key, value)
