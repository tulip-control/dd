"""Tests of the module `dd.cudd_zdd`."""
import os

from dd import cudd
from dd import cudd_zdd
from dd import _copy

from common import Tests as Tests
from common_cudd import Tests as CuddTests


Tests.DD = cudd_zdd.ZDD
CuddTests.DD = cudd_zdd.ZDD
CuddTests.MODULE = cudd_zdd


def test_false():
    zdd = cudd_zdd.ZDD()
    u = zdd.false
    assert len(u) == 0, len(u)


def test_true():
    zdd = cudd_zdd.ZDD()
    zdd.declare('x', 'y', 'z', 'w')
    u = zdd.true
    assert u.low is not None
    assert u.high is not None
    assert len(u) == 4, len(u)


def test_true_node():
    zdd = cudd_zdd.ZDD()
    zdd.declare('x', 'y')
    u = zdd.true_node
    assert u.low is None
    assert u.high is None
    assert len(u) == 0, len(u)


def test_var():
    zdd = cudd_zdd.ZDD()
    zdd.declare('x', 'y', 'z')
    x = zdd.var('x')
    x_ = zdd._var_cudd('x')
    assert x == x_, len(x)
    y = zdd.var('y')
    y_ = zdd._var_cudd('y')
    assert y == y_, len(y)
    z = zdd.var('z')
    z_ = zdd._var_cudd('z')
    assert z == z_, len(z)


def test_support_cudd():
    # support implemented by CUDD
    zdd = cudd_zdd.ZDD()
    zdd.declare('x', 'y')
    zdd._add_bdd_var(0)
    zdd._add_bdd_var(1)
    u = zdd.add_expr('~ x')
    s = zdd._support_cudd(u)
    assert s == {'y'}, s  # `{'x'}` is expected


def test_cudd_cofactor():
    zdd = cudd_zdd.ZDD()
    zdd.declare('x', 'y')
    u = zdd.add_expr(r'x /\ ~ y')
    r = zdd._cofactor_cudd(u, 'y', False)
    r_ = zdd.add_expr(r'x /\ ~ y')
    assert r == r_, len(r)
    u = zdd.add_expr(r'x /\ y')
    r = zdd._cofactor_cudd(u, 'x', True)
    r_ = zdd.add_expr(r'~ x /\ y')  # no node at x
    assert r == r_


def test_find_or_add():
    bdd = cudd_zdd.ZDD()
    bdd.declare('x', 'y', 'z')
    v = bdd.add_expr(r'~ x /\ y /\ ~ z')
    w = bdd.add_expr(r'~ x /\ ~ y /\ z')
    u = bdd.find_or_add('x', v, w)
    assert u.low == v, len(u)
    assert u.high == w, len(u)
    assert u.var == 'x', u.var
    assert u.level == 0, u.level


def test_count():
    zdd = cudd_zdd.ZDD()
    zdd.declare('x', 'y')
    # FALSE
    u = zdd.false
    n = zdd.count(u, 2)
    assert n == 0, n
    # TRUE
    u = zdd.true
    n = zdd.count(u, 1)
    assert n == 2, n
    n = zdd.count(u, 2)
    assert n == 4, n


def test_bdd_to_zdd_copy():
    zdd = cudd_zdd.ZDD()
    zdd.declare('x', 'y', 'z')
    bdd = cudd.BDD()
    bdd.declare('x', 'y', 'z')
    u = bdd.add_expr('x')
    v = bdd.copy(u, zdd)
    x = zdd.var('x')
    assert v == x, len(v)
    print_size(v, 'v')
    # copy `y`
    u = bdd.var('y')
    y = bdd.copy(u, zdd)
    y_ = zdd.var('y')
    assert y == y_, (y, y_)


def test_len():
    zdd = cudd_zdd.ZDD()
    zdd.declare('x', 'y', 'z')
    # x
    x = zdd.var('x')
    assert len(x) == 3, len(x)
    # y
    y = zdd.var('y')
    assert len(y) == 3, len(y)
    # x /\ y /\ ~ z
    u = x & y & ~ zdd.var('z')
    assert len(u) == 2, len(u)
    # ~ x
    u = zdd.add_expr('~ x')
    assert len(u) == 2, len(u)


def test_disjunction():
    zdd = cudd_zdd.ZDD()
    zdd.declare('w', 'x', 'y')
    # x \/ TRUE
    v = zdd.add_expr('x')
    w = zdd.true
    u = zdd._disjoin_root(v, w)
    assert u == w, len(u)
    # x \/ FALSE
    w = zdd.false
    u = zdd._disjoin_root(v, w)
    assert u == v, len(u)
    # x \/ y
    v = zdd.add_expr('x')
    w = zdd.add_expr('y')
    u = zdd._disjoin_root(v, w)
    u_ = zdd.add_expr(r'x \/ y')
    assert u == u_, len(u)
    # (~ w /\ x) \/ y
    v = zdd.add_expr(r'~ w /\ x')
    w = zdd.add_expr('y')
    u = zdd._disjoin_root(v, w)
    u_ = zdd.add_expr(r'(~ w /\ x) \/ y')
    assert u == u_, len(u)


def test_conjunction():
    zdd = cudd_zdd.ZDD()
    zdd.declare('x', 'y', 'z')
    v = zdd.var('x')
    w = zdd.var('y')
    u = zdd._conjoin_root(v, w)
    u_ = zdd.add_expr(r'x /\ y')
    assert u == u_, len(u)
    u = zdd._conjoin_root(v, ~ w)
    u_ = zdd.add_expr(r'x /\ ~ y')
    assert u == u_, len(u)


def test_c_disjunction():
    zdd = cudd_zdd.ZDD()
    zdd.declare('w', 'x', 'y')
    v = zdd.add_expr(r'~ w /\ x')
    w = zdd.add_expr('y')
    u = cudd_zdd._c_disjoin(v, w)
    u_ = zdd.add_expr(r'(~ w /\ x) \/ y')
    assert u == u_, len(u)


def test_c_conjunction():
    zdd = cudd_zdd.ZDD()
    zdd.declare('x', 'y', 'z')
    x = zdd.var('x')
    y = zdd.var('y')
    u = cudd_zdd._c_conjoin(x, y)
    u_ = zdd.add_expr(r'x /\ y')
    assert u == u_, len(u)


def test_c_exist():
    zdd = cudd_zdd.ZDD()
    zdd.declare('x', 'y', 'z')
    # \E x:  (x /\ ~ y) \/ ~ z
    u = zdd.add_expr(r'(x /\ ~ y) \/ ~ z')
    qvars = ['x']
    r = cudd_zdd._c_exist(qvars, u)
    r_ = zdd.exist(qvars, u)
    assert r == r_, len(r)
    # \E x:  x
    u = zdd.add_expr('x')
    qvars = ['x']
    r = cudd_zdd._c_exist(qvars, u)
    r_ = zdd.exist(qvars, u)
    assert r == r_, len(r)


def test_dump():
    zdd = cudd_zdd.ZDD()
    zdd.declare('x', 'y', 'w')
    u = zdd.add_expr('~ w')
    fname = 'not_w.pdf'
    if os.path.isfile(fname):
        os.remove(fname)
    assert not os.path.isfile(fname)
    zdd.dump(fname, [u])
    assert os.path.isfile(fname)


def test_dict_to_zdd():
    zdd = cudd_zdd.ZDD()
    zdd.declare('x', 'y', 'z')
    qvars = {'x', 'z'}
    u = cudd_zdd._dict_to_zdd(qvars, zdd)
    assert len(u) == 2, len(u)
    assert u.var == 'x', u.var
    assert u.low == u.high
    v = u.low
    assert v.var == 'z', v.var
    assert v.low == v.high
    assert v.low == zdd.true_node


def print_size(u, msg):
    n = len(u)
    print('Dag size of {msg}: {n}'.format(
        msg=msg, n=n))


if __name__ == '__main__':
    Tests().test_support()
    # test_compose()
