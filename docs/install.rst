
Installation
============

Manual set-up
~~~~~~~~~~~~~

::

    python setup.py install

Via Pypi
~~~~~~~~

As of November 2018, the Pypi server is: ::

    export DEVPY_SERVER=192.168.13.10

`kosc-workflow` can then be installed with: ::

    pip install kosc_workflow -i http://${DEVPY_SERVER}/devpi/packages/stable/+simple/ --trusted-host ${DEVPY_SERVER}
