"""Tests of the module `dd.cudd`."""
# This file is released in the public domain.
#
import logging

import dd.cudd as _cudd
import pytest

import common
import common_bdd
import common_cudd


logging.getLogger('astutils').setLevel('ERROR')


class Tests(common.Tests):
    def setup_method(self):
        self.DD = _cudd.BDD


class BDDTests(common_bdd.Tests):
    def setup_method(self):
        self.DD = _cudd.BDD


class CuddTests(common_cudd.Tests):
    def setup_method(self):
        self.DD = _cudd.BDD
        self.MODULE = _cudd


def test_str():
    bdd = _cudd.BDD()
    with pytest.warns(UserWarning):
        s = str(bdd)
    s + 'must be a string'


def test_insert_var():
    bdd = _cudd.BDD()
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
    _cudd._test_incref()
    _cudd._test_decref()


def test_len():
    bdd = _cudd.BDD()
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
    _cudd._test_dict_to_cube_array()
    _cudd._test_cube_array_to_dict()


def test_dump_load_dddmp():
    bdd = _cudd.BDD()
    for var in ['x', 'y', 'z', 'w']:
        bdd.add_var(var)
    u = bdd.add_expr(r'(x /\ ~ w) \/ z')
    fname = 'bdd.dddmp'
    bdd.dump(fname, [u], filetype='dddmp')
    u_, = bdd.load(fname)
    assert u == u_


def test_load_sample0():
    bdd = _cudd.BDD()
    names = ['a', 'b', 'c']
    for var in names:
        bdd.add_var(var)
    fname = 'sample0.dddmp'
    u, = bdd.load(fname)
    n = len(u)
    assert n == 5, n
    s = r'~ ( (a /\ (b \/ c)) \/ (~ a /\ (b \/ ~ c)) )'
    u_ = bdd.add_expr(s)
    assert u == u_, (u, u_)


def test_and_exists():
    bdd = _cudd.BDD()
    for var in ['x', 'y']:
        bdd.add_var(var)
    # (\E x:  x /\ y) \equiv y
    x = bdd.add_expr('x')
    y = bdd.add_expr('y')
    qvars = ['x']
    r = _cudd.and_exists(x, y, qvars)
    assert r == y, (r, y)
    # (\E x:  x /\ ~ x) \equiv FALSE
    not_x = bdd.apply('not', x)
    r = _cudd.and_exists(x, not_x, qvars)
    assert r == bdd.false


def test_or_forall():
    bdd = _cudd.BDD()
    for var in ['x', 'y']:
        bdd.add_var(var)
    # (\A x, y:  x \/ ~ y) \equiv FALSE
    x = bdd.var('x')
    not_y = bdd.add_expr('~ y')
    qvars = ['x', 'y']
    r = _cudd.or_forall(x, not_y, qvars)
    assert r == bdd.false, r


def test_swap():
    bdd = _cudd.BDD()
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
    with pytest.raises(ValueError):
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
    with pytest.raises(ValueError):
        f = bdd._swap(u, d)
    # The following result is obtained if the
    # assertions are removed from `BDD._swap`.
    # f_ = bdd.apply('and', y, ~ z)
    # assert f == f_, bdd.to_expr(f)
    #
    # 2) each value appears once among values
    u = bdd.apply('and', x, ~ y)
    d = dict(x='y', z='y')
    with pytest.raises(ValueError):
        f = bdd._swap(u, d)
    # The following result is obtained if the
    # assertions are removed from `BDD._swap`.
    # f_ = bdd.apply('and', y, ~ z)
    # assert f == f_, bdd.to_expr(f)


def test_copy_bdd_same_indices():
    # each va has same index in each `BDD`
    bdd = _cudd.BDD()
    other = _cudd.BDD()
    assert bdd != other
    dvars = ['x', 'y', 'z']
    for var in dvars:
        bdd.add_var(var)
        other.add_var(var)
    s = r'(x /\ y) \/ ~ z'
    u0 = bdd.add_expr(s)
    u1 = _cudd.copy_bdd(u0, other)
    u2 = _cudd.copy_bdd(u1, bdd)
    # involution
    assert u0 == u2, (u0, u2)
    # confirm
    w = other.add_expr(s)
    assert w == u1, (w, u1)
    # different nodes
    u3 = _cudd.copy_bdd(other.true, bdd)
    assert u3 != u2, (u3, u2)


def test_copy_bdd_different_indices():
    # each var has different index in each `BDD`
    bdd = _cudd.BDD()
    other = _cudd.BDD()
    assert bdd != other
    dvars = ['x', 'y', 'z']
    for var in dvars:
        bdd.add_var(var)
    for var in reversed(dvars):
        other.add_var(var)
    s = r'(x \/ ~ y) /\ ~ z'
    u0 = bdd.add_expr(s)
    u1 = _cudd.copy_bdd(u0, other)
    u2 = _cudd.copy_bdd(u1, bdd)
    # involution
    assert u0 == u2, (u0, u2)
    # confirm
    w = other.add_expr(s)
    assert w == u1, (w, u1)
    # different nodes
    u3 = _cudd.copy_bdd(other.true, bdd)
    assert u3 != u2, (u3, u2)


def test_copy_bdd_different_order():
    bdd = _cudd.BDD()
    other = _cudd.BDD()
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
    s = r'(x \/ ~ y) /\ w /\ (z \/ ~ w)'
    u0 = bdd.add_expr(s)
    u1 = _cudd.copy_bdd(u0, other)
    u2 = _cudd.copy_bdd(u1, bdd)
    assert u0 == u2, (u0, u2)
    u3 = _cudd.copy_bdd(other.false, bdd)
    assert u3 != u2, (u3, u2)
    # verify
    w = other.add_expr(s)
    assert w == u1, (w, u1)


def test_count_nodes():
    bdd = _cudd.BDD()
    [bdd.add_var(var) for var in ['x', 'y', 'z']]
    u = bdd.add_expr(r'x /\ y')
    v = bdd.add_expr(r'x /\ z')
    assert len(u) == 3, len(u)
    assert len(v) == 3, len(v)
    bdd.reorder(dict(x=0, y=1, z=2))
    n = _cudd.count_nodes([u, v])
    assert n == 5, n
    bdd.reorder(dict(z=0, y=1, x=2))
    n = _cudd.count_nodes([u, v])
    assert n == 4, n


def test_function():
    bdd = _cudd.BDD()
    bdd.add_var('x')
    # x
    x = bdd.var('x')
    assert not x.negated
    # ~ x
    not_x = ~x
    assert not_x.negated


if __name__ == '__main__':
    test_function()
