"""Compare the signatures of methods in a Cython `cdef` class to ABC.

A `cdef` class cannot inherit from an ABC (or a Python class that serves
the same purpose). `inspect.signature` works when the compiler directive
`binding` is enabled, but returns keyword arguments as if they are positional.

This script reports any mismatch of argument names (ignoring which ones
are keyword arguments) between methods of the classes:

- `dd._abc.BDD` (the specification)
- `dd.cudd.BDD` (the implementation)

Methods present in `_abc.BDD` but absent from `cudd.BDD` are reported too.
Use the script to ensure the API is implemented, also for other Cython
modules, for example `dd.sylvan`.

MEMO: Remember to enable `binding` when using this script.
"""
# Copyright 2017 by California Institute of Technology
# All rights reserved. Licensed under BSD-3.
#
import inspect
import logging
import warnings

from dd import _abc
from dd import cudd


log = logging.getLogger(__name__)


def inspect_signatures(spec, imp):
    """Print mismatches of method names or argument names.

    @param spec: the specification
    @param imp: the implementation
    """
    print('Specification class: {t}'.format(t=type(spec)))
    print('Implementation class: {t}'.format(t=type(imp)))
    print('Checking whether all spec methods are implemented:\n')
    spec_dir = dir(spec)
    imp_dir = dir(imp)
    for method_name in spec_dir:
        if is_hidden(method_name):
            continue
        method = getattr(spec, method_name)
        if not callable(method):
            continue
        log.info('"{name}" is callable'.format(name=method_name))
        if method_name not in imp_dir:
            print('MISSING implementation for "{name}"\n'.format(
                name=method_name))
            continue
        assert method_name in spec_dir, method_name
        assert method_name in imp_dir, method_name
        spec_method = getattr(spec, method_name)
        imp_method = getattr(imp, method_name)
        spec_sig = get_signature(spec_method)
        imp_sig = get_signature(imp_method)
        if spec_sig is None or imp_sig is None:
            continue
        spec_args = spec_sig.parameters.keys()
        imp_args = imp_sig.parameters.keys()
        if spec_args != imp_args:
            print((
                'MISMATCH: method "{name}"\n'
                '    spec args: {spec_args}\n'
                '    imp args: {imp_args}\n').format(
                    name=method_name,
                    spec_args=spec_args,
                    imp_args=imp_args))
    print('\nExtra methods:\n')
    for method_name in imp_dir:
        if is_hidden(method_name):
            continue
        method = getattr(imp, method_name)
        if not callable(method):
            continue
        if method_name not in spec_dir:
            print(method_name)


def is_hidden(method_name):
    """Return `True` if not an interface method."""
    return method_name.startswith('_')


def get_signature(func):
    """Wrapper of `inspect.signature` with Cython reminder."""
    try:
        sig = inspect.signature(func)
    except ValueError:
        warnings.warn(
            'Compile `cudd` with the compiler directive `binding`')
        sig = None
    return sig


if __name__ == '__main__':
    # BDD manager
    a = _abc.BDD()
    b = cudd.BDD()
    inspect_signatures(a, b)
    # BDD nodes
    print(30 * '-' + '\n')
    u = _abc.Operator
    # cannot instantiate `cudd.Function`
    # w/o a `DdNode` pointer
    b.declare('x')
    v = b.add_expr('x')
    inspect_signatures(u, v)
