
import datetime
import functools

now = datetime.datetime.now


class ContextDecorator(object):
    def __call__(self, f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            with self:
                return f(*args, **kwargs)
        return decorated

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class transaction(object):
    atomic = ContextDecorator()
