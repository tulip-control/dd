"""How the variable order in a BDD affects the number of nodes.


Reference
=========

    Randal Bryant
    "On the complexity of VLSI implementations and graph representations
    of Boolean functions with application to integer multiplication"
    TOC, 1991
    https://doi.org/10.1109/12.73590
"""
from dd import autoref as _bdd


def comparing_two_variable_orders():
    """
    Comparing two variables.

    Args:
    """
    n = 6
    # declare variables
    vrs = ['x{i}'.format(i=i) for i in range(n)]
    primed_vars = [prime(var) for var in vrs]
    bdd = _bdd.BDD()
    bdd.declare(*(vrs + primed_vars))
    # equality constraints cause difficulties with BDD size
    expr = r' /\ '.join(
        " {var} <=> {var}' ".format(var=var) for var in vrs)
    u = bdd.add_expr(expr)
    bdd.collect_garbage()
    # an order that yields a small BDD for `expr`
    good_order = list()
    for var in vrs:
        good_order.extend([var, prime(var)])
    # an order that yields a large BDD for `expr`
    bad_order = list(vrs)
    bad_order.extend(prime(var) for var in vrs)
    # plot
    _bdd.reorder(bdd, list_to_dict(good_order))
    bdd.dump('good.pdf')
    _bdd.reorder(bdd, list_to_dict(bad_order))
    bdd.dump('bad.pdf')


def list_to_dict(c):
    """
    Convert a list of dicts to a dictionary.

    Args:
        c: (str): write your description
    """
    return {var: level for level, var in enumerate(c)}


def prime(s):
    """
    Prime s

    Args:
        s: (int): write your description
    """
    return s + "'"


if __name__ == '__main__':
    comparing_two_variable_orders()
