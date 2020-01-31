"""
mixins.py
=================================================
Various helper mixins.
"""


class WorkflowEnabled:
    """
    This mixin provides a ``workflow`` attribute on model instances.

    This mixin is just a helper providing shortcuts to the most common scenario
    in which models have one workflow. However this logic can be extended
    to any number of workflows for a given model, using the same concept.

    Attributes:
        workflow_class: class extending ``Workflow`` describing the model
            workflow.
    """

    workflow_class = None

    def __init__(self, *args, **kwargs):
        self._workflow = None
        super().__init__(*args, **kwargs)

    def get_workflow_class(self):
        """
        Return the workflow class to be instanciated, by default
        ``self.workflow_class``.
        Override if you need a custom logic.
        """
        return self.workflow_class

    @property
    def workflow(self):
        """
        Return a cached instance of the workflow.
        """
        if self._workflow:
            return self._workflow
        workflow_class = self.get_workflow_class()
        self.workflow = workflow_class(model=self)
        return self._workflow

    @workflow.setter
    def workflow(self, value):
        self._workflow = value
