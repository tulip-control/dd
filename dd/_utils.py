"""Convenience functions."""
# Copyright 2017-2018 by California Institute of Technology
# All rights reserved. Licensed under 3-clause BSD.
#


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
    assert ref_count_lb <= 0, ref_count_lb
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
