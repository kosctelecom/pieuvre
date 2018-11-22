# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
from kosc_workflow import __version__


with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()


setup(
    name='KOSC Workflow',
    version=__version__,
    description='KOSC Workflow module',
    long_description=readme,
    author='Said Ben Rjab',
    author_email='said.benrjab@kosc-telecom.fr',
    url='https://gitlab.kosc-telecom.fr/gitlab/said.benrjab/kosc_workflow',
    license=license,
    packages=find_packages(exclude=('tests', 'docs')),
    install_requires=[
        "wheel",
    ]
)
