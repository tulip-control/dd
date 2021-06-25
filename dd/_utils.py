"""Convenience functions."""
# Copyright 2017-2018 by California Institute of Technology
# All rights reserved. Licensed under 3-clause BSD.
#
import textwrap as _tw


def print_var_levels(bdd):
    """Print `bdd` variables ordered by level."""
    n = len(bdd.vars)
    levels = [
        bdd.var_at_level(level)
        for level in range(n)]
    print((
        'Variable order (starting at level 0):\n'
        '{levels}').format(
            levels=levels))


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
        ref_count_lb, name, class_name):
    """Raise `RuntimeError` about reference count lower bound.

    Call this function when an unexpected nonpositive
    lower bound on a node's reference count is detected
    for a `Function` instance.

    @param ref_count_lb: lower bound on the reference count of
        the node that the `Function` instance points to.
        Assert `ref_count_lb <= 0`.
    @param name: `str` to mention as location where
        the error was detected. For example:
        ```
        'method `dd.cudd.BDD.decref`'
        ```
    @param class_name: `str` to mention as name of
        the class of the object where the value
        `ref_count_lb` was found. For example:
        ```
        '`dd.cudd.Function`'
        ```
    """
    if ref_count_lb > 0:
        raise ValueError(ref_count_lb)
    raise RuntimeError((
        'The {name} requires '
        'that `u._ref > 0` '
        '(where `u` is an instance of {cls_name}). '
        'This ensures that deallocated memory '
        'in CUDD will not be accessed. The current '
        'value of attribute `_ref` is:\n{_ref}\n'
        'For more information read the docstring of '
        'the class {cls_name}.'
        ).format(
            name=name,
            cls_name=class_name,
            _ref=ref_count_lb))
