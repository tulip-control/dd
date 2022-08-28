"""Convenience functions."""
# Copyright 2017-2018 by California Institute of Technology
# All rights reserved. Licensed under 3-clause BSD.
#
import collections.abc as _abc
import os
import textwrap as _tw
import types
import typing as _ty

try:
    import networkx as _nx
except ImportError as error:
    _nx = None
    _nx_error = error
try:
    import pydot as _pydot
except ImportError as error:
    _pydot = None
    _pydot_error = error


if _nx is not None:
    MultiDiGraph: _ty.TypeAlias = _nx.MultiDiGraph
if _pydot is not None:
    Dot: _ty.TypeAlias = _pydot.Dot


# The mapping from values of argument `op` of
# `__richcmp__()` of Cython objects,
# to the corresponding operator symbols.
# Constants are defined in `cpython.object`.
_CY_SYMBOLS: _ty.Final = {
    2: '==',
    3: '!=',
    0: '<',
    1: '<=',
    4: '>',
    5: '>='}


def import_module(
        module_name:
            str
        ) -> types.ModuleType:
    """Return module with `module_name`, if present.

    Raise `ImportError` otherwise.
    """
    modules = dict(
        networkx=_nx,
        pydot=_pydot)
    if module_name in modules:
        return modules[module_name]
    errors = dict(
        networkx=_nx_error,
        pydot=_pydot_error)
    raise errors[module_name]


def print_var_levels(
        bdd
        ) -> None:
    """Print `bdd` variables ordered by level."""
    n = len(bdd.vars)
    levels = [
        bdd.var_at_level(level)
        for level in range(n)]
    print(
        'Variable order (starting at level 0):\n'
        f'{levels}')


def var_counts(
        bdd
        ) -> str:
    """Return levels and numbers of variables, CUDD indices.

    @type bdd:
        `dd.cudd.BDD` or
        `dd.cudd_zdd.ZDD`
    """
    n_declared_vars = len(bdd.vars)
    n_cudd_vars = bdd._number_of_cudd_vars()
    return _tw.dedent(f'''
        There are:
        {n_cudd_vars} variable indices in CUDD,
        {n_declared_vars} declared variables in {bdd!r}.

        So the set of levels of the declared variables
        is not a contiguous range of integers.

        This can occur when specific levels have been
        given to `{type(bdd)}.add_var()`.

        The declared variables and their levels are:
        {bdd.var_levels}
        ''')


def contiguous_levels(
        callable:
            str,
        bdd
        ) -> str:
    """Return requirement about contiguous levels.

    @type bdd:
        `dd.cudd.BDD` or
        `dd.cudd_zdd.ZDD`
    """
    return _tw.dedent(f'''
        The callable `{callable}()` requires that
        the number of variable indices in CUDD, and
        the number of declared variables in {bdd!r}
        be equal.
        ''')


def _raise_runtimerror_about_ref_count(
        ref_count_lb:
            int,
        name:
            str,
        class_name:
            str
        ) -> _ty.NoReturn:
    """Raise `RuntimeError` about reference count lower bound.

    Call this function when an unexpected nonpositive
    lower bound on a node's reference count is detected
    for a `Function` instance.

    @param ref_count_lb:
        lower bound on the reference count of
        the node that the `Function` instance points to.
        ```tla
        ASSUME
            ref_count_lb <= 0
        ```
    @param name:
        to mention as location where
        the error was detected. For example:
        ```python
        'method `dd.cudd.BDD.decref`'
        ```
    @param class_name:
        to mention as name of
        the class of the object where the value
        `ref_count_lb` was found. For example:
        ```python
        '`dd.cudd.Function`'
        ```
    """
    if ref_count_lb > 0:
        raise ValueError(ref_count_lb)
    raise RuntimeError(
        f'The {name} requires '
        'that `u._ref > 0` '
        f'(where `u` is an instance of {class_name}). '
        'This ensures that deallocated memory '
        'in CUDD will not be accessed. The current '
        f'value of attribute `_ref` is:\n{ref_count_lb}\n'
        'For more information read the docstring of '
        f'the class {class_name}.')



@_ty.overload
def _map_container(
        mapper:
            _abc.Callable,
        container:
            _abc.Mapping
        ) -> dict:
    ...


@_ty.overload
def _map_container(
        mapper:
            _abc.Callable,
        container:
            _abc.Iterable
        ) -> list:
    ...


def _map_container(
        mapper,
        container):
    """Map `container`, using `mapper()`.

    If `container` is a sequence,
    then map each item.

    If `container` is a mapping of
    keys to values, then map each value.
    """
    if isinstance(container, _abc.Mapping):
        return _map_values(mapper, container)
    return list(map(mapper, container))


def _map_values(
        mapper:
            _abc.Callable,
        kv:
            _abc.Mapping
        ) -> dict:
    """Map each value of `kv` using `mapper()`.

    The keys of `kv` remain unchanged.
    """
    return {k: mapper(v) for k, v in kv.items()}


def _values_of(
        container:
            _abc.Mapping |
            _abc.Collection
        ) -> _abc.Iterable:
    """Return container values.

    @return:
        - `container.values()` if
          `container` is a mapping
        - `container` otherwise
    """
    if isinstance(container, _abc.Mapping):
        return container.values()
    return container


def total_memory(
        ) -> (
            int |
            None):
    """Return number of bytes of memory.

    Requires that:
    - `SC_PAGE_SIZE` and
    - `SC_PHYS_PAGES`
    be readable via `os.sysconf()`.
    """
    names = os.sysconf_names
    has_both = (
        'SC_PAGE_SIZE' in names and
        'SC_PHYS_PAGES' in names)
    if not has_both:
        print(
            'skipping check that '
            'initial memory estimate fits '
            'in available memory of system, '
            "because either `'SC_PAGE_SIZE'` or "
            "`'SC_PHYS_PAGES'` undefined in "
            '`os.sysconf_names`.')
        return None
    page_size = os.sysconf('SC_PAGE_SIZE')
    n_pages = os.sysconf('SC_PHYS_PAGES')
    both_defined = (
        page_size >= 0 and
        n_pages >= 0)
    if not both_defined:
        return None
    return page_size * n_pages
