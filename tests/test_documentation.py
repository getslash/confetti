from unittest import TestCase
import os
import doctest


class DocumentationTest(TestCase):

    def test_doctests(self):
        for p, _, filenames in os.walk(
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "doc"))
        ):
            for filename in filenames:
                if not filename.endswith(".rst"):
                    continue
                filename = os.path.join(p, filename)
                result = doctest.testfile(filename, module_relative=False)
                self.assertEqual(result.failed, 0, "%s tests failed!" % result.failed)
