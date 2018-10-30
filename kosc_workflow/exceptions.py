# -*- coding: utf-8 -*-

from __future__ import unicode_literals


class WorkflowBaseError(Exception):
    """
    Base exception for workflow error
    """
    message = "Error {transition}: {current_state} -> {to_state}"

    def __init__(self, transition, current_state=None, to_state=None):

        self.transition = transition
        self.current_state = current_state
        self.to_state = to_state

    def __str__(self):

        return self.message.format(
            transition=self.transition,
            current_state=self.current_state,
            to_state=self.to_state
        )


class InvalidTransition(WorkflowBaseError):
    """
    Raise when trying to perform a transition from an invalid state
    """
    message = "Invalid transition {transition}: {current_state} -> {to_state}"


class ForbiddenTransition(WorkflowBaseError):
    """
    Raise when condition is not valid to perform the transition
    """
    message = "Transition forbidden {transition}: {current_state} -> {to_state}"


class TransitionDoesNotExist(WorkflowBaseError):
    """
    Raise when condition is not valid to perform the transition
    """
    message = "Transition {transition} does not exist"
