from .exceptions import CannotResolveError


class Ref(object):

    def __init__(self, target, filter=None):
        super(Ref, self).__init__()
        self._target = target
        self._filter = filter

    def resolve(self, config):
        target = self._target
        if target.startswith("."):
            target = target[1:]
        while target.startswith("."):
            target = target[1:]
            if config is None:
                raise CannotResolveError("Cannot resolve {0}".format(self._target))
            config = config.get_parent()
        try:
            returned = config.get_path(target)
        except LookupError:
            raise CannotResolveError("Cannot resolve {0}".format(self._target))
        if self._filter is not None:
            returned = self._filter(returned)
        return returned
