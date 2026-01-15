from flask import jsonify
from marshmallow import fields


class JsonifiableGenerator(list):
    """
    Inherite from list, so compatible with JSONEncoder, but must be initialized
    with a generator. Implement __bool__ as used by JSONEncoder.
    """

    def __init__(self, gen):
        self.gen = gen
        self.empty = None

    def __iter__(self):
        if self.empty is None:
            bool(self)
        if not self.empty:
            yield self.first_item
            yield from self.gen

    def __bool__(self):
        if self.empty is None:
            try:
                self.first_item = next(self.gen)
                self.empty = False
            except StopIteration:
                self.empty = True
        return not self.empty

    __repr__ = object.__repr__


class GeneratorField(fields.List):
    """
    As marshmallow List field, but if value is not a list (e.g. map or generator),
    return a JsonifiableGenerator instead of a list.
    """

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        result = map(lambda each: self.inner._serialize(each, attr, obj, **kwargs), value)
        if isinstance(value, list):
            result = list(result)
        else:
            result = JsonifiableGenerator(result)
        return result


def geojsonify(*args, **kwargs):
    response = jsonify(*args, **kwargs)
    response.mimetype = "application/geo+json"
    return response
