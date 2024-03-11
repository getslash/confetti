import platform
from types import MethodType

IS_PY3 = platform.python_version() >= "3"

if IS_PY3:
    iteritems = lambda d: iter(d.items())  # not dict.items!!! See above
    itervalues = lambda d: iter(d.values())

    create_instance_method = MethodType
    basestring = str
    string_types = (basestring,)
    from functools import reduce
else:
    iteritems = (
        lambda d: d.iteritems()
    )  # not dict.iteritems!!! we support ordered dicts as well
    itervalues = lambda d: d.itervalues()

    from __builtin__ import basestring

    string_types = (str,)
    from __builtin__ import reduce


def items_list(dictionary):
    return list(iteritems(dictionary))
