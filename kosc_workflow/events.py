# -*- coding: utf-8 -*-

from __future__ import unicode_literals


def get_empty_dict():
    return {}


class WorkflowEventManager(object):
    """
    Generate events in transitions

    supported_transitions = {
        "submit": {
                    "event_type": "order-submitted",
                    "data": get_submitted_data,
                  }
    }

    """
    supported_transitions = {

    }

    def __init__(self, model):
        self.model = model

    def push_event(self, transition):
        transition_name = transition["name"]

        if transition_name not in self.supported_transitions:
            return

        event = self.get_event(transition_name)

        # Push event
        self._push_event(event)

    def get_event(self, transition_name):
        return {
            "type": self.supported_transitions[transition_name]["event_type"],
            "data": self.supported_transitions.get(transition_name, get_empty_dict)()
        }

    def _push_event(self, event):
        pass
