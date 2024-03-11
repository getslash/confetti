import itertools

import pytest
from confetti import Config


@pytest.fixture
def nested_config():
    returned = Config(
        {
            "value": 0,
            "a": {
                "value": 1,
                "b": {
                    "value": 2,
                },
            },
            "a2": {
                "value": 3,
            },
        }
    )
    return returned


@pytest.fixture
def checkpoint():
    return Checkpoint()


_timestamp = itertools.count(1000000)


class Checkpoint(object):

    called = False
    args = kwargs = timestamp = None

    def __call__(self, *args, **kwargs):
        self.called = True
        self.args = args
        self.kwargs = kwargs
        self.timestamp = next(_timestamp)
