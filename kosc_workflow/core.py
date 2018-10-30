# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import logging

from functools import partial

from .utils import transaction, now
from .exceptions import InvalidTransition, ForbiddenTransition, TransitionDoesNotExist

logger = logging.getLogger(__name__)

ON_ENTER_STATE_PREFIX = "on_enter_"
ON_EXIT_STATE_PREFIX = "on_exit_"
AFTER_TRANSITION_PREFIX = "after_"
BEFORE_TRANSITION_PREFIX = "before_"
CHECK_TRANSITION_PREFIX = "check_"
TRANSITION_IMPLEMENTATION_PREFIX = "__"


def make_transition_implementation_private(dct):

    for transition in dct["transitions"]:
        transition_name = transition["name"]
        if transition_name not in dct:
            continue

        dct["{}{}".format(TRANSITION_IMPLEMENTATION_PREFIX, transition_name)] = dct.pop(transition_name)

    return dct


class WorkflowMetaclass(type):

    def __new__(cls, name, bases, dct):
        dct = make_transition_implementation_private(dct)
        return type.__new__(cls, name, bases, dct)


class Workflow(metaclass=WorkflowMetaclass):
    """
    Workflow class

    Attributes:
        initial_state(string): initial state of the model
        states(list): The list of states, it can be a list of strings or dicts or a mix of them
            Example:
                states = ["draft", "submitted", "completed", "rejected"]

        transitions(list): List of transitions:
            Example:
                transitions = [
                    {"name": "submit", "source": "draft", "destination": "submitted", "date_field": "submission_date"},
                    {"name": "complete", "source": "submitted", "destination": "completed"}
                ]
    """

    from_any_transition = "*"
    state_field_name = "state"
    states = None
    transitions = []
    db_logging = False
    db_logging_class = None

    event_manager_classes = ()

    def __init__(self, model):

        self.model = model

        super(Workflow, self).__init__()

        self.event_managers = [klass(model) for klass in self.event_manager_classes]

    def _get_model_state(self):
        """
        Get the state of model using the state name defined in the class
        :return: the value of model state
        """

        return getattr(self.model, self.state_field_name)

    def update_model_state(self, value):
        """
        Update the state of the model
        :param value(string): the value of the state to be updated
        :return: None
        """
        logger.debug("Updating model {} to {}".format(self.state_field_name, value))

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

    def _check_state(self, state):
        """

        Check if the state of the model is the desired state

        :param state(string): desired state
        :return:
        """
        if state == self.from_any_transition:
            return True

        current_state = self._get_model_state()

        return current_state in state if isinstance(state, list) else current_state == state

    def _pre_transition_check(self, transition):
        """
        Check if transition can be performed from the current state.

        :param transition(dict): transition
        :return: None
        :raises: InvalidTransition
        """

        if self._check_state(transition["source"]):
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
    def _is_transition(cls, name):
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

    def _on_enter_state(self, state):
        """
        Get the function to call after entering the desired state

        :param state:
        :return: The function to call or pass_function
        """
        on_enter_state = getattr(self, "{}{}".format(ON_ENTER_STATE_PREFIX, state), None)

        if not on_enter_state:
            return

        logger.debug("Entering {} {}".format(self.state_field_name, state))
        on_enter_state()

    def _on_exit_state(self, state):
        """
        Get the function to call after leaving the desired state

        :param state:
        :return: The function to call or pass_function
        """
        on_exit_state = getattr(self, "{}{}".format(ON_EXIT_STATE_PREFIX, state), None)
        if not on_exit_state:
            return

        logger.debug("Leaving {} {}".format(self.state_field_name, state))
        on_exit_state()

    def _before_transition(self, transition, *args, **kwargs):
        """
        Get the function to call before calling the transition

        :param state:
        :return: The function to call or pass_function
        """

        before_transition = getattr(self, "{}{}".format(BEFORE_TRANSITION_PREFIX, transition["name"]), None)
        if not before_transition:
            return

        logger.debug("Before transition {}".format(transition["name"]))
        before_transition(*args, **kwargs)

    def _after_transition(self, transition, *args):
        """
        Get the function to call after calling the transition

        :param state:
        :return: The function to call or pass_function
        """
        after_transition = getattr(self, "{}{}".format(AFTER_TRANSITION_PREFIX, transition["name"]), None)
        if not after_transition:
            return

        logger.debug("After transition {}".format(transition["name"]))
        after_transition(*args)

    def _transition_implementation(self, transition, *args, **kwargs):
        """
        Get the implementation of the transition

        :param state:
        :return: The function to call or pass_function
        """

        try:
            transition_implementation = getattr(
                self,
                "{}{}".format(TRANSITION_IMPLEMENTATION_PREFIX, transition["name"])
            )

            is_implemented = True

        except AttributeError as e:
            is_implemented = False
            result = None

        else:
            logger.debug("Running transition {}".format(transition["name"]))
            result = transition_implementation(*args, **kwargs)

        return is_implemented, result

    def check_transition_condition(self, transition, *args, **kwargs):
        """
        Call condition function.

        :param transition(dict): desired transition
        :return: None
        :raises ForbiddenTransition

        """
        check_function = getattr(self, "{}{}".format(CHECK_TRANSITION_PREFIX, transition["name"]), None)
        if not check_function:
            return

        if check_function(*args, **kwargs):
            return

        raise ForbiddenTransition(
            transition=transition["name"],
            current_state=self._get_model_state(),
            to_state=transition["destination"]
        )

    @transaction.atomic
    def _execute_transition(self, name, *args, **kwargs):
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
        #  TODO handle rollback

        transition = self._get_transition_by_name(name)

        #  Check if transition is valid
        self._pre_transition_check(transition)

        #  Check conditions if exist
        self.check_transition_condition(transition, *args, **kwargs)

        # Call before transition
        self._before_transition(transition, *args, **kwargs)

        # Call on_exit of the current state
        self._on_exit_state(self._get_model_state())

        # Call the transition if implemented
        is_implemented, result = self._transition_implementation(transition, *args, **kwargs)

        # Change state
        self.update_model_state(transition["destination"])

        # Call on_enter of the destination state
        self._on_enter_state(transition["destination"])

        # Call after transition
        params = []
        if is_implemented:
            params = [result, ]

        self._after_transition(transition, *params)

        # save model
        self.finalize_transition(transition)

        # log in db
        self.log_db(transition, *args, **kwargs)

        # Create events
        self.create_events(transition)

    def run_transition(self, name):
        """

        :param name:
        :return:
        """

        # Check transition
        if not self._is_transition(name):
            raise TransitionDoesNotExist(
                transition=name
            )

        return self._execute_transition(name)

    def rollback(self, current_state, target_state, exc):
        self.update_model_state(current_state)

    def get_available_transitions(self):
        pass

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
            return super().__getattribute__(item)

        except AttributeError as e:
            if self._is_transition(item):
                return partial(self._execute_transition, item)
            raise