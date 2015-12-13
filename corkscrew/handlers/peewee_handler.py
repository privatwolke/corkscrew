# coding: utf-8

import json
from peewee import ForeignKeyField
from bottle import request, response

from corkscrew.jsonapi import JsonAPIValidator, JsonAPIResponse
from corkscrew.handlers.util import entry_to_resource, get_primary_key
from corkscrew.handlers import ErrorHandler, Listener


class PeeweeHandlerFactory(object):
	"""A Factory of Handlers for peewee models.

	This class wraps a peewee model and keeps a reference of its reverse
	relations. Additionally a listener may be specified that is notified when
	resources are created, retrieved, listed, patched or deleted.
	"""

	def __init__(self, model, related = {}, listener = Listener()):
		"""Return a new instance of PeeweeHandlerFactory.

		Keyword arguments:
		related -- a dictionary in the form of {"relation": OtherModel}
		listener -- a corkscrew.handlers.listener.Listener subclass
		"""

		self.model = model
		self.related = related
		self.listener = listener
		self.context = None


	def entry_to_resource(self, entry, include = [], linkage = False):
		"""Formats a peewee database row as a JsonAPIResource."""

		return entry_to_resource(entry, self.context, include, linkage)


	def get_reverse_field(self, target):
		"""Returns the back reference field from a target model to self.model."""

		for f in target._meta.sorted_fields:
			if isinstance(f, ForeignKeyField) and f.rel_model == self.model:
				return f


	def create(self):
		"""Returns a function that will create resources in response to POST."""

		@ErrorHandler
		def fn_create():
			"""Creates a new resource and returns it."""

			request_doc = json.loads(request.body.getvalue())
			JsonAPIValidator.validate_create(request_doc, self.model._meta.name)

			self.listener.before_create(request)
			response_doc = JsonAPIResponse()

			attributes = {}

			if "attributes" in request_doc["data"]:
				attributes = request_doc["data"]["attributes"]

			if "relationships" in request_doc["data"]:
				for key, data in request_doc["data"]["relationships"].iteritems():
					attributes[key] = data["data"]["id"]

			if "id" in request_doc["data"]:
				attributes["id"] = request_doc["data"]["id"]

			created = self.model.create(**attributes)
			response_doc.data = self.entry_to_resource(created)[0]

			self.listener.after_create(response_doc)

			response.set_header("Location", "{}/{}".format(
				request.url,
				get_primary_key(created))
			)

			return json.dumps(dict(response_doc), sort_keys = True)

		return fn_create


	def get(self):
		"""Returns a function that retrieves resources in response to GET."""

		@ErrorHandler
		def fn_get(_id):
			"""Retrieves a singlar resource by its ID."""

			self.listener.before_get(_id)
			response_doc = JsonAPIResponse()

			entry = self.model.select().where(
				self.model._meta.primary_key == _id
			).get()

			data, included = self.entry_to_resource(
				entry,
				include = request.query.include.split(",")
			)

			response_doc.data = data
			response_doc.included = included

			self.listener.after_get(response_doc)
			return json.dumps(dict(response_doc), sort_keys = True)

		return fn_get


	def get_relationship(self, relationship, linkage = False):
		"""Returns a function that retrieves or lists a relationship."""

		@ErrorHandler
		def fn_get_relationship(_id):
			"""Returns either a listing of the relationship or the data itself."""

			response_doc = JsonAPIResponse()

			entry = self.model.select().where(
				self.model._meta.primary_key == _id
			).get()

			relation = getattr(entry, relationship)
			# non existant relationships must return successful with data: null
			data, included = self.entry_to_resource(
				relation,
				include = request.query.include.split(","),
				linkage = linkage
			) if relation else (None, [])

			response_doc.data = data
			response_doc.included = included

			return json.dumps(dict(response_doc), sort_keys = True)

		return fn_get_relationship


	def get_reverse_relationship(self, target, via, linkage = False):
		"""Returns a function that retrieves or lists a reverse relationship."""

		reverse_field = self.get_reverse_field(via or target)

		if not reverse_field:
			raise Exception("There is no reverse field for this relationship: " + str(self.model) + " -> " + str(target))

		@ErrorHandler
		def fn_get_reverse_relationship(_id):
			"""Returns either listing of the reverse relationship or the data itself."""

			response_doc = JsonAPIResponse()

			if via:
				query = target.select().join(via).where(reverse_field == _id)
			else:
				query = target.select().where(reverse_field == _id)

			for entry in query:
				data, included = self.entry_to_resource(
					entry,
					include = request.query.include.split(","),
					linkage = linkage
				)

				response_doc.data.append(data)
				response_doc.included += included

			return json.dumps(dict(response_doc), sort_keys = True)

		return fn_get_reverse_relationship


	def list(self):
		"""Returns a function that lists resources."""

		@ErrorHandler
		def fn_list():
			"""Returns a listing of resources."""

			self.listener.before_list()
			response_doc = JsonAPIResponse()

			for entry in self.model.select():
				data, included = self.entry_to_resource(
					entry,
					include = request.query.include.split(",")
				)

				response_doc.data.append(data)
				response_doc.included += included

			self.listener.after_list(response_doc)
			return json.dumps(dict(response_doc), sort_keys = True)

		return fn_list


	def patch_relationship(self, relationship):
		"""Returns a function that patches a relationship."""

		@ErrorHandler
		def fn_patch_relationship(_id):
			"""Patches a relationship with the given ID and returns."""

			request_doc = json.loads(request.body.getvalue())
			JsonAPIValidator.validate_patch(request_doc, _id, None)

			# PATCH /res/<_id>/relationships/other_res is equal to patching the
			# main resource which is what we are doing now
			rewritten_request = {
				u"data": {
					u"id" : unicode(_id),
					u"type": unicode(self.model._meta.name),
					u"relationships": {
						unicode(relationship): {
							u"data": request_doc["data"]
						}
					}
				}
			}

			JsonAPIValidator.validate_patch(
				rewritten_request, _id, self.model._meta.name
			)

			return self.patch()(_id, request_doc = rewritten_request)

		return fn_patch_relationship


	def __patch_relationships(self, _id, relationships):
		"""Works through a data.relationships object and patches the given
		relationships in the data store.
		"""

		entry = self.model.select().where(
			self.model._meta.primary_key == _id
		).get()

		for key, relationship in relationships.iteritems():

			if key in self.related:
				# target model
				target = self.related[key]

				# this is a reverse relationship that will be updated
				reverse_field = self.get_reverse_field(target)

				with target._meta.database.atomic() as txn:
					# remove all existing links
					for row in target.select().where(reverse_field == entry):
						setattr(row, reverse_field.name, None)
						row.save()

					if isinstance(relationship["data"], list):
						# add new links
						for linkage in relationship["data"]:
							row = target.select().where(
								related[key]._meta.primary_key == int(linkage["id"])
							).get()

							setattr(row, reverse_field.name, entry)
							row.save()

			elif relationship["data"] is None:
				# this is a direct relationship that will be set to null
				setattr(entry, key, None)

			elif hasattr(entry, key):
				# this is a direct relationship with a new value
				setattr(entry, key, relationship["data"]["id"])

			else:
				# we should not encounter a non existant field
				raise JsonAPIException("Encountered unknown relationship field: '{}'.".format(key))

		entry.save()


	def patch(self):
		"""Returns a function that handles a PATCH request to a resource."""

		@ErrorHandler
		def fn_patch(_id, request_doc = None):
			"""Handles PATCH requests to the given resource."""

			request_doc = request_doc or json.loads(request.body.getvalue())
			JsonAPIValidator.validate_patch(request_doc, _id, self.model._meta.name)

			self.listener.before_patch(request_doc)

			entry = self.model.select().where(
				self.model._meta.primary_key == _id
			).get()

			if "attributes" in request_doc["data"]:
				# each attribute that is present will be updated
				for key, value in request_doc["data"]["attributes"].iteritems():
					setattr(entry, key, value)

				entry.save()

			if "relationships" in request_doc["data"]:
				# patch given relationships
				self.__patch_relationships(_id, request_doc["data"]["relationships"])

			if self.listener.after_patch(response):
				# if the listener changed something else then return the object
				return self.get()(_id)

			else:
				# nothing changed, we return a 204 No Content status
				response.status = 204

		return fn_patch


	def delete(self):
		"""Returns a function that handles DELETE requests."""

		@ErrorHandler
		def fn_delete(_id):
			"""Deletes a resource."""

			self.listener.before_delete(_id)

			entry = self.model.select().where(
				self.model._meta.primary_key == _id
			).get()

			entry.delete_instance()

			self.listener.after_delete(_id)

			# return a 204 No Content status
			response.status = 204

		return fn_delete
