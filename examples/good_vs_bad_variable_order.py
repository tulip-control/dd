"""How the variable order in a BDD affects the number of nodes.


Reference
=========

[1] Randal Bryant
    "On the complexity of VLSI implementations and graph representations
    of Boolean functions with application to integer multiplication"
    TOC, 1991
    <https://doi.org/10.1109/12.73590>
"""
from dd import autoref as _bdd


def comparing_two_variable_orders():
    n = 6
    # declare variables
    vrs = [f'x{i}' for i in range(n)]
    primed_vars = [prime(var) for var in vrs]
    bdd = _bdd.BDD()
    bdd.declare(*(vrs + primed_vars))
    # equality constraints cause difficulties with BDD size
    expr = r' /\ '.join(
        f" {var} <=> {var}' " for var in vrs)
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
    return {var: level for level, var in enumerate(c)}


def prime(s):
    return s + "'"


if __name__ == '__main__':
    comparing_two_variable_orders()
