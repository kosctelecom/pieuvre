# -*- coding: utf-8 -*-

from .core import Workflow
from .core import Transition as transition
from .core import OnEnterStateCheck as on_enter_state_check
from .core import OnExitStateCheck as on_exit_state_check
from .exceptions import InvalidTransition, ForbiddenTransition, TransitionDoesNotExist, TransitionNotFound
from .events import WorkflowEventManager
from .mixins import WorkflowEnabled

__version__ = "0.0.12"


def set_configuration(conf):
    backend = conf.get('backend')
    if backend == 'Django':
        from django import db, utils
        core.transaction = db.transaction
        core.now = utils.timezone.now
