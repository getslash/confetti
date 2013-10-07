from .test_utils import TestCase
from confetti import Config
from confetti import get_config_object_from_proxy
from confetti import exceptions


class BasicUsageTest(TestCase):

    def setUp(self):
        super(BasicUsageTest, self).setUp()
        self.conf = Config(dict(
            a=dict(
                b=2
            )
        ))

    def test__getting(self):
        self.assertEquals(self.conf.root.a.b, 2)

    def test__setting(self):
        self.conf.root.a.b = 3
        self.assertEquals(self.conf.root.a.b, 3)

    def test__get_conf_from_proxy(self):
        self.assertIs(get_config_object_from_proxy(self.conf.root), self.conf)

    def test__proxy_dir(self):
        self.assertEquals(dir(self.conf.root), ['a'])
        self.assertEquals(dir(self.conf.root.a), ['b'])

    def test__pop(self):
        self.assertEquals(list(self.conf['a'].keys()), ['b'])
        self.conf['a'].pop('b')
        self.assertEquals(list(self.conf['a'].keys()), [])

    def test__setting_existing_paths_through_setitem(self):
        self.conf["a"]["b"] = 3
        self.assertEquals(self.conf.root.a.b, 3)

    def test__setting_existing_paths_through_assign_path(self):
        self.conf.assign_path('a.b', 3)
        self.assertEquals(self.conf.root.a.b, 3)

    def test__setting_nonexistent_paths(self):
        with self.assertRaises(exceptions.CannotSetValue):
            self.conf['a']['c'] = 4
        with self.assertRaises(AttributeError):
            self.conf.root.a.c = 4

    def test__getting_through_getitem(self):
        self.assertIsInstance(self.conf['a'], Config)

    def test__contains(self):
        self.assertTrue("a" in self.conf)
        self.assertFalse("b" in self.conf)
        self.assertFalse("c" in self.conf["a"])
        self.assertTrue("b" in self.conf["a"])

    def test__item_not_found(self):
        with self.assertRaises(LookupError):
            self.conf.root.a.c

    def test__keys(self):
        self.assertEquals(set(self.conf.keys()), set(['a']))


class ExtendingTest(TestCase):

    def setUp(self):
        super(ExtendingTest, self).setUp()
        self.conf = Config({
            "a": 1
        })

    def test__extend_single_value(self):
        self.conf.extend({"b": 2})
        self.assertEquals(self.conf.root.b, 2)

    def test__extend_structure(self):
        self.conf.extend({
            "b": {
                "c": {
                    "d": 2
                }
            }
        })
        self.assertEquals(self.conf.root.b.c.d, 2)

    def test__extend_preserves_nodes(self):
        self.conf.extend({"b": {"c": 2}})
        self.conf.extend({"b": {"d": 3}})
        self.assertEquals(
            self.conf.serialize_to_dict(),
            {"a": 1, "b": {"c": 2, "d": 3}}
        )


class HelperMethodsTest(TestCase):

    def setUp(self):
        super(HelperMethodsTest, self).setUp()
        self.config = Config({
            "a": {
                "b": 2,
                "c": {
                    "d": 3,
                },
                "e": 4,
            },
            "f": 5,
        })

    def test__traverse_leaves(self):
        self.assertEquals(
            sorted((path, c.get_value())
                   for path, c in self.config.traverse_leaves()),
            [("a.b", 2), ("a.c.d", 3), ("a.e", 4), ("f", 5)])


class CopyingTest(TestCase):

    def test__copying_nested_dictionaries(self):
        raw_conf = {"a": {"b": 2}}
        conf1 = Config(raw_conf)
        conf2 = Config(raw_conf)
        conf1["a"]["b"] += 1
        self.assertNotEquals(conf1["a"]["b"], conf2["a"]["b"])


class LinkedConfigurationTest(TestCase):

    def setUp(self):
        super(LinkedConfigurationTest, self).setUp()
        self.conf1 = Config(dict(a=1))
        self.conf2 = Config(dict(c=2))
        self.conf1.extend({"b": self.conf2})

    def test__linked_configurations(self):
        self.assertIs(self.conf1['b'], self.conf2)

    def test__linked_backup_and_restore(self):
        self.conf1.backup()
        self.conf2['c'] = 3
        self.assertEquals(self.conf1.root.b.c, 3)
        self.conf1['a'] = 2
        self.conf1.restore()
        self.assertEquals(self.conf1.root.b.c, 2)

    def test__linked_backups_restore_parent_then_child(self):
        self.conf2.backup()
        self.conf1.backup()
        self.conf2['c'] = 4
        self.assertEquals(self.conf2.root.c, 4)
        self.conf1.restore()
        self.assertEquals(self.conf2.root.c, 2)
        self.conf2['c'] = 5
        self.assertEquals(self.conf2.root.c, 5)
        self.conf2.restore()
        self.assertEquals(self.conf2.root.c, 2)


class BackupTest(TestCase):

    def setUp(self):
        super(BackupTest, self).setUp()
        self.conf = Config(dict(a=1, b=2))

    def test__restore_no_backup(self):
        with self.assertRaises(exceptions.NoBackup):
            self.conf.restore()

class SerializationTest(TestCase):

    def setUp(self):
        super(SerializationTest, self).setUp()
        self.dict = dict(
            a=dict(
                b=dict(
                    c=8
                )
            )
        )
        self.conf = Config(self.dict)

    def test__serialization(self):
        result = self.conf.serialize_to_dict()
        self.assertIsNot(result, self.dict)
        self.assertEquals(result, self.dict)
        self.assertIsNot(result['a'], self.dict['a'])
        self.assertEquals(result['a']['b']['c'], 8)

    def test__serialization_with_assignment(self):
        self.conf.assign_path("a.b.c", 9)
        result = self.conf.serialize_to_dict()
        self.assertEquals(result['a']['b']['c'], 9)
