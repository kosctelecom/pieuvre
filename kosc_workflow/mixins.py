# -*- coding: utf-8 -*-

from __future__ import unicode_literals


class WorkflowEnabled(object):

    workflow_class = None

    def __init__(self, *args, **kwargs):
        self._workflow = None
        super(WorkflowEnabled, self).__init__(*args, **kwargs)

    def get_workflow_class(self):
        return self.workflow_class

    @property
    def workflow(self):
        if self._workflow:
            return self._workflow
        workflow_class = self.get_workflow_class()
        self.workflow = workflow_class(model=self)
        return self._workflow

    @workflow.setter
    def workflow(self, value):
        self._workflow = value
