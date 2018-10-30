# -*- coding: utf-8 -*-

from .core import Workflow
from .exceptions import InvalidTransition, ForbiddenTransition, TransitionDoesNotExist
from .events import WorkflowEventManager
from .mixins import WorkflowEnabled


def set_configuration(conf):
    backend = conf.get('backend')
    if backend == 'Django':
        from django import db, utils
        core.transaction = db.transaction
        core.now = utils.timezone.now
