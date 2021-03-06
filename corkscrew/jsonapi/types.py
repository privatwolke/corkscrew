# coding: utf-8


def urljoin(*parts):
    return "/".join(part.strip("/") for part in parts)

CONTENT_TYPE = "application/vnd.api+json"


class JsonAPIBase(object):
    def __init__(self, **kwargs):
        for key, value in kwargs.iteritems():
            setattr(self, key, value)

    def __iter__(self):
        return self.generator().__iter__()


class JsonAPIException(Exception):
    def __init__(self, message, status=500):
        self.status = status
        super(JsonAPIException, self).__init__(message)


class JsonAPIResponse(JsonAPIBase):
    def __init__(self, self_url, **kwargs):
        self.data = []
        self.errors = []
        self.included = []
        self.links = {u"self": self_url}

    def generator(self):
        if hasattr(self, "meta") and self.meta:
            yield ("meta", dict(self.meta))

        if self.errors:
            yield ("errors", [dict(error) for error in self.errors])
            return

        if isinstance(self.data, list):
            yield ("data", [dict(d) for d in self.data])
        elif self.data is None:
            yield ("data", None)
        else:
            yield ("data", dict(self.data))

        if self.included:
            included = []
            for inc in self.included:
                i = dict(inc)
                if i not in included:
                    included.append(i)

            yield ("included", included)

        if not ((hasattr(self, "meta") and self.meta) or hasattr(self, "data")
                or self.errors):
            raise JsonAPIException(
                "A document MUST contain at least one of the following"
                "top-level members: data, errors, meta."
            )

        if hasattr(self, "links") and self.links:
            yield ("links", dict(self.links))


class JsonAPIError(JsonAPIBase):
    def generator(self):
        if hasattr(self, "id") and self.id:
            yield ("id",     self.id)

        if hasattr(self, "links") and self.links:
            yield ("links",  dict(self.links))

        if hasattr(self, "status") and self.status:
            yield ("status", self.status)

        if hasattr(self, "code") and self.code:
            yield ("code",   str(self.code))

        if hasattr(self, "title") and self.title:
            yield ("title",  str(self.title))

        if hasattr(self, "detail") and self.detail:
            yield ("detail", str(self.detail))

        if hasattr(self, "source") and self.source:
            yield ("source", dict(self.source))

        if hasattr(self, "meta") and self.meta:
            yield ("meta",   dict(self.meta))


class JsonAPIResource(JsonAPIBase):
    def __init__(self, _id, _type, attributes=None):
        self.id = _id
        self.type = _type
        self.attributes = attributes or {}

    @property
    def attributes(self):
        return self.__attributes

    @attributes.setter
    def attributes(self, value):
        if "id" in value:
            del value["id"]

        if "type" in value:
            del value["type"]

        self.__attributes = value

    def generator(self):
        yield ("id", str(self.id))
        yield ("type", str(self.type))

        if hasattr(self, "attributes") and self.attributes:
            yield ("attributes", dict(self.attributes))

        if hasattr(self, "relationships") and self.relationships:
            yield ("relationships", dict(self.relationships))

        if hasattr(self, "links") and self.links:
            yield ("links", dict(self.links))

        if hasattr(self, "meta") and self.meta:
            yield ("meta", dict(self.meta))


class JsonAPIRelationships(JsonAPIBase):
    def __init__(self, base_uri):
        self.data = {}
        self.base_uri = base_uri

    def __len__(self):
        return len(self.data)

    def __make_links(self, relation, endpoint, key):
        key = "/" + str(key) if key else ""
        return {
            "links": {
                "related": urljoin(self.base_uri, endpoint, key, relation),
                "self": urljoin(
                    self.base_uri,
                    endpoint,
                    key,
                    "relationships", relation
                )
            }
        }

    def add(self, relation, endpoint, data, key=None):
        self.data[relation] = self.__make_links(relation, endpoint, key)
        self.data[relation]["data"] = data

    def generator(self):
        for key, value in self.data.iteritems():
            yield (key, value)
