import logging
from dd import cudd
from nose.tools import assert_raises

from common import Tests
from common_bdd import Tests as BDDTests
from common_cudd import Tests as CuddTests


logging.getLogger('astutils').setLevel('ERROR')


Tests.DD = cudd.BDD
BDDTests.DD = cudd.BDD
CuddTests.DD = cudd.BDD


def test_insert_var():
    bdd = cudd.BDD()
    level = 0
    j = bdd.insert_var('x', level)
    assert j == 0, j  # initially indices = levels
    x = bdd.var_at_level(level)
    assert x == 'x', x
    level = 101
    bdd.insert_var('y', level)
    y = bdd.var_at_level(level)
    assert y == 'y', y


def test_refs():
    cudd._test_incref()
    cudd._test_decref()


def test_len():
    bdd = cudd.BDD()
    assert len(bdd) == 0, len(bdd)
    u = bdd.true
    assert len(bdd) == 1, len(bdd)
    del u
    assert len(bdd) == 0, len(bdd)
    u = bdd.true
    v = bdd.false
    assert len(bdd) == 1, len(bdd)
    bdd.add_var('x')
    x = bdd.var('x')
    assert len(bdd) == 2, len(bdd)
    not_x = ~x
    # len(bdd) is the number of referenced nodes
    # a node is used both for the positive and
    # negative literals of its variable
    assert len(bdd) == 2, len(bdd)
    del x
    assert len(bdd) == 2, len(bdd)
    del not_x
    assert len(bdd) == 1, len(bdd)
    del u, v
    assert len(bdd) == 0, len(bdd)


def test_cube_array():
    cudd._test_dict_to_cube_array()
    cudd._test_cube_array_to_dict()


def test_dump_load():
    bdd = cudd.BDD()
    for var in ['x', 'y', 'z', 'w']:
        bdd.add_var(var)
    u = bdd.add_expr('(x /\ ~ w) \/ z')
    fname = 'bdd.txt'
    bdd.dump(fname, [u], filetype='dddmp')
    u_ = bdd.load(fname)
    assert u == u_


def test_load_sample0():
    bdd = cudd.BDD()
    names = ['a', 'b', 'c']
    for var in names:
        bdd.add_var(var)
    fname = 'sample0.txt'
    u = bdd.load(fname)
    n = len(u)
    assert n == 5, n
    s = '~ ( (a /\ (b \/ c)) \/ (~ a /\ (b \/ ~ c)) )'
    u_ = bdd.add_expr(s)
    assert u == u_, (u, u_)


def test_and_exists():
    bdd = cudd.BDD()
    for var in ['x', 'y']:
        bdd.add_var(var)
    # (\E x:  x /\ y) \equiv y
    x = bdd.add_expr('x')
    y = bdd.add_expr('y')
    qvars = ['x']
    r = cudd.and_exists(x, y, qvars)
    assert r == y, (r, y)
    # (\E x:  x /\ ~ x) \equiv FALSE
    not_x = bdd.apply('not', x)
    r = cudd.and_exists(x, not_x, qvars)
    assert r == bdd.false


def test_or_forall():
    bdd = cudd.BDD()
    for var in ['x', 'y']:
        bdd.add_var(var)
    # (\A x, y:  x \/ ~ y) \equiv FALSE
    x = bdd.var('x')
    not_y = bdd.add_expr('~ y')
    qvars = ['x', 'y']
    r = cudd.or_forall(x, not_y, qvars)
    assert r == bdd.false, r


def test_swap():
    bdd = cudd.BDD()
    bdd.declare('x', 'y')
    x = bdd.var('x')
    y = bdd.var('y')
    # swap x and y
    #
    # This swap returns the same result as `bdd.let`
    # with the same arguments, because `d` contains
    # both `'x'` and `'y'` as keys.
    #
    # This result is obtained when the arguments are
    # not checked for overlapping key-value pairs.
    u = bdd.apply('and', x, ~ y)
    d = dict(x='y', y='x')
    with assert_raises(AssertionError):
        f = bdd._swap(u, d)
    # f_ = bdd.apply('and', ~ x, y)
    # assert f == f_, (f, f_)
    #
    # swap x and y
    # ensure swapping, not simultaneous substitution
    #
    # This swap returns a different result than
    # `bdd.let` when given the same arguments,
    # because `d` contains only `'x'` as key,
    # so `let` does not result in simultaneous
    # substitution.
    u = bdd.apply('and', x, ~ y)
    d = dict(x='y')  # swap x with y
    f = bdd._swap(u, d)
    f_ = bdd.apply('and', y, ~ x)
    # compare to the corresponding test of `bdd.let`
    assert f == f_, (f, f_)
    #
    # each variable should in at most one
    # key-value pair of `d`
    #
    # 1) keys and values are disjoint sets
    bdd.declare('z')
    z = bdd.var('z')
    u = bdd.apply('and', x, ~ y)
    d = dict(x='y', y='z')
    with assert_raises(AssertionError):
        f = bdd._swap(u, d)
    # The following result is obtained if the
    # assertions are removed from `BDD._swap`.
    # f_ = bdd.apply('and', y, ~ z)
    # assert f == f_, bdd.to_expr(f)
    #
    # 2) each value appears once among values
    u = bdd.apply('and', x, ~ y)
    d = dict(x='y', z='y')
    with assert_raises(AssertionError):
        f = bdd._swap(u, d)
    # The following result is obtained if the
    # assertions are removed from `BDD._swap`.
    # f_ = bdd.apply('and', y, ~ z)
    # assert f == f_, bdd.to_expr(f)


def test_copy_bdd_same_indices():
    # each va has same index in each `BDD`
    bdd = cudd.BDD()
    other = cudd.BDD()
    assert bdd != other
    dvars = ['x', 'y', 'z']
    for var in dvars:
        bdd.add_var(var)
        other.add_var(var)
    s = '(x /\ y) \/ ~ z'
    u0 = bdd.add_expr(s)
    u1 = cudd.copy_bdd(u0, other)
    u2 = cudd.copy_bdd(u1, bdd)
    # involution
    assert u0 == u2, (u0, u2)
    # confirm
    w = other.add_expr(s)
    assert w == u1, (w, u1)
    # different nodes
    u3 = cudd.copy_bdd(other.true, bdd)
    assert u3 != u2, (u3, u2)


def test_copy_bdd_different_indices():
    # each var has different index in each `BDD`
    bdd = cudd.BDD()
    other = cudd.BDD()
    assert bdd != other
    dvars = ['x', 'y', 'z']
    for var in dvars:
        bdd.add_var(var)
    for var in reversed(dvars):
        other.add_var(var)
    s = '(x \/ ~ y) /\ ~ z'
    u0 = bdd.add_expr(s)
    u1 = cudd.copy_bdd(u0, other)
    u2 = cudd.copy_bdd(u1, bdd)
    # involution
    assert u0 == u2, (u0, u2)
    # confirm
    w = other.add_expr(s)
    assert w == u1, (w, u1)
    # different nodes
    u3 = cudd.copy_bdd(other.true, bdd)
    assert u3 != u2, (u3, u2)


def test_copy_bdd_different_order():
    bdd = cudd.BDD()
    other = cudd.BDD()
    assert bdd != other
    dvars = ['x', 'y', 'z', 'w']
    for index, var in enumerate(dvars):
        bdd.add_var(var, index=index)
        other.add_var(var, index=index)
    # reorder
    order = dict(w=0, x=1, y=2, z=3)
    other.reorder(order)
    # confirm resultant order
    for var in order:
        level_ = order[var]
        level = other.level_of_var(var)
        assert level == level_, (var, level, level_)
    # same indices
    for var in dvars:
        i = bdd._index_of_var[var]
        j = other._index_of_var[var]
        assert i == j, (i, j)
    # but different levels
    for var in dvars:
        i = bdd.level_of_var(var)
        j = other.level_of_var(var)
        assert i != j, (i, j)
    # copy
    s = '(x \/ ~ y) /\ w /\ (z \/ ~ w)'
    u0 = bdd.add_expr(s)
    u1 = cudd.copy_bdd(u0, other)
    u2 = cudd.copy_bdd(u1, bdd)
    assert u0 == u2, (u0, u2)
    u3 = cudd.copy_bdd(other.false, bdd)
    assert u3 != u2, (u3, u2)
    # verify
    w = other.add_expr(s)
    assert w == u1, (w, u1)


def test_count_nodes():
    bdd = cudd.BDD()
    [bdd.add_var(var) for var in ['x', 'y', 'z']]
    u = bdd.add_expr('x /\ y')
    v = bdd.add_expr('x /\ z')
    assert len(u) == 3, len(u)
    assert len(v) == 3, len(v)
    bdd.reorder(dict(x=0, y=1, z=2))
    n = cudd.count_nodes([u, v])
    assert n == 5, n
    bdd.reorder(dict(z=0, y=1, x=2))
    n = cudd.count_nodes([u, v])
    assert n == 4, n


def test_function():
    bdd = cudd.BDD()
    bdd.add_var('x')
    # x
    x = bdd.var('x')
    assert not x.negated
    # ~ x
    not_x = ~x
    assert not_x.negated


if __name__ == '__main__':
    test_pick_iter()
