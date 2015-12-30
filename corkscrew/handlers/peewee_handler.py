# coding: utf-8

import json

from peewee import ForeignKeyField
from bottle import request, response

from corkscrew.jsonapi import JsonAPIValidator
from corkscrew.jsonapi import JsonAPIResponse
from corkscrew.jsonapi import JsonAPIException
from corkscrew.handlers import util
from corkscrew.handlers import ErrorHandler, Listener


class PeeweeHandlerFactory(object):
    """A Factory of Handlers for peewee models.

    This class wraps a peewee model and keeps a reference of its reverse
    relations. Additionally a listener may be specified that is notified when
    resources are created, retrieved, listed, patched or deleted.
    """

    def __init__(self, model, related=None, listener=None):
        """Return a new instance of PeeweeHandlerFactory.

        Keyword arguments:
        related -- a dictionary in the form of {"relation": OtherModel}
        listener -- a corkscrew.handlers.listener.Listener subclass
        """

        self.model = model
        self.related = related or {}
        self.listener = listener or Listener()
        self.context = None

    def __entry_to_resource(self, entry,
                            include=None, fields=None, linkage=False):
        """Formats a peewee database row as a JsonAPIResource."""

        return util.entry_to_resource(entry, self.context, include or [],
                                      fields or {}, linkage)

    def __get_reverse_field(self, target):
        """Returns the reverse reference from a target model to self.model."""

        t = target.via or target.target

        for f in t._meta.sorted_fields:
            if target.on:
                if target.on == f.name:
                    return f

            elif isinstance(f, ForeignKeyField) and f.rel_model == self.model:
                return f

    def __get(self, _id):
        """Retrieves a singlar resource by its ID."""

        response_doc = JsonAPIResponse(request.url)

        entry = self.model.select().where(
            self.model._meta.primary_key == _id
        ).get()

        data, included = self.__entry_to_resource(
            entry,
            include=request.query.include.split(","),
            fields=util.parse_fields_parameter()
        )

        response_doc.data = data
        response_doc.included = included

        return json.dumps(dict(response_doc), sort_keys=True)

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

                if not isinstance(target, util.Link):
                    target = util.Link(target)

                if target.via:
                    reverse_field = self.__get_reverse_field(target)
                    target.via.delete().where(reverse_field == entry).execute()

                    if isinstance(relationship["data"], list):
                        for linkage in relationship["data"]:
                            rel = target.via()
                            setattr(rel, reverse_field.name, entry)
                            setattr(
                                rel,
                                target.target._meta.name,
                                linkage["id"]
                            )
                            rel.save()

                else:

                    # this is a reverse relationship that will be updated
                    rev_field = self.__get_reverse_field(target)

                    with target.target._meta.database.atomic():
                        # remove all existing links
                        for row in target.target.select().where(
                            rev_field == entry
                        ):
                            if rev_field.null:
                                setattr(row, rev_field.name, None)
                                row.save()
                            else:
                                raise JsonAPIException(
                                    "You can't orphan a " + str(row)
                                    + " resource.",
                                    status=400
                                )

                        if isinstance(relationship["data"], list):
                            # add new links
                            for linkage in relationship["data"]:
                                row = target.target.select().where(
                                    target.target._meta.primary_key
                                    == linkage["id"]
                                ).get()

                                setattr(row, rev_field.name, entry)
                                row.save()

            elif relationship["data"] is None:
                # this is a direct relationship that will be set to null
                setattr(entry, key, None)

            elif hasattr(entry, key):
                # this is a direct relationship with a new value
                setattr(entry, key, relationship["data"]["id"])

            else:
                # we should not encounter a non existant field
                raise JsonAPIException(
                    "Encountered unknown relationship field: '{}'.".format(key)
                )

        entry.save()

    def create(self):
        """Returns a function that creates resources in response to POST."""

        @ErrorHandler
        def fn_create():
            """Creates a new resource and returns it."""

            if request.method == "OPTIONS":
                return

            request_doc = json.loads(request.body.getvalue())
            JsonAPIValidator.validate_create(
                request_doc,
                self.model._meta.name
            )

            self.listener.before_create(request)

            attributes = {}

            if "attributes" in request_doc["data"]:
                attributes = request_doc["data"]["attributes"]

            if "relationships" in request_doc["data"]:
                for k, dat in request_doc["data"]["relationships"].iteritems():
                    attributes[k] = dat["data"]["id"]

            if "id" in request_doc["data"]:
                primary = self.model._meta.primary_key.name
                attributes[primary] = request_doc["data"]["id"]

            created = self.model.create(**attributes)

            self.listener.after_create(created)

            response.set_header("Location", "{}/{}".format(
                request.url,
                util.get_primary_key(created))
            )

            return self.__get(util.get_primary_key(created))

        return fn_create

    def get(self):
        """Returns a function that retrieves resources in response to GET."""

        @ErrorHandler
        def fn_get(_id):
            """Retrieves a singlar resource by its ID."""

            if request.method == "OPTIONS":
                return

            self.listener.before_get(_id)
            response_doc = self.__get(_id)
            self.listener.after_get(response_doc)

            return response_doc

        return fn_get

    def get_relationship(self, relationship, linkage=False):
        """Returns a function that retrieves or lists a relationship."""

        @ErrorHandler
        def fn_get_relationship(_id):
            """Returns either a listing of the relationship or the data itself
            depending on the linkage parameter.
            """

            if request.method == "OPTIONS":
                return

            response_doc = JsonAPIResponse(request.url)

            entry = self.model.select().where(
                self.model._meta.primary_key == _id
            ).get()

            relation = getattr(entry, relationship)
            # non existant relationships must return successful with data: null
            data, included = self.__entry_to_resource(
                relation,
                include=request.query.include.split(","),
                fields=util.parse_fields_parameter(),
                linkage=linkage
            ) if relation else (None, [])

            response_doc.data = data
            response_doc.included = included

            return json.dumps(dict(response_doc), sort_keys=True)

        return fn_get_relationship

    def get_reverse_relationship(self, target, linkage=False):
        """Returns a function that will retrieve or list a reverse
        relationship.
        """

        reverse_field = self.__get_reverse_field(target)

        if not reverse_field:
            raise Exception("There is no reverse field for this relationship: "
                            + str(self.model) + " -> " + str(target.on))

        @ErrorHandler
        def fn_get_reverse_relationship(_id):
            """Returns either a listing of the reverse relationship or the data
            itself, depending on the linkage parameter.
            """

            if request.method == "OPTIONS":
                return

            response_doc = JsonAPIResponse(request.url)

            if target.via:
                query = target.target.select().join(target.via).where(
                    reverse_field == _id
                )
            else:
                query = target.target.select().where(reverse_field == _id)

            for entry in query:
                data, included = self.__entry_to_resource(
                    entry,
                    include=request.query.include.split(","),
                    fields=util.parse_fields_parameter(),
                    linkage=linkage
                )

                response_doc.data.append(data)
                response_doc.included += included

            return json.dumps(dict(response_doc), sort_keys=True)

        return fn_get_reverse_relationship

    def list(self):
        """Returns a function that lists resources."""

        @ErrorHandler
        def fn_list():
            """Returns a listing of resources."""

            if request.method == "OPTIONS":
                return

            self.listener.before_list()
            response_doc = JsonAPIResponse(request.url)

            for entry in self.model.select():
                data, included = self.__entry_to_resource(
                    entry,
                    include=request.query.include.split(","),
                    fields=util.parse_fields_parameter()
                )

                response_doc.data.append(data)
                response_doc.included += included

            self.listener.after_list(response_doc)
            return json.dumps(dict(response_doc), sort_keys=True)

        return fn_list

    def patch_relationship(self, relationship):
        """Returns a function that patches a relationship."""

        @ErrorHandler
        def fn_patch_relationship(_id):
            """Patches a relationship with the given ID and returns."""

            if request.method == "OPTIONS":
                return

            request_doc = json.loads(request.body.getvalue())
            # JsonAPIValidator.validate_patch(request_doc, _id, None)

            # PATCH /res/<_id>/relationships/other_res is equal to patching the
            # main resource which is what we are doing now
            rewritten_request = {
                u"data": {
                    u"id": unicode(_id),
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

            return self.patch()(_id, request_doc=rewritten_request)

        return fn_patch_relationship

    def patch(self):
        """Returns a function that handles a PATCH request to a resource."""

        @ErrorHandler
        def fn_patch(_id, request_doc=None):
            """Handles PATCH requests to the given resource."""

            if request.method == "OPTIONS":
                return

            request_doc = request_doc or json.loads(request.body.getvalue())
            JsonAPIValidator.validate_patch(
                request_doc,
                _id,
                self.model._meta.name
            )

            self.listener.before_patch(request_doc)

            entry = self.model.select().where(
                self.model._meta.primary_key == _id
            ).get()

            if "attributes" in request_doc["data"]:
                # each attribute that is present will be updated
                for key, val in request_doc["data"]["attributes"].iteritems():
                    setattr(entry, key, val)

                entry.save()

            if "relationships" in request_doc["data"]:
                # patch given relationships
                self.__patch_relationships(
                    _id,
                    request_doc["data"]["relationships"]
                )

            if self.listener.after_patch(response):
                # if the listener changed something else then return the object
                return self.__get(_id)

            else:
                # nothing changed, we return a 204 No Content status
                response.status = 204

        return fn_patch

    def delete(self):
        """Returns a function that handles DELETE requests."""

        @ErrorHandler
        def fn_delete(_id):
            """Deletes a resource."""

            if request.method == "OPTIONS":
                return

            self.listener.before_delete(_id)

            entry = self.model.select().where(
                self.model._meta.primary_key == _id
            ).get()

            entry.delete_instance()

            self.listener.after_delete(_id)

            # return a 204 No Content status
            response.status = 204

        return fn_delete
