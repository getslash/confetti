from .config import Config


class Metadata(object):
    def __init__(self, **kwargs):
        super(Metadata, self).__init__()
        self.metadata = kwargs

    def __rfloordiv__(self, value):
        if isinstance(value, Config):
            if value.metadata is None:
                value.metadata = {}
            value.metadata.update(self.metadata)
            return value
        return Config(value, metadata=self.metadata)
