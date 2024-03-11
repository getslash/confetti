from .test_utils import TestCase
from confetti import Config, Ref


class CrossReferencingTest(TestCase):
    VALUE = 239829382

    def test_references(self):
        conf = Config(dict(a=dict(b=self.VALUE, references_b=Ref("b")))).root
        self.assertEqual(conf.a.references_b, self.VALUE)

    def test_references_traversal(self):
        conf = Config(
            dict(
                a=dict(
                    a_1=dict(
                        value=23232,
                        ref_1=Ref(".value"),
                        ref_2=Ref("..a_2.value"),
                        ref_3=Ref("...b.b_1.value"),
                    ),
                    a_2=dict(
                        value=383872,
                    ),
                ),
                b=dict(
                    b_1=dict(
                        value=287870997,
                    )
                ),
            )
        ).root
        self.assertEqual(conf.a.a_1.ref_1, conf.a.a_1.value)
        self.assertEqual(conf.a.a_1.ref_2, conf.a.a_2.value)
        self.assertEqual(conf.a.a_1.ref_3, conf.b.b_1.value)
