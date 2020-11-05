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
    Compute the two - wise variable equality.

    Args:
    """
    n = 6
    # declare variables
    vrs = ['x{i}'.format(i=i) for i in range(2 * n)]
    bdd = _bdd.BDD()
    bdd.declare(*vrs)
    # equality constraints cause difficulties with BDD size
    expr_1 = r' /\ '.join(
        " x{i} <=> x{j} ".format(i=i, j=(i + n + 1) % (2*n)) for i in range(n))
    u = bdd.add_expr(expr_1)
    expr_2 = r' /\ '.join(
        " x{i} <=> x{j} ".format(i=2 * i, j=(2 * i + 1)) for i in range(n))
    v = bdd.add_expr(expr_2)
    bdd.collect_garbage()
    # an order that yields a small BDD for `expr`
    good_order = ['x{i}'.format(i=i - 1) for i in
        [1, 7, 3, 9, 5, 11,
        2, 8, 4, 10, 6, 12]]
    # an order that yields a large BDD for `expr`
    bad_order = list(vrs)
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
