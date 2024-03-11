from .test_utils import TestCase
from confetti import Config
from confetti import exceptions


class PathAssignmentTest(TestCase):

    def setUp(self):
        super(PathAssignmentTest, self).setUp()
        self.conf = Config(dict(a=dict(b=dict(c=3)), d=4, e=None))

    def tearDown(self):
        super(PathAssignmentTest, self).tearDown()

    def test_invalid_path_assignment_to_path(self):
        with self.assertRaises(exceptions.InvalidPath):
            self.conf.assign_path("a.g.d", 3)

    def test_invalid_path_getting(self):
        with self.assertRaises(exceptions.InvalidPath):
            self.conf.get_path("a.g.d")

    def test_get_path_direct(self):
        self.assertEqual(4, self.conf.get_path("d"))

    def test_path_deducing_with_none(self):
        self.conf.root.a.b.c = None
        self.assertIsNone(self.conf.root.a.b.c)
        with self.assertRaises(exceptions.CannotDeduceType):
            self.conf.assign_path_expression("a.b.c=2", deduce_type=True)
        self.assertIsNone(self.conf.root.a.b.c)

    def test_path_assign_value_deduce_type(self):
        self.conf.root.a.b.c = 1
        self.conf.assign_path("a.b.c", "2", deduce_type=True)
        self.assertEqual(self.conf.root.a.b.c, 2)

    def test_path_deducing_with_none_force_type(self):
        self.conf.assign_path_expression("a.b.c=2", deduce_type=True, default_type=str)
        self.assertEqual(self.conf.root.a.b.c, 2)

    def test_path_deducing_with_compound_types(self):
        for initial_value, value in [([1, 2, 3], ["a", "b", 3]), ((1, 2), (3, 4, 5))]:
            self.conf["a"]["b"] = initial_value
            self.conf.assign_path_expression(
                "a.b={0!r}".format(value), deduce_type=True
            )
            self.assertEqual(self.conf["a"]["b"], value)

    def test_path_deducing_with_booleans(self):
        for false_literal in ("false", "False", "no", "n", "No", "N"):
            self.conf["a"]["b"]["c"] = True
            self.conf.assign_path_expression(
                "a.b.c={0}".format(false_literal), deduce_type=True
            )
            self.assertFalse(self.conf.root.a.b.c)
        for true_literal in ("true", "True", "yes", "y", "Yes", "Y"):
            self.conf["a"]["b"]["c"] = False
            self.conf.assign_path_expression(
                "a.b.c={0}".format(true_literal), deduce_type=True
            )
            self.assertTrue(self.conf.root.a.b.c)
        for invalid_literal in ("trueee", 0, 23, 2.3):
            with self.assertRaises(ValueError):
                self.conf.assign_path_expression(
                    "a.b.c={0}".format(invalid_literal), deduce_type=True
                )

    def test_assign_path_direct(self):
        self.conf.assign_path("d", 5)
        self.assertEqual(self.conf["d"], 5)
