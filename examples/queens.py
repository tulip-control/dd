"""N-Queens problem using one-hot encoding.


Reference
=========

Henrik R. Andersen
    "An introduction to binary decision diagrams"
    Lecture notes for "Efficient Algorithms and Programs", 1999
    The IT University of Copenhagen
    Sec.6.1
"""
import pickle
import time
from dd import bdd as _bdd
from omega.logic.syntax import conj, disj


def solve_queens(n):
    """Return set of models for the `n`-queens problem.

    @rtype: `int`, `BDD`
    """
    v = [_var_str(i, j) for i in xrange(n) for j in xrange(n)]
    d = {xij: level for level, xij in enumerate(v)}
    bdd = _bdd.BDD(d)
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
    s = conj([present, rows, cols, slash, backslash])
    return s


def at_least_one_queen_per_row(n):
    """Return formula as `str`."""
    c = list()
    for i in xrange(n):
        xijs = [_var_str(i, j) for j in xrange(n)]
        s = disj(xijs)
        c.append(s)
    return conj(c)


def at_most_one_queen_per_line(row, n):
    """Return formula as `str`.

    @param row: if `True`, then constrain rows, else columns.
    """
    c = list()
    for i in xrange(n):
        if row:
            xijs = [_var_str(i, j) for j in xrange(n)]
        else:
            xijs = [_var_str(j, i) for j in xrange(n)]
        s = mutex(xijs)
        c.append(s)
    return conj(c)


def at_most_one_queen_per_diagonal(slash, n):
    """Return formula as `str`.

    @param slash: if `True`, then constrain anti-diagonals,
        else diagonals.
    """
    c = list()
    if slash:
        a = -n
        b = n
    else:
        a = 0
        b = 2 * n
    for k in xrange(a, b):
        if slash:
            ij = [(i, i + k) for i in xrange(n)]
        else:
            ij = [(i, k - i) for i in xrange(n)]
        ijs = [(i, j) for i, j in ij if 0 <= i < n and 0 <= j < n]
        if not ij:
            continue
        xijs = [_var_str(i, j) for i, j in ijs]
        s = mutex(xijs)
        c.append(s)
    return conj(c)


def mutex(v):
    """Return formula for at most one variable `True`.

    @param v: iterable of variables as `str`
    """
    v = set(v)
    c = list()
    for x in v:
        rest = disj(y for y in v if y != x)
        s = '{x} -> !({rest})'.format(x=x, rest=rest)
        c.append(s)
    return conj(c)


def _var_str(i, j):
    """Return variable for occupancy of cell at {row: i, column: j}."""
    return 'x{i}{j}'.format(i=i, j=j)


def benchmark(n):
    """Run for `n` queens and print statistics."""
    t0 = time.time()
    u, bdd = solve_queens(n)
    t1 = time.time()
    dt = t1 - t0
    s = (
        '------\n'
        'queens: {n}\n'
        'time: {dt} (sec)\n'
        'node: {u}\n'
        'total nodes: {k}\n'
        '------\n').format(
            n=n, dt=dt, u=u, k=len(bdd))
    print(s)
    return dt


if __name__ == '__main__':
    n_max = 9
    fname = 'dd_times.p'
    times = dict()
    for n in xrange(n_max + 1):
        t = benchmark(n)
        times[n] = t
    f = open(fname, 'w')
    pickle.dump(times, f)
