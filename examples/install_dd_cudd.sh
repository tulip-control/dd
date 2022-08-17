#!/usr/bin/env bash
#
# Install `dd`, including the modules
# `dd.cudd` and `dd.cudd_zdd`
# (which are written in Cython).
#
# To run this script, enter in
# a command-line environment:
#
# ./install_dd_cudd.sh
#
# This script is unnecessary if you
# want a pure-Python installation of `dd`.
# If so, then `pip install dd`.
#
# This is script is unnecessary also
# if a wheel file for your operating system
# and CPython version is available on PyPI.
# Wheel files (`*.whl`) can be found at:
#     https://pypi.org/project/dd/#files
#
# If there *is* a wheel file on PyPI
# that matches your operating system and
# CPython version, then `pip install dd`
# suffices.


set -v
set -e
pip install dd
    # to first install
    # dependencies of `dd`
pip uninstall -y dd
pip download \
    --no-deps dd \
    --no-binary dd
tar -xzf dd-*.tar.gz
pushd dd-*/
python setup.py install --fetch --cudd --cudd_zdd
# confirm that `dd.cudd` did get installed
pushd tests/
python -c 'import dd.cudd'
popd
popd
