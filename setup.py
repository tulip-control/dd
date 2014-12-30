# -*- coding: utf-8 -*-
from setuptools import setup
import warnings


README = 'README.md'
try:
    long_description = open(README).read()
except:
    warnings.warn('Could not find {readme}'.format(readme=README))


setup(
    name='dd',
    version='0.0.2',
    license='BSD',
    description='Library of decision diagrams and algorithms on them.',
    long_description=long_description,
    author='Ioannis Filippidis',
    author_email='jfilippidis@gmail.com',
    url='https://github.com/johnyf/dd',
    install_requires=['networkx'],
    keywords=['bdd', 'decision diagram', 'networkx', 'boolean'])
