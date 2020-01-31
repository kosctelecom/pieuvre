"""
utils.py
=================================================
Utils.
"""


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


class transaction:
    """
    No-op replacement for Django transaction if Django is not installed.
    """

    atomic = ContextDecorator()


class TestAllTransitionsMixin:
    """
    Mixin to launch all transitions of a given workflow to perform
    a basic sanity check.

    Attributes:
        factory_class: factory class used to instanciate a model instance
            for tests
        transitions (list): list of transitions to test
        ignore_transitions (list): list of transitions to ignore

    """

    factory_class = None
    transitions = []
    ignore_transitions = []

    def _create_instance(self, state):
        return self.factory_class(state=state)

    def _get_test_transitions(self):
        return [
            tr for tr in self.transitions if tr["name"] not in self.ignore_transitions
        ]

    def test_all_transitions(self):
        for transition in self._get_test_transitions():
            sources = (
                transition["source"]
                if isinstance(transition["source"], list)
                else [transition["source"]]
            )

            for source in sources:
                obj = self._create_instance(source)

                # Make sure the transition can execute
                getattr(obj.workflow, transition["name"])()

                # There are no guarantee that obj.state is equal to transition["destination"]
                # Because the transition could trigger other transitions (that could even lead
                # back to the initial state).
                # Hence there is no point in checking the object state.
