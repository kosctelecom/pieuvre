# -*- coding: utf-8 -*-

from .core import Workflow
from .core import Transition as transition
from .exceptions import InvalidTransition, ForbiddenTransition, TransitionDoesNotExist, TransitionNotFound
from .events import WorkflowEventManager
from .mixins import WorkflowEnabled

__version__ = "0.0.8"


def set_configuration(conf):
    backend = conf.get('backend')
    if backend == 'Django':
        from django import db, utils
        core.transaction = db.transaction
        core.now = utils.timezone.now
