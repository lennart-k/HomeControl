"""Custom validators for voluptuous"""

import voluptuous as vol


class ConsistsOf:
    """
    Validate that the given schema element applies
    to every element in a sequence.

    >>> s = ConsistsOf({"a": int})
    >>> s([{"a": 1}, {"a": 2}, {"a": 3}])
    [{"a": 1}, {"a": 2}, {"a": 3}]
    """

    def __init__(self, schema, msg=None, extra: int=vol.PREVENT_EXTRA):
        self.schema = vol.Schema(schema, extra=extra)
        self.msg = msg

    # pylint: disable=invalid-name
    def __call__(self, v):
        if not hasattr(v, "__iter__"):
            return vol.Invalid('value is not iterable')

        return [self.schema(element) for element in v]

    def __repr__(self):
        return 'ConsistsOf(%s)' % (self.schema,)
