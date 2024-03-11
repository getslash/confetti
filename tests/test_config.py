import os
import tempfile

from .test_utils import TestCase
from confetti import Config
from confetti import get_config_object_from_proxy
from confetti import exceptions
from confetti import Metadata
from sentinels import NOTHING


class BasicUsageTest(TestCase):

    def setUp(self):
        super(BasicUsageTest, self).setUp()
        self.conf = Config(dict(a=dict(b=2)))

    def test_init_with_nothing(self):
        conf = Config(NOTHING)
        self.assertEqual(conf.get_value(), {})

    def test_init_with_config(self):
        parent_conf = Config({"a": 1})
        child_conf = Config(parent_conf)
        nested_conf = child_conf.get_config("a")
        self.assertIs(nested_conf.get_parent(), child_conf)

    def test_getting(self):
        self.assertEqual(self.conf.root.a.b, 2)

    def test_setting(self):
        self.conf.root.a.b = 3
        self.assertEqual(self.conf.root.a.b, 3)

    def test_get_conf_from_proxy(self):
        self.assertIs(get_config_object_from_proxy(self.conf.root), self.conf)

    def test_proxy_hasattr(self):
        self.assertFalse(hasattr(self.conf.root.a, "c"))
        self.assertIsNone(getattr(self.conf.root.a, "c", None))

    def test_proxy_getitem(self):
        self.assertEqual(self.conf.root.a["b"], 2)
        self.assertRaises(KeyError, lambda: self.conf.root.a["c"])

    def test_proxy_dir(self):
        self.assertEqual(dir(self.conf.root), ["a"])
        self.assertEqual(dir(self.conf.root.a), ["b"])

    def test_pop(self):
        self.assertEqual(list(self.conf["a"].keys()), ["b"])
        self.conf["a"].pop("b")
        self.assertEqual(list(self.conf["a"].keys()), [])

    def test_setting_existing_paths_through_setitem(self):
        self.conf["a"]["b"] = 3
        self.assertEqual(self.conf.root.a.b, 3)

    def test_setting_existing_paths_through_assign_path(self):
        self.conf.assign_path("a.b", 3)
        self.assertEqual(self.conf.root.a.b, 3)

    def test_setting_nonexistent_paths(self):
        with self.assertRaises(exceptions.CannotSetValue):
            self.conf["a"]["c"] = 4
        with self.assertRaises(AttributeError):
            self.conf.root.a.c = 4

    def test_getting_through_getitem(self):
        self.assertIsInstance(self.conf["a"], Config)

    def test_contains(self):
        self.assertTrue("a" in self.conf)
        self.assertFalse("b" in self.conf)
        self.assertFalse("c" in self.conf["a"])
        self.assertTrue("b" in self.conf["a"])

    def test_item_not_found(self):
        with self.assertRaises(AttributeError):
            self.conf.root.a.c

    def test_keys(self):
        self.assertEqual(set(self.conf.keys()), set(["a"]))


class ExtendingTest(TestCase):

    def setUp(self):
        super(ExtendingTest, self).setUp()
        self.conf = Config({"a": 1})

    def test_extend_single_value(self):
        self.conf.extend({"b": 2})
        self.assertEqual(self.conf.root.b, 2)

    def test_extend_keyword_arguments(self):
        self.conf.extend(b=2)
        self.assertEqual(self.conf.root.b, 2)

    def test_extend_structure(self):
        self.conf.extend({"b": {"c": {"d": 2}}})
        self.assertEqual(self.conf.root.b.c.d, 2)

    def test_extend_structure_and_keywords(self):
        self.conf.extend({"b": 1, "c": 3}, b=2)
        self.assertEqual(self.conf.root.b, 2)
        self.assertEqual(self.conf.root.c, 3)

    def test_extend_preserves_nodes(self):
        self.conf.extend({"b": {"c": 2}})
        self.conf.extend({"b": {"d": 3}})
        self.assertEqual(self.conf.serialize_to_dict(), {"a": 1, "b": {"c": 2, "d": 3}})

    def test_extend_config(self):
        self.conf.extend(Config({"b": {"c": {"d": 2}}}))
        self.assertEqual(self.conf.root.b.c.d, 2)

    def test_extend_config_propagates_changes(self):
        new_cfg = Config({"b": {"c": 2}})
        self.conf.extend(new_cfg)
        self.assertEqual(self.conf.root.b.c, 2)
        new_cfg.root.b.c = 3
        self.assertEqual(self.conf.root.b.c, 3)

    def test_extend_config_preserves_metadata(self):
        new_cfg = Config({"b": {"c": 2 // Metadata(x=3)}})
        self.conf.extend(new_cfg)
        self.assertEqual(self.conf.get_config("b.c").metadata, {"x": 3})

    def test_extend_config_preserves_nodes(self):
        self.conf.extend(Config({"b": {"c": 2}}))
        self.conf.extend(Config({"b": {"c": 2, "d": 3}}))
        self.assertEqual(self.conf.serialize_to_dict(), {"a": 1, "b": {"c": 2, "d": 3}})

    def test_extend_config_prevents_losing_value(self):
        self.conf = Config({"a": 1})
        new_cfg = Config({"a": {"b": 2}})
        with self.assertRaises(exceptions.CannotSetValue):
            self.conf.extend(new_cfg)

    def test_extend_config_prevents_losing_path(self):
        self.conf = Config({"a": {"b": 1}})
        new_cfg = Config({"a": 1})
        with self.assertRaises(exceptions.CannotSetValue):
            self.conf.extend(new_cfg)

    def test_update_config_preserves_nodes(self):
        self.conf.update(Config({"b": {"c": 2}}))
        self.conf.update(Config({"b": {"d": 3}}))
        self.assertEqual(self.conf.serialize_to_dict(), {"a": 1, "b": {"c": 2, "d": 3}})


class HelperMethodsTest(TestCase):

    def setUp(self):
        super(HelperMethodsTest, self).setUp()
        self.config = Config(
            {
                "a": {
                    "b": 2,
                    "c": {
                        "d": 3,
                    },
                    "e": 4,
                },
                "f": 5,
            }
        )

    def test_traverse_leaves(self):
        self.assertEqual(
            sorted((path, c.get_value()) for path, c in self.config.traverse_leaves()),
            [("a.b", 2), ("a.c.d", 3), ("a.e", 4), ("f", 5)],
        )


class CopyingTest(TestCase):

    def test_copying_nested_dictionaries(self):
        raw_conf = {"a": {"b": 2}}
        conf1 = Config(raw_conf)
        conf2 = Config(raw_conf)
        conf1["a"]["b"] += 1
        self.assertNotEqual(conf1["a"]["b"], conf2["a"]["b"])


class LinkedConfigurationTest(TestCase):

    def setUp(self):
        super(LinkedConfigurationTest, self).setUp()
        self.conf1 = Config(dict(a=1))
        self.conf2 = Config(dict(c=2))
        self.conf1.extend({"b": self.conf2})

    def test_linked_configurations(self):
        self.assertIs(self.conf1["b"], self.conf2)

    def test_linked_backup_and_restore(self):
        self.conf1.backup()
        self.conf2["c"] = 3
        self.assertEqual(self.conf1.root.b.c, 3)
        self.conf1["a"] = 2
        self.conf1.restore()
        self.assertEqual(self.conf1.root.b.c, 2)

    def test_linked_backups_restore_parent_then_child(self):
        self.conf2.backup()
        self.conf1.backup()
        self.conf2["c"] = 4
        self.assertEqual(self.conf2.root.c, 4)
        self.conf1.restore()
        self.assertEqual(self.conf2.root.c, 2)
        self.conf2["c"] = 5
        self.assertEqual(self.conf2.root.c, 5)
        self.conf2.restore()
        self.assertEqual(self.conf2.root.c, 2)


class BackupTest(TestCase):

    def setUp(self):
        super(BackupTest, self).setUp()
        self.conf = Config(dict(a=1, b=2, c=[]))
        self.conf.extend(Config({"d": []}))

    def test_backup_context(self):
        with self.conf.backup_context():
            self.conf.root.a = 10
            assert self.conf.root.a == 10

        assert self.conf.root.a == 1

    def test_restore_no_backup(self):
        with self.assertRaises(exceptions.NoBackup):
            self.conf.restore()

    def test_discard(self):
        self.conf.backup()
        self.conf.discard_backup()
        with self.assertRaises(exceptions.NoBackup):
            self.conf.restore()

    def test_backup_copy(self):
        self.conf.backup()
        self.conf.root.c.append(0)
        self.conf.root.d.extend([2, 3])
        self.conf.restore()
        self.assertEqual(self.conf.root.c, [])
        self.assertEqual(self.conf.root.d, [])


class SerializationTest(TestCase):

    def setUp(self):
        super(SerializationTest, self).setUp()
        self.dict = dict(a=dict(b=dict(c=8)))
        self.conf = Config(self.dict)

    def test_serialization(self):
        result = self.conf.serialize_to_dict()
        self.assertIsNot(result, self.dict)
        self.assertEqual(result, self.dict)
        self.assertIsNot(result["a"], self.dict["a"])
        self.assertEqual(result["a"]["b"]["c"], 8)

    def test_serialization_with_assignment(self):
        self.conf.assign_path("a.b.c", 9)
        result = self.conf.serialize_to_dict()
        self.assertEqual(result["a"]["b"]["c"], 9)


class ConfigInitializationTest(TestCase):
    def test_from_filename(self):
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_file:
            temp_file.write('CONFIG = {"a": 1}')
            temp_file.flush()

            config = Config.from_filename(temp_file.name)
            self.assertEqual(config.root.a, 1)

        os.unlink(temp_file.name)

    def test_from_file(self):
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_file:
            temp_file.write('CONFIG = {"b": 2}')
            temp_file.flush()

            with open(temp_file.name, "rb") as f:
                config = Config.from_file(f, filename=temp_file.name)
                self.assertEqual(config.root.b, 2)

        os.unlink(temp_file.name)

    def test_from_string(self):
        config_str = 'CONFIG = {"c": 3}'
        config = Config.from_string(config_str)
        self.assertEqual(config.root.c, 3)

    def test_from_string_with_namespace(self):
        config_str = 'CONFIG = {"d": x}'
        namespace = {"x": 4}
        config = Config.from_string(config_str, namespace=namespace)
        self.assertEqual(config.root.d, 4)

    def test_from_file_with_namespace(self):
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_file:
            temp_file.write('CONFIG = {"e": y}')
            temp_file.flush()

            namespace = {"y": 5}
            with open(temp_file.name, "rb") as f:
                config = Config.from_file(
                    f, filename=temp_file.name, namespace=namespace
                )
                self.assertEqual(config.root.e, 5)

        os.unlink(temp_file.name)


class ConfigParentTest(TestCase):
    def test_set_parent_twice(self):
        parent_config = Config({"a": 1})
        child_config = Config({"b": 2})

        child_config.set_parent(parent_config)

        with self.assertRaises(RuntimeError):
            child_config.set_parent(parent_config)
