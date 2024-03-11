import copy

from contextlib import contextmanager

from sentinels import NOTHING

from . import exceptions
from .python3_compat import iteritems, string_types, itervalues
from .ref import Ref
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
        self._dirty = False
        self._update_callbacks = []

    def on_update(self, func):
        self._update_callbacks.append(func)

    def is_dirty(self):
        return self._dirty

    def notify_update(self):
        if not self._dirty:
            self._dirty = True

        if self._parent is not None:
            self._parent.notify_update()

        for hook in self._update_callbacks:
            hook(self)

    def mark_clean(self):
        stack = [self]
        while stack:
            root = stack.pop()
            if isinstance(root, dict):
                stack.extend(itervalues(root))
            elif isinstance(root, Config):
                stack.extend(root.itervalues())

            if isinstance(root, Config):
                assert isinstance(root._dirty, bool)
                root._dirty = False

    def _init_value(self, value):
        if value is NOTHING:
            value = {}
        elif isinstance(value, dict):
            value = value.copy()
        elif isinstance(value, Config):
            value.set_parent(self)
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
                "Cannot set value of a non-leaf config object"
            )
        self._value = value
        self.notify_update()

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
                raise exceptions.InvalidPath("Invalid path: {0!r}".format(path))
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
            raise exceptions.CannotSetValue("Cannot set key {0!r}".format(item))
        old_value = self._value[item]
        if isinstance(old_value, Config):
            old_metadata = old_value.metadata
        else:
            old_metadata = NOTHING
        self._value[item] = value
        if old_metadata is not NOTHING:
            if not isinstance(value, Config):
                self._value[item] = Config(value, parent=self)
            self._value[item].metadata = old_metadata
        self.notify_update()

    def extend(self, conf=None, **kw):
        """
        Extends a configuration files by adding values from a specified config or dict.
        This permits adding new (previously nonexisting) structures or nodes to the configuration.
        """
        if conf is None:
            conf = {}

        if isinstance(conf, Config):
            self._extend_from_conf(conf)
        else:
            self._extend_from_dict(conf)
        self._extend_from_dict(kw)

    def _extend_from_conf(self, conf):
        conf = dict((key, conf.get_config(key)) for key in conf.keys())
        for key, value in iteritems(conf):
            if key in self._value:
                self.get_config(key)._verify_config_paths(value)
        for key, value in iteritems(conf):
            self._value[key] = value

    def _verify_config_paths(self, conf):
        if self.is_leaf():
            if (isinstance(conf, Config) and not conf.is_leaf()) or isinstance(
                conf, dict
            ):
                raise exceptions.CannotSetValue(
                    "Setting {0} will cause a value to disappear from {1}".format(
                        conf, self
                    )
                )
        else:
            if conf.is_leaf():
                raise exceptions.CannotSetValue(
                    "Setting {0} will cause paths to disappear from {1}".format(
                        conf, self
                    )
                )
            else:
                for k in self._value.keys():
                    if k not in conf._value:
                        raise exceptions.CannotSetValue(
                            "Setting {0} will cause paths to disappear from {1}".format(
                                conf, self
                            )
                        )
                    self.get_config(k)._verify_config_paths(conf._value[k])

    def _extend_from_dict(self, d):
        for key, value in iteritems(d):
            if isinstance(value, dict):
                if key not in self._value:
                    self._value[key] = {}
                self.get_config(key).extend(value)
            else:
                self._value[key] = value

    def update(self, conf):
        conf = dict((key, conf.get_config(key)) for key in conf.keys())
        for key, value in iteritems(conf):
            if not value.is_leaf():
                if key not in self._value:
                    self._value[key] = {}
                self.get_config(key).update(value)
            else:
                self._value[key] = value

    def keys(self):
        """
        Similar to ``dict.keys()`` - returns iterable of all keys in the config object
        """
        return self._value.keys()

    def itervalues(self):
        return itervalues(self._value)

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
        return cls(namespace["CONFIG"])

    def backup(self):
        """
        Saves a copy of the current state in the backup stack, possibly to be restored later
        """
        if self._backups is None:
            self._backups = []
        self._backups.append(_get_state(self))

    @contextmanager
    def backup_context(self):
        """
        A context manager wrapping backup() and restore()
        """
        self.backup()
        try:
            yield
        finally:
            self.restore()

    def discard_backup(self):
        """
        Discards the latest backup made
        """
        self._backups.pop()

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

    def set_parent(self, parent):
        if self._parent is not None:
            raise RuntimeError("Config object already has a parent")
        self._parent = parent

    def assign_path(self, path, value, deduce_type=False, default_type=None):
        """
        Assigns ``value`` to the dotted path ``path``.

        >>> config = Config({"a" : {"b" : 2}})
        >>> config.assign_path("a.b", 3)
        >>> config.root.a.b
        3
        """
        config = self.get_config(path)
        if deduce_type and isinstance(value, string_types):
            leaf = self.get_path(path)
            value = coerce_leaf_value(path, value, leaf, default_type)

        config.set_value(value)

    def assign_path_expression(self, expr, deduce_type=False, default_type=None):
        path, value = expr.split("=", 1)
        self.assign_path(path, value, deduce_type, default_type)

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
        try:
            value = self._conf[attr]
        except LookupError:
            raise AttributeError(attr)
        if isinstance(value, dict):
            value = Config(value)
        if isinstance(value, Config):
            return ConfigProxy(value)
        return value

    def __getitem__(self, item):
        try:
            return getattr(self, item)
        except AttributeError:
            raise KeyError(item)


def _get_state(config):
    if isinstance(config, Config):
        if config.is_leaf():
            return copy.deepcopy(config._value)
        return _get_state(config._value)
    if isinstance(config, dict):
        returned = {}
        for key in config.keys():
            returned[key] = _get_state(config[key])
        return returned
    return copy.deepcopy(config)


def _set_state(config, state):
    assert isinstance(config, Config)
    for key in set(config.keys()) - set(state):
        config.pop(key)
    for key, value in iteritems(state):
        if isinstance(value, dict):
            _set_state(config[key], value)
        else:
            config[key] = value
