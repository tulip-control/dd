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
