# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

from toolbox.utils.python_setup import *


setup(
    name='kosc_workflow',
    version=VERSION,
    description='KOSC Workflow module',
    long_description=README,
    author='Said Ben Rjab',
    author_email='said.benrjab@kosc-telecom.fr',
    url='http://gitlab.kosc-telecom.fr/gitlab/tools/kosc_workflow.git',
    license=license,
    packages=find_packages(exclude=('tests', 'docs')),
    install_requires=requirements,
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
)
