# coding: utf-8

import datetime

from bottle import request
from peewee import ForeignKeyField, PrimaryKeyField

from corkscrew.jsonapi import JsonAPIResource
from corkscrew.jsonapi import JsonAPIRelationships
from corkscrew.jsonapi import JsonAPIException


class Link(object):

    def __init__(self, target, via=None, on=None):
        self.target = target
        self.via = via
        self.on = on

    def __str__(self):
        return "Link({}, via={}, on={})".format(self.target, self.via, self.on)


def get_primary_key(entry):
    return getattr(entry, entry.__class__._meta.primary_key.name)


def parse_fields_parameter():
    fields = {}
    for param in request.query:
        if param.startswith("fields["):
            fields[param[7:-1]] = getattr(request.query, param).split(",")

    return fields


def include_is_valid(include, entry, factory):
    related = factory.related if factory else {}

    for inc in include:
        if list(set(inc.split("."))) != inc.split("."):
            raise JsonAPIException(
                "Circular include field specification detected.",
                status=400
            )

        if len(inc):
            field = inc.split(".")[0]
            if not (hasattr(entry, field) or field in related.keys()):
                raise JsonAPIException(
                    "Unknown field to be included: " + field, status=400
                )


def include_matches(include, field):
    matches = []
    for inc in include:
        if inc.startswith(field):
            matches.append(inc[len(field) + 1:])

    return matches


def entry_to_resource(entry, context,
                      include=None, fields=None, linkage=False):
    """Converts a peewee model instance to a resource object."""

    include = include or []
    fields = fields or []

    factory = context.get_factory(entry.__class__)
    model = entry.__class__
    meta = model._meta
    primary_key = get_primary_key(entry)

    # validate the include parameter
    include_is_valid(include, entry, factory)

    if linkage:
        # we only want resource linkage
        return ({
            u"id": unicode(primary_key),
            u"type": meta.name
        }, [])

    # prepare the attribute dict and a relationship container
    attributes = {}
    included = []
    base_uri = request.urlparts.scheme + "://" + request.urlparts.netloc
    relationships = JsonAPIRelationships(base_uri)

    for field in meta.sorted_fields:
        # for each field

        if meta.name in fields and field.name not in fields[meta.name]:
            # the client requested certain fields and this is not one of them
            continue

        if isinstance(field, ForeignKeyField):
            # we have a reference to another model, retrieve it
            obj = getattr(entry, field.name)

            if obj:
                # the reference is not null
                relationships.add(
                    field.name,  # name of the relation
                    context.get_endpoint(model),  # the current endpoint
                    entry_to_resource(obj, context, linkage=True)[0],
                    primary_key  # the current primary key
                )

                if include_matches(include, field.name):
                    incdata, incinc = entry_to_resource(
                        obj,
                        context,
                        include=include_matches(include, field.name),
                        fields=fields
                    )

                    included.append(incdata)
                    included += incinc

            else:
                # the reference is null
                relationships.add(
                    field.name,
                    context.get_endpoint(model),
                    None,
                    key=primary_key
                )

        elif not isinstance(field, PrimaryKeyField):
            # the field is anything else than a primary key
            attr = getattr(entry, field.name)
            if isinstance(attr, datetime.date):
                # handle datetime instances
                attr = str(attr)

            # save the attribute
            attributes[field.name] = attr

    if factory and factory.related:
        # we have 1:n or n:m relations
        for field, rel in factory.related.iteritems():

            if not isinstance(rel, Link):
                rel = Link(rel)

            if meta.name in fields and field not in fields[meta.name]:
                # the client requested certain fields, but not this one
                continue

            data = []

            if rel.via:
                query = rel.target.select().join(rel.via).where(
                    get_reverse_field(rel.via, model) == primary_key
                )
            else:
                query = rel.target.select().where(
                    get_reverse_field(rel.target, model) == primary_key
                )

            # retrieve the related resources
            for child_row in query:
                data.append(
                    dict(
                        entry_to_resource(child_row, context, linkage=True)[0]
                    )
                )

                if include_matches(include, field):
                    incdata, incinc = entry_to_resource(
                        child_row,
                        context,
                        include=include_matches(include, field),
                        fields=fields
                    )

                    included.append(incdata)
                    included += incinc

            relationships.add(
                field,
                context.get_endpoint(model),
                data,
                key=primary_key
            )

    # construct a resource object
    resource = JsonAPIResource(primary_key, meta.name, attributes=attributes)

    # add a self link to the resource if it has its own endpoint
    # note that models that are not exposed directly through app.register do
    # not have self links.
    if context.get_endpoint(model):
        resource.links = {
            "self": "{}://{}{}/{}".format(
                request.urlparts.scheme,
                request.urlparts.netloc,
                context.get_endpoint(model),
                primary_key
            )
        }

    if len(relationships):
        resource.relationships = relationships

    return (resource, included)


def get_reverse_field(child, parent):
    for field in child._meta.sorted_fields:
        if isinstance(field, ForeignKeyField) and field.rel_model == parent:
            return field
