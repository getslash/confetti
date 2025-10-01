.. Confetti documentation master file, created by
   sphinx-quickstart on Fri Mar 22 23:33:10 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Confetti
========

Confetti deals mostly with :class:`.Config` objects. These objects represent nodes and leaves in a configuration structure, and provide most of the functionality for querying and manipulating the configuration.

By default, parts of the configuration, even scalar values, are wrapped in Config objects when possible. However, Confetti provides ways to access values as simple Python values.

Basic Operations
~~~~~~~~~~~~~~~~

Initializing Configurations
---------------------------

The most convenient way to initialize a configuration structure is by simply passing a nested dictionary into the :class:`.Config` constructor::

  from confetti import Config
  CONFIG = Config({
      "a" : {
          "b" : 2,
      }
  })

Confetti also has convenience helpers to load from files that contain the above structure (NB the capital ``CONFIG``), via the :func:`.Config.from_filename`, :func:`.Config.from_file` and :func:`.Config.from_string` methods.

Querying the Configuration Tree
-------------------------------

Getting Direct Values
+++++++++++++++++++++

The simplest and most memorizable way to access values in the configuration structure is through the ``root`` member of the Config object. This member is a proxy to the Config object and allows accessing values through attributes::

  >>> from confetti import Config
  >>> c = Config({
  ...   "a" : {"b" : {"c" : 12}},
  ... })
  >>> c.root.a.b.c
  12

You can also use ``__getitem__`` syntax (as in Python dicts) to access nodes and values::

  >>> c["a"]["b"]["c"]
  12

For getting a nested value you can also use **configuration path**, which are dotted notations of the above::

  >>> c.get_path("a.b.c")
  12

Getting Config Objects
++++++++++++++++++++++

For most manipulation and advanced querying purposes, a user would want to work with *config objects*, rather than direct values. Those provide more reflection capabilities and smarter traversal (e.g. finding the parent of a node). This is possible via the :func:`.Config.get_config` function::

 >>> c.get_config("a")
 <Config {'b': {'c': 12}}>

You can also use dotted notation::

 >>> c.get_config("a.b.c")
 <Config 12>

Modifying Configurations
------------------------

Existing Values
+++++++++++++++

Existing values can be changed pretty easily, both by using the ``root`` proxy, and by using ``__setitem__``::

  >>> c["a"]["b"]["c"] = 100
  >>> c.root.a.b.c = 100

New Values and Nodes
++++++++++++++++++++

To avoid mistakes when using or updating configurations, Confetti does not allow setting nonexistent values::

 >>> c["new_value"] = 1 # doctest: +IGNORE_EXCEPTION_DETAIL
 Traceback (most recent call last):
    ...
 CannotSetValue: ...

Configuration objects have the :func:`.Config.extend` method to assign new values or nested structures to an existing configuration, that does the trick:

 >>> c.extend({"new_value" : 1})
 >>> c.root.new_value
 1

It is possible to assign a path with a Config object, which is referenced in the parent Config, and can be updated:

 >>> new_conf = Config({"inner": 1})
 >>> c.extend({"linked_value":new_conf})
 >>> c.root.linked_value.inner
 1
 >>> new_conf.root.inner = 2
 >>> c.root.linked_value.inner
 2

However, it is not allowed to extend using a Config object if it will remove existing paths:

 >>> c.extend(Config({'extended_value':{'child1':1}}))
 >>> c.extend(Config({'extended_value':{'child2':2}})) # doctest: +IGNORE_EXCEPTION_DETAIL
 Traceback (most recent call last):
    ...
 CannotSetValue: ...

In the above example, in order to add the path c.root.extended_value.child2, without re-specifying extended_value.child1, use the :func:`.Config.update` method:

 >>> c.update(Config({'extended_value':{'child2':2}}))
 >>> c.root.extended_value.child1
 1
 >>> c.root.extended_value.child2
 2


Advanced Uses
~~~~~~~~~~~~~

Path Assignments
----------------

Config objects can assign to paths using the :func:`.Config.assign_path` method::

 >>> c.assign_path("a.b.c", 2)
 >>> c.root.a.b.c
 2

Which is a synonym for:

 >>> c.get_config("a.b.c").set_value(2)

In some cases you want to process config overrides from various sources that are not completely type safe, e.g. command-line or environment variables. Such variables would look like ``'some.value=2'``. Confetti provides a utility for easily assigning such expressions, optionally deducing the leaf type::

 >>> c.assign_path_expression("a.b.c=234", deduce_type=True)
 >>> c.root.a.b.c
 234

The default is no type deduction, which results in string values always::

 >>> c.assign_path_expression("a.b.c=230")
 >>> c.root.a.b.c
 '230'

Dirty/Clean States
------------------

 >>> cfg = Config({
 ...    'value': 1,
 ...    'subcfg': {
 ...       'value': 2,
 ...    }})
 >>> cfg.is_dirty()
 False
 >>> cfg.root.subcfg.value += 1
 >>> cfg.is_dirty()
 True
 >>> cfg['subcfg'].is_dirty()
 True

 >>> cfg.mark_clean()
 >>> cfg.is_dirty()
 False
 >>> cfg['subcfg'].is_dirty()
 False

Update Callbacks
----------------

You can register callbacks to be called after any value or subconfig is being changed::

 >>> @cfg.on_update
 ... def handle_update(config):
 ...     assert cfg is config
 ...     # handle the update here

Cross References
----------------

In many cases you want to set a single value in your configuration, and have other leaves take it by default. Instead of repeating yourself like so::

 >>> cfg = Config(dict(
 ...     my_value = 1337,
 ...     value_1 = 1337,
 ...     x = dict(
 ...         y = dict(
 ...             z = 1337,
 ...         )
 ...     )
 ... ))

You can do this:

 >>> from confetti import Ref
 >>> cfg = Config(dict(
 ...     my_value = 1337,
 ...     value_1 = Ref(".my_value"),
 ...     x = dict(
 ...         y = dict(
 ...             z = Ref("...my_value"),
 ...         )
 ...     )
 ... ))
 >>> cfg.root.x.y.z
 1337

Or you can apply a custom filter to the reference, to create derived values::

 >>> cfg = Config(dict(
 ...     my_value = 1337,
 ...     value_1 = Ref(".my_value", filter="I am {0}".format),
 ... ))
 >>> cfg.root.value_1
 'I am 1337'


Backing Up/Restoring
--------------------

Whenever you want to preserve the configuration prior to a change and restore it later, you can do it with :meth:`.Config.backup` and :meth:`.Config.restore`. They work like a stack, so they push and pop states::

 >>> c = Config({"value":2})
 >>> c['value']
 2
 >>> c.backup()
 >>> c['value'] = 3
 >>> c['value']
 3
 >>> c.backup()
 >>> c['value'] = 4
 >>> c['value']
 4
 >>> c.restore()
 >>> c['value']
 3
 >>> c.restore()
 >>> c['value']
 2

You can also use :meth:`.Config.backup_context` to wrap blocks of code with backup/restore operations::

 >>> with c.backup_context():
 ...    c['value'] = 4
 >>> c['value']
 2


Metadata
--------

Confetti supports attaching metadata to configuration values. This is can be done directly with manipulating the ``metadata`` attribute of the :class:`.Config` class, but also has a handy syntax making use of the ``//`` operator::

 >>> from confetti import Config, Metadata
 >>> cfg = Config({
 ...     "name" : "value" // Metadata(metadata_key="metadata_value"),
 ... })
 >>> cfg.get_config("name").metadata
 {'metadata_key': 'metadata_value'}




The confetti.config.Config Class
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: confetti.config.Config
   :members:
   :special-members:






Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

