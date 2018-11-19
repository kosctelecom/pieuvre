
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


class TestAllTransitionsMixin(object):
    factory_class = None
    transitions = []
    ignore_transitions = []

    def _create_instance(self, state):
        return self.factory_class(state=state)

    def _get_test_transitions(self):
        return [tr for tr in self.transitions if tr["name"] not in self.ignore_transitions]

    def test_all_transitions(self):
        for transition in self._get_test_transitions():
            sources = transition["source"] if isinstance(transition["source"], list) else [transition["source"], ]

            for source in sources:
                obj = self._create_instance(source)

                getattr(obj.workflow, transition["name"])()

                obj.refresh_from_db()
                self.assertEqual(obj.state, transition["destination"])
