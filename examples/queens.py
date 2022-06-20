"""N-Queens problem using one-hot encoding.


Reference
=========

[1] Henrik R. Andersen
    "An introduction to binary decision diagrams"
    Lecture notes for "Efficient Algorithms and Programs", 1999
    The IT University of Copenhagen
    Section 6.1
"""
import collections.abc as _abc
import pickle
import time

import dd.bdd as _bdd


def solve_queens(n):
    """Return set of models for the `n`-queens problem.

    @rtype:
        `int`, `BDD`
    """
    vrs = [_var_str(i, j) for i in range(n) for j in range(n)]
    bdd = _bdd.BDD()
    bdd.declare(*vrs)
    s = queens_formula(n)
    u = bdd.add_expr(s)
    return u, bdd


def queens_formula(n):
    """Return a non-trivial propositional formula for the problem."""
    # i = row index
    # j = column index
    present = at_least_one_queen_per_row(n)
    rows = at_most_one_queen_per_line(True, n)
    cols = at_most_one_queen_per_line(False, n)
    slash = at_most_one_queen_per_diagonal(True, n)
    backslash = at_most_one_queen_per_diagonal(False, n)
    s = _conjoin([present, rows, cols, slash, backslash])
    return s


def at_least_one_queen_per_row(n):
    """Return formula as `str`."""
    c = list()
    for i in range(n):
        xijs = [_var_str(i, j) for j in range(n)]
        s = _disjoin(xijs)
        c.append(s)
    return _conjoin(c)


def at_most_one_queen_per_line(row, n):
    """Return formula as `str`.

    @param row:
        if `True`, then constrain rows, else columns.
    """
    c = list()
    for i in range(n):
        if row:
            xijs = [_var_str(i, j) for j in range(n)]
        else:
            xijs = [_var_str(j, i) for j in range(n)]
        s = mutex(xijs)
        c.append(s)
    return _conjoin(c)


def at_most_one_queen_per_diagonal(slash, n):
    """Return formula as `str`.

    @param slash:
        if `True`, then constrain anti-diagonals,
        else diagonals.
    """
    c = list()
    if slash:
        a = -n
        b = n
    else:
        a = 0
        b = 2 * n
    for k in range(a, b):
        if slash:
            ij = [(i, i + k) for i in range(n)]
        else:
            ij = [(i, k - i) for i in range(n)]
        ijs = [(i, j) for i, j in ij if 0 <= i < n and 0 <= j < n]
        if not ij:
            continue
        xijs = [_var_str(i, j) for i, j in ijs]
        s = mutex(xijs)
        c.append(s)
    return _conjoin(c)


def mutex(v):
    """Return formula for at most one variable `True`.

    @param v:
        iterable of variables as `str`
    """
    v = set(v)
    c = list()
    for x in v:
        rest = _disjoin(y for y in v if y != x)
        s = f'{x} => ~ ({rest})'
        c.append(s)
    return _conjoin(c)


def _var_str(i, j):
    """Return variable for occupancy of cell at {row: i, column: j}."""
    return f'x{i}{j}'


def _conjoin(
        strings:
            _abc.Iterable
        ) -> str:
    """Return conjunction of `strings`."""
    expr = _apply_infix(
        strings,
        operator=r' /\ ')
    if not expr:
        expr = 'FALSE'
    return expr


def _disjoin(
        strings:
            _abc.Iterable
        ) -> str:
    """Return disjunction of `strings`."""
    expr = _apply_infix(
        strings,
        operator=r' \/ ')
    if not expr:
        expr = 'TRUE'
    return expr


def _apply_infix(
        strings:
            _abc.Iterable,
        operator:
            str
        ) -> str:
    """Apply infix `operator` to `strings`."""
    nonempty = filter(None, strings)
    parenthesized = map(_parenthesize, nonempty)
    return operator.join(parenthesized)


def _parenthesize(string) -> str:
    """Return `string` within parentheses."""
    return f'({string})'


def benchmark(n):
    """Run for `n` queens and print statistics."""
    t0 = time.perf_counter()
    u, bdd = solve_queens(n)
    t1 = time.perf_counter()
    dt = t1 - t0
    s = (
        '------\n'
        f'queens: {n}\n'
        f'time: {dt} (sec)\n'
        f'node: {u}\n'
        f'total nodes: {len(bdd)}\n'
        '------\n')
    print(s)
    return dt


def _example():
    n_max = 9
    fname = 'dd_times.p'
    times = dict()
    for n in range(n_max + 1):
        t = benchmark(n)
        times[n] = t
    with open(fname, 'wb') as f:
        pickle.dump(times, f)


if __name__ == '__main__':
    _example()
