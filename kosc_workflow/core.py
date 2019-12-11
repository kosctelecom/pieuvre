
import logging

from functools import partial

from .exceptions import (
    ForbiddenTransition,
    InvalidTransition,
    TransitionDoesNotExist,
    TransitionNotFound
)
try:
    from django.db import transaction
    from django.utils.timezone import now
except ImportError:
    from .utils import transaction, now

logger = logging.getLogger(__name__)

ON_ENTER_STATE_PREFIX = "on_enter_"
ON_EXIT_STATE_PREFIX = "on_exit_"
AFTER_TRANSITION_PREFIX = "after_"
BEFORE_TRANSITION_PREFIX = "before_"
CHECK_TRANSITION_PREFIX = "check_"


def update_decorated_functions(obj, states, function):

    for state in states:
        if state in obj:
            obj[state].append(function)
        else:
            obj[state] = [function, ]


class Workflow(object):
    """
    Workflow class

    Attributes:
        initial_state(string): initial state of the model
        states(list): The list of states, it can be a list of strings or dicts
                      or a mix of them
            Example:
                states = ["draft", "submitted", "completed", "rejected"]

        transitions(list): List of transitions:
            Example:
                transitions = [
                    {
                        "name": "submit",
                        "source": "draft",
                        "destination": "submitted",
                        "date_field": "submission_date"
                    },
                    {
                        "name": "complete",
                        "source": "submitted",
                        "destination": "completed"
                    }
                ]
    """

    from_any_transition = "*"
    state_field_name = "state"
    states = []
    transitions = []
    db_logging = False
    db_logging_class = None

    events = {
        # "name": "method"
    }

    event_manager_classes = ()

    def __init__(self, model):

        self.model = model
        self._check_initial_state()
        self.event_managers = [klass(model) for klass in self.get_event_manager_classes()]

        super(Workflow, self).__init__()

        self._on_enter_state_check = {}
        self._on_exit_state_check = {}
        self._on_enter_state_hook = {}
        self._on_exit_state_hook = {}

        self.gather_decorated_functions()

    def gather_decorated_functions(self):
        """
        Construct _on_enter_state_checks and _on_exit_state_checks
        """

        for attr in dir(self):
            if attr.startswith("__"):
                continue

            func = getattr(self, attr)
            if not callable(func):
                continue

            for deco in ("_on_enter_state_check", "_on_exit_state_check", "_on_enter_state_hook",
                         "_on_exit_state_hook"):

                if hasattr(func, deco):
                    update_decorated_functions(
                        getattr(self, deco),
                        getattr(func, deco),
                        func)

    def process_event(self, name, data):
        if name not in self.events:
            return

        func = getattr(self, self.events[name])
        return func(data)

    def _check_initial_state(self):
        pass

    def get_event_manager_classes(self):
        """
        Return the list of event manager

        :return: list
        """
        return self.event_manager_classes

    def _get_model_state(self):
        """
        Get the state of model using the state name defined in the class
        :return: the value of model state
        """

        return getattr(self.model, self.state_field_name)

    @property
    def state(self):
        return self._get_model_state()

    def update_model_state(self, value):
        """
        Update the state of the model
        :param value(string): the value of the state to be updated
        :return: None
        """
        logger.debug("Updating model {} to {}".format(
            self.state_field_name, value))

        setattr(self.model, self.state_field_name, value)

    def update_transition_date(self, transition):
        """
        Update the transition date field of the model
        :param transition:
        :return:
        """
        if "date_field" not in transition:
            return
        setattr(self.model, transition["date_field"], now())

    @classmethod
    def _check_state(cls, source, state):
        """

        Check if the state of the model is the desired state

        :param state(string): desired state
        :return:
        """
        if source == cls.from_any_transition:
            return True

        return state in source if isinstance(source, list) else source == state

    def _pre_transition_check(self, transition):
        """
        Check if transition can be performed from the current state.

        :param transition(dict): transition
        :return: None
        :raises: InvalidTransition
        """

        if self._check_state(transition["source"], self._get_model_state()):
            return

        raise InvalidTransition(
            transition=transition["name"],
            current_state=self._get_model_state(),
            to_state=transition["destination"]
        )

    @classmethod
    def _get_transition_by_name(cls, name):
        """

        Return the transition dict by name

        :param name(string): name of the transition
        :return: dict, may be an empty dict if transition does not exist!
        """
        try:
            return next(trans for trans in cls.transitions if trans["name"] == name)
        except StopIteration:
            return {}

    @classmethod
    def is_transition(cls, name):
        """
        Check if an attribute is a transition
        :param name(string): name of an attribute
        :return:
        """
        return bool(cls._get_transition_by_name(name))

    def finalize_transition(self, transition):
        """
        Save the model
        :return:
        """
        self.update_transition_date(transition)
        logger.debug("Saving model.")
        self.model.save()

    def _on_enter_state(self, transition):
        """
        Get the function to call after entering the desired state

        :param transition:
        :return: The function to call or pass_function
        """
        state = transition["destination"]
        functions = self._on_enter_state_hook.get(state, [])
        _on_enter_state = getattr(self, "{}{}".format(
            ON_ENTER_STATE_PREFIX, state), None)

        if _on_enter_state:
            functions.append(_on_enter_state)

        logger.debug("Entering {} {}".format(self.state_field_name, state))
        for func in functions:
            func(transition)

    def _on_exit_state(self, transition):
        """
        Get the function to call after leaving the desired state

        :param transition:
        :return: The function to call or pass_function
        """
        state = self._get_model_state()
        functions = self._on_exit_state_hook.get(state, [])
        _on_exit_state = getattr(self, "{}{}".format(
            ON_EXIT_STATE_PREFIX, state), None)
        if _on_exit_state:
            functions.append(_on_exit_state)

        logger.debug("Leaving {} {}".format(self.state_field_name, state))
        for func in functions:
            func(transition)

    def _before_transition(self, transition, *args, **kwargs):
        """
        Get the function to call before calling the transition

        :param state:
        :return: The function to call or pass_function
        """

        before_transition = getattr(self, "{}{}".format(
            BEFORE_TRANSITION_PREFIX, transition["name"]), None)
        if not before_transition:
            return

        logger.debug("Before transition {}".format(transition["name"]))
        before_transition(*args, **kwargs)

    def _after_transition(self, transition, result):
        """
        Get the function to call after calling the transition

        :param state:
        :return: The function to call or pass_function
        """
        after_transition = getattr(self, "{}{}".format(
            AFTER_TRANSITION_PREFIX, transition["name"]), None)
        if not after_transition:
            return

        logger.debug("After transition {}".format(transition["name"]))
        after_transition(result)

    def _check_on_enter_state(self, state):
        return all([func() for func in self._on_enter_state_check.get(state, [])])

    def _check_on_exit_state(self, state):
        return all([func() for func in self._on_exit_state_check.get(state, [])])

    def check_transition_condition(self, transition, *args, **kwargs):
        """
        Call condition function.
        Call entering new state conditions
        Call exiting old state conditions

        :param transition(dict): desired transition
        :return: None
        :raises ForbiddenTransition

        """
        valid_transition = True
        check_transition_function = getattr(self, "{}{}".format(
            CHECK_TRANSITION_PREFIX, transition["name"]), None)

        if check_transition_function and not check_transition_function(*args, **kwargs):
            valid_transition = False

        if valid_transition \
                and self._check_on_enter_state(transition["destination"]) \
                and self._check_on_exit_state(self._get_model_state()):
            return

        raise ForbiddenTransition(
            transition=transition["name"],
            current_state=self._get_model_state(),
            to_state=transition["destination"]
        )

    def pre_transition(self, name, *args, **kwargs):
        transition = self._get_transition_by_name(name)

        #  Check if transition is valid
        self._pre_transition_check(transition)

        #  Check conditions if exist
        self.check_transition_condition(transition, *args, **kwargs)

        # Call before transition
        self._before_transition(transition, *args, **kwargs)

        # Call on_exit of the current state
        self._on_exit_state(transition)

    def post_transition(self, name, result, *args, **kwargs):

        transition = self._get_transition_by_name(name)
        source = self._get_model_state()
        # Change state
        self.update_model_state(transition["destination"])

        self._on_enter_state(transition)

        self._after_transition(transition, result)

        # save model
        self.finalize_transition(transition)

        # log in db
        # transition can be from a specific state or from a list of states or
        # from any state for logging we send the exact source state
        _transition = dict(transition, source=source)
        self.log_db(_transition, *args, **kwargs)

        # Create events
        self.create_events(_transition)

    @transaction.atomic
    def default_transition(self, name, *args, **kwargs):
        """

        Transition will be executed by following these steps:

            1) Check if transition is valid
            2) Check conditions if exist
            3) Call before transition
            4) Call on_exit of the current state
            5) Call the transition if implemented
            5) Change state
            6) Call on_enter of the destination state
            7) Call after transition
            8) save model

        :param name:
        :return:
        """
        self.pre_transition(name, *args, **kwargs)
        self.post_transition(name, None, *args, **kwargs)

    def run_transition(self, name, *args, **kwargs):
        """

        :param name:
        :return:
        """

        # Check transition
        if not self.is_transition(name):
            raise TransitionDoesNotExist(
                transition=name
            )

        # TODO handle the case when the name of the method is different
        trans = getattr(self, name, None)
        if trans:
            return trans(*args, **kwargs)

        return self.default_transition(name, *args, **kwargs)

    def rollback(self, current_state, target_state, exc):
        self.update_model_state(current_state)

    def get_all_transitions(self):
        pass

    def get_available_transitions(self, state=None):
        """
        Get the list of available transitions from a given state,
        If no state is given, return available transitions from current state

        :param source: str
        :return:
        """

        state = state or self._get_model_state()

        return [trans for trans in self.transitions if self._check_state(
            trans["source"], state)]

    def get_next_available_states(self, state=None):
        """
        Return the list of available next states from a given state
        If no state is given, the current state will be used
        :param state:
        :return: list
        """
        state = state or self._get_model_state()

        return [
            {
                "state": trans["destination"],
                "label": trans.get("label")
            } for trans in self.get_available_transitions(state)
        ]

    def get_transition(self, target_state):
        """
        Return the transition to call to get to the target state
        :param target_state: str
        :return: callable
        """
        state = self._get_model_state()
        potential_transition = [
            trans["name"] for trans in self.transitions if trans["destination"] == target_state and
            self._check_state(trans["source"], state)
            ]

        if potential_transition:
            return getattr(self, potential_transition[0])
        raise TransitionNotFound(current_state=state, to_state=target_state)

    def log_db(self, transition, *args, **kwargs):

        if not self.db_logging:
            return

        params = {
            "args": args,
            "kwargs": kwargs
        }

        self.db_logging_class.log(
            transition=transition["name"],
            from_state=transition["source"],
            to_state=transition["destination"],
            model=self.model,
            params=params
        )

    def create_events(self, transition):
        if not self.event_managers:
            return

        for manager in self.event_managers:
            manager.push_event(transition)

    def __getattr__(self, item):

        try:
            return object.__getattribute__(self, item)

        except AttributeError:
            if self.is_transition(item):
                return partial(self.default_transition, item)
            raise


class Transition(object):
    def __call__(self, func):
        #  TODO Check if it's a valid transition
        @transaction.atomic
        def wrapped_func(workflow, *args, **kwargs):
            workflow.pre_transition(func.__name__, *args, **kwargs)

            result = func(workflow, *args, **kwargs)

            workflow.post_transition(func.__name__, result, *args, **kwargs)

            return result

        return wrapped_func


class BaseDecorator(object):

    type = None

    def __init__(self, state):
        self.states = state if isinstance(state, list) else [state, ]
        super().__init__()

    def __call__(self, func):
        setattr(func, self.type, self.states)
        return func


class OnEnterStateCheck(BaseDecorator):
    type = "_on_enter_state_check"


class OnExitStateCheck(BaseDecorator):
    type = "_on_exit_state_check"


class OnEnterState(BaseDecorator):
    type = "_on_enter_state_hook"


class OnExitState(BaseDecorator):
    type = "_on_exit_state_hook"
