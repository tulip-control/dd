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
    n = 6
    # declare variables
    vrs = [
        f'x{i}'
        for i in range(2 * n)]
    bdd = _bdd.BDD()
    bdd.declare(*vrs)
    # equality constraints cause difficulties with BDD size
    def eq(i):
        j = (i + n + 1) % (2 * n)
        return f' x{i} <=> x{j} '
    expr_1 = r' /\ '.join(map(
        eq, range(n)))
    u = bdd.add_expr(expr_1)
    def eq(k):
        i = 2 * k
        j = 2 * k + 1
        return f' x{i} <=> x{j} '
    expr_2 = r' /\ '.join(map(
        eq, range(n)))
    v = bdd.add_expr(expr_2)
    bdd.collect_garbage()
    # an order that yields a small BDD for `expr`
    good_order = [
        f'x{i - 1}'
        for i in [
            1, 7, 3, 9, 5, 11,
            2, 8, 4, 10, 6, 12]]
    # an order that yields a large BDD for `expr`
    bad_order = list(vrs)
    # plot
    _bdd.reorder(bdd, list_to_dict(good_order))
    bdd.dump('good.pdf')
    _bdd.reorder(bdd, list_to_dict(bad_order))
    bdd.dump('bad.pdf')


def list_to_dict(c):
    return {var: level for level, var in enumerate(c)}


def prime(s):
    return f"{s}'"


if __name__ == '__main__':
    comparing_two_variable_orders()
