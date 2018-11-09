# -*- coding: utf-8 -*-
import uuid

from unittest import TestCase

from kosc_workflow import Workflow, InvalidTransition, TransitionDoesNotExist, ForbiddenTransition, transition


class MyOrder(object):
    """
    Use this object to mock a django model.

    After changing the value of the state, is_saved is equal a True if save method is called.
    This allow us to check if the save is called or not !

    """

    def __init__(self, state="draft"):
        self.uuid = uuid.uuid4()
        self.is_saved = True
        self._state = state
        self.allow_submit = True

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self.is_saved = False
        self._state = value

    def save(self):
        self.is_saved = True


class LoggingModel(object):

    logs = {}

    @classmethod
    def log(cls, **kwargs):
        cls.logs = kwargs


class MyWorkflow(Workflow):

    event_manager_classes = ()
    db_logging = True
    db_logging_class = LoggingModel

    states = ["draft", "submitted", "completed", "rejected"]

    transitions = [
        {"name": "submit", "source": "draft", "destination": "submitted"},
        {"name": "complete", "source": "submitted", "destination": "completed"},
        {"name": "reject", "source": "*", "destination": "rejected"},
    ]

    def before_submit(self):
        # To test later if this implementation is called
        setattr(self.model, "before_submit_called", True)

    @transition()
    def submit(self):

        # To test later if this implementation is called
        setattr(self.model, "submit_called", True)

    def after_submit(self, res):
        # To test later if this implementation is called
        setattr(self.model, "after_submit_called", True)

    def on_enter_submitted(self):
        # To test later if this implementation is called
        setattr(self.model, "on_enter_submitted_called", True)

    def on_exit_draft(self):
        # To test later if this implementation is called
        setattr(self.model, "on_exit_draft_called", True)

    def check_submit(self):
        if getattr(self.model, "allow_submit", None):  # If model has an allow_submit attribute, it's valid else not!
            return True

        return False


class TestWorkflow(TestCase):

    def setUp(self):
        self.model = MyOrder()
        self.workflow = MyWorkflow(model=self.model)

    def test_get_model_state(self):
        self.assertEqual(self.workflow._get_model_state(), "draft")

    def test_update_model_state(self):
        self.workflow.update_model_state("new_state")

        self.assertEqual(self.model.state, "new_state")

    def test_check_state(self):
        self.assertTrue(self.workflow._check_state("draft", "draft"))
        self.assertTrue(self.workflow._check_state("*", "draft"))
        self.assertTrue(self.workflow._check_state(["draft", "completed"], "draft"))
        self.assertFalse(self.workflow._check_state("completed", "draft"))
        self.assertFalse(self.workflow._check_state(["completed", "rejected"], "draft"))

    def test_pre_transition_check(self):
        valid_transition = {"name": "submit", "source": "draft", "destination": "submitted"}
        invalid_transition = {"name": "complete", "source": "submitted", "destination": "completed"}

        self.assertIsNone(self.workflow._pre_transition_check(valid_transition))

        with self.assertRaises(InvalidTransition) as e:
            self.workflow._pre_transition_check(invalid_transition)
        e = e.exception
        self.assertEqual(e.transition, invalid_transition["name"])
        self.assertEqual(e.current_state, "draft")
        self.assertEqual(e.to_state, invalid_transition["destination"])

    def test_get_transition_by_name(self):
        self.assertEqual(
            self.workflow._get_transition_by_name("submit"),
            {"name": "submit", "source": "draft", "destination": "submitted"}
        )

        self.assertEqual(
            self.workflow._get_transition_by_name("invalid_transition"),
            {}
        )

    def test_is_transition(self):
        self.assertTrue(
            self.workflow.is_transition("submit")
        )

        self.assertFalse(
            self.workflow.is_transition("invalid_transition")
        )

    def test_finalize_transition(self):
        self.model.is_saved = False
        self.workflow.finalize_transition({"name": "submit", "source": "draft", "destination": "submitted"})

        self.assertTrue(self.model.is_saved)

    def test_on_enter_state(self):
        self.assertIsNone(
            self.workflow._on_enter_state("rejected")
        )

        self.workflow._on_enter_state("submitted")
        self.assertTrue(self.model.on_enter_submitted_called)

    def test_on_exit_state(self):
        self.assertIsNone(
            self.workflow._on_exit_state("rejected")
        )

        self.workflow._on_exit_state("draft")
        self.assertTrue(self.model.on_exit_draft_called)

    def test_before_transition(self):
        self.assertIsNone(
            self.workflow._before_transition({"name": "reject", "source": "*", "destination": "rejected"})
        )

        self.workflow._before_transition({"name": "submit", "source": "draft", "destination": "submitted"})
        self.assertTrue(self.model.before_submit_called)

    def test_after_transition(self):
        self.assertIsNone(
            self.workflow._after_transition({"name": "reject", "source": "*", "destination": "rejected"}, None)
        )

        self.workflow._after_transition({"name": "submit", "source": "draft", "destination": "submitted"}, None)
        self.assertTrue(self.model.after_submit_called)

    def test_check_transition(self):
        transition_with_check = {"name": "submit", "source": "draft", "destination": "submitted"}
        transition_without_check = {"name": "complete", "source": "submitted", "destination": "completed"}

        self.assertIsNone(self.workflow.check_transition_condition(transition_without_check))

        # check is valid
        self.assertIsNone(self.workflow.check_transition_condition(transition_with_check))

        self.model.allow_submit = False
        with self.assertRaises(ForbiddenTransition) as e:
            self.workflow.check_transition_condition(transition_with_check)
        e = e.exception
        self.assertEqual(e.transition, transition_with_check["name"])
        self.assertEqual(e.current_state, "draft")
        self.assertEqual(e.to_state, transition_with_check["destination"])

    def test_execute_transition(self):
        self.model.is_saved = False

        self.workflow.submit()
        self.assertTrue(self.model.on_exit_draft_called)
        self.assertTrue(self.model.before_submit_called)
        self.assertTrue(self.model.submit_called)
        self.assertTrue(self.model.on_enter_submitted_called)
        self.assertTrue(self.model.after_submit_called)

        self.assertEqual(self.model.state, "submitted")
        self.assertTrue(self.model.is_saved)

    def test_run_transition(self):
        with self.assertRaises(TransitionDoesNotExist) as e:
            self.workflow.run_transition("does_not_exist")
        e = e.exception
        self.assertEqual(e.transition, "does_not_exist")

        self.workflow.run_transition("reject")
        self.assertEqual(self.model.state, "rejected")

    def test_log_db(self):

        pass
