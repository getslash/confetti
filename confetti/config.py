import copy
from sentinels import NOTHING
from . import exceptions
from .ref import Ref
from .python3_compat import iteritems
from .utils import coerce_leaf_value


class Config(object):
    _backups = None

    def __init__(self, value=NOTHING, parent=None, metadata=None):
        super(Config, self).__init__()
        self._value = self._init_value(value)
        if isinstance(self._value, dict):
            self._fix_dictionary_value()
        self._parent = parent
        self.metadata = metadata
        self.root = ConfigProxy(self)

    def _init_value(self, value):
        if value is NOTHING:
            value = {}
        elif isinstance(value, dict):
            value = value.copy()
        return value

    def _fix_dictionary_value(self):
        to_replace = []
        for k, v in iteritems(self._value):
            if isinstance(v, dict):
                to_replace.append((k, Config(v, parent=self)))
        for k, v in to_replace:
            self._value[k] = v

    def get_value(self):
        """
        Gets the value of the config object, assuming it represents a leaf

        .. seealso:: :func:`is_leaf <confetti.config.Config.is_leaf>`
        """
        if self.is_leaf():
            return self._value
        returned = {}
        for key in self.keys():
            returned[key] = self.get_config(key).get_value()
        return returned

    def set_value(self, value):
        """
        Sets the value for the config object assuming it is a leaf
        """
        if not self.is_leaf():
            raise exceptions.CannotSetValue(
                "Cannot set value of a non-leaf config object")
        self._value = value

    def is_leaf(self):
        """
        Returns whether this config object is a leaf, i.e. represents a value rather than a tree node.
        """
        return not isinstance(self._value, dict)

    def traverse_leaves(self):
        """
        A generator, yielding tuples of the form (subpath, config_object) for each leaf config under
        the given config object
        """
        for key in self.keys():
            value = self.get_config(key)
            if value.is_leaf():
                yield key, value
            else:
                for subpath, cfg in value.traverse_leaves():
                    yield "{0}.{1}".format(key, subpath), cfg

    def __getitem__(self, item):
        """
        Retrieves a direct child of this config object assuming it exists. The child is returned as a value, not as a
        config object. If you wish to get the child as a config object, use :func:`Config.get_config`.

        Raises KeyError if no such child exists
        """
        returned = self._value[item]
        if isinstance(returned, Config) and returned.is_leaf():
            returned = returned._value
        if isinstance(returned, Ref):
            returned = returned.resolve(self)
        assert not isinstance(returned, dict)
        return returned

    def __contains__(self, child_name):
        """
        Checks if this config object has a child under the given child_name
        """
        return self.get(child_name, NOTHING) is not NOTHING

    def get(self, child_name, default=None):
        """
        Similar to ``dict.get()``, tries to get a child by its name, defaulting to None or a specific default value
        """
        try:
            return self[child_name]
        except KeyError:
            return default

    def get_config(self, path):
        """
        Returns the child under the name ``path`` (dotted notation) as a config object.
        """
        returned = self
        path_components = path.split(".")
        for p in path_components:
            child = returned._value.get(p, NOTHING)
            if child is NOTHING:
                raise exceptions.InvalidPath(
                    "Invalid path: {0!r}".format(path))
            if not isinstance(child, Config):
                child = returned._value[p] = Config(child, parent=returned)
            returned = child
        return returned

    def pop(self, child_name):
        """
        Removes a child by its name
        """
        return self._value.pop(child_name)

    def __setitem__(self, item, value):
        """
        Sets a value to a value (leaf) child. If the child does not currently exist, this will succeed
        only if the value assigned is a config object.
        """
        if item not in self._value:
            raise exceptions.CannotSetValue(
                "Cannot set key {0!r}".format(item))
        self._value[item] = value

    def extend(self, conf):
        """
        Extends a configuration files by adding values from a specified config or dict.
        This permits adding new (previously nonexisting) structures or nodes to the configuration.
        """
        for key, value in iteritems(conf):
            if isinstance(value, dict):
                if key not in self._value:
                    self._value[key] = {}
                self.get_config(key).extend(value)
            else:
                self._value[key] = value

    def keys(self):
        """
        Similar to ``dict.keys()`` - returns iterable of all keys in the config object
        """
        return self._value.keys()

    @classmethod
    def from_filename(cls, filename, namespace=None):
        """
        Initializes the config from a file named ``filename``. The file is expected to contain a variable named ``CONFIG``.
        """
        with open(filename, "rb") as f:
            return cls.from_file(f, filename)

    @classmethod
    def from_file(cls, f, filename="?", namespace=None):
        """
        Initializes the config from a file object ``f``. The file is expected to contain a variable named ``CONFIG``.
        """
        ns = dict(__file__=filename)
        if namespace is not None:
            ns.update(namespace)
        return cls.from_string(f.read(), namespace=namespace)

    @classmethod
    def from_string(cls, s, namespace=None):
        """
        Initializes the config from a string. The string is expected to contain the config as a variable named ``CONFIG``.
        """
        if namespace is None:
            namespace = {}
        else:
            namespace = dict(namespace)
        exec(s, namespace)
        return cls(namespace['CONFIG'])

    def backup(self):
        """
        Saves a copy of the current state in the backup stack, possibly to be restored later
        """
        if self._backups is None:
            self._backups = []
        self._backups.append(_get_state(self))

    def restore(self):
        """
        Restores the most recent backup of the configuration under this child
        """
        if not self._backups:
            raise exceptions.NoBackup()
        _set_state(self, self._backups.pop())

    def serialize_to_dict(self):
        """
        Returns a recursive dict equivalent of this config object
        """
        return _get_state(self)

    def get_parent(self):
        """
        Returns the parent config object
        """
        return self._parent

    def assign_path(self, path, value):
        """
        Assigns ``value`` to the dotted path ``path``.

        >>> config = Config({"a" : {"b" : 2}})
        >>> config.assign_path("a.b", 3)
        >>> config.root.a.b
        3
        """
        config = self.get_config(path)
        config.set_value(value)

    def assign_path_expression(self, expr, deduce_type=False, default_type=None):
        path, value = expr.split("=", 1)
        if deduce_type:
            leaf = self.get_path(path)
            value = coerce_leaf_value(path, value, leaf, default_type)
        self.assign_path(path, value)

    def get_path(self, path):
        """
        Gets a value by its dotted path

        >>> config = Config({"a" : {"b" : 2}})
        >>> config.get_path("a.b")
        2
        """
        return self.get_config(path).get_value()

    def __repr__(self):
        return "<Config {0}>".format(self.get_value())


class ConfigProxy(object):

    def __init__(self, conf):
        super(ConfigProxy, self).__init__()
        self._conf = conf

    def __dir__(self):
        return list(self._conf.keys())

    def __setattr__(self, attr, value):
        if attr.startswith("_"):
            return super(ConfigProxy, self).__setattr__(attr, value)
        assert isinstance(self._conf, Config)
        try:
            self._conf[attr] = value
        except exceptions.CannotSetValue:
            raise AttributeError(attr)

    def __getattr__(self, attr):
        value = self._conf[attr]
        if isinstance(value, dict):
            value = Config(value)
        if isinstance(value, Config):
            return ConfigProxy(value)
        return value


def _get_state(config):
    if isinstance(config, Config):
        if config.is_leaf():
            return config._value
        return _get_state(config._value)
    if isinstance(config, dict):
        returned = {}
        for key in config.keys():
            returned[key] = _get_state(config[key])
        return returned
    return config


def _set_state(config, state):
    assert isinstance(config, Config)
    for key in set(config.keys()) - set(state):
        config.pop(key)
    for key, value in iteritems(state):
        if isinstance(value, dict):
            _set_state(config[key], value)
        else:
            config[key] = value
