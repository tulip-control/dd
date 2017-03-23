import logging
from dd import autoref as _bdd
from nose.tools import assert_raises


logging.getLogger('astutils').setLevel('ERROR')


def test_true_false():
    bdd = _bdd.BDD()
    true = bdd.true
    false = bdd.false
    assert false != true
    assert false == ~true
    assert false == false & true
    assert true == true | false


def test_add_var():
    bdd = _bdd.BDD()
    bdd.add_var('x')
    bdd.add_var('y')
    assert set(bdd.vars) == {'x', 'y'}, bdd.vars
    x = bdd.var('x')
    y = bdd.var('y')
    assert x != y, (x, y)


def test_var_cofactor():
    bdd = _bdd.BDD()
    bdd.add_var('x')
    x = bdd.var('x')
    values = dict(x=False)
    u = bdd.let(values, x)
    assert u == bdd.false, u
    values = dict(x=True)
    u = bdd.let(values, x)
    assert u == bdd.true, u


def test_compose():
    bdd = _bdd.BDD()
    for var in ['x', 'y', 'z']:
        bdd.add_var(var)
    u = bdd.add_expr('x & !y')
    # x |-> y
    sub = dict(x=bdd.var('y'))
    v = bdd.let(sub, u)
    v_ = bdd.false
    assert v == v_, v
    # x |-> z
    sub = dict(x=bdd.var('z'))
    v = bdd.let(sub, u)
    v_ = bdd.add_expr('z & !y')
    assert v == v_, v
    # x |-> (y | z)
    sub = dict(x=bdd.add_expr('y | z'))
    v = bdd.let(sub, u)
    v_ = bdd.add_expr('(y | z) & !y')
    assert v == v_, v


def test_apply():
    bdd = _bdd.BDD()
    for var in ['x', 'y', 'z']:
        bdd.add_var(var)
    x = bdd.var('x')
    y = bdd.var('y')
    z = bdd.var('z')
    # x | !x = 1
    not_x = bdd.apply('not', x)
    true = bdd.apply('or', x, not_x)
    assert true == bdd.true, true
    # x & !x = 0
    false = bdd.apply('and', x, not_x)
    assert false == bdd.false, false
    # x & y = ! (!x | !y)
    u = bdd.apply('and', x, y)
    not_y = bdd.apply('not', y)
    v = bdd.apply('or', not_x, not_y)
    v = bdd.apply('not', v)
    assert u == v, (u, v)
    # xor
    u = bdd.apply('xor', x, y)
    r = bdd.let(dict(x=False, y=False), u)
    assert r == bdd.false, r
    r = bdd.let(dict(x=True, y=False), u)
    assert r == bdd.true, r
    r = bdd.let(dict(x=False, y=True), u)
    assert r == bdd.true, r
    r = bdd.let(dict(x=True, y=True), u)
    assert r == bdd.false, r
    # (z | !y) & x = (z & x) | (!y & x)
    u = bdd.apply('or', z, not_y)
    u = bdd.apply('and', u, x)
    v = bdd.apply('and', z, x)
    w = bdd.apply('and', not_y, x)
    v = bdd.apply('or', v, w)
    assert u == v, (u, v)
    # symbols
    u = bdd.apply('and', x, y)
    v = bdd.apply('&', x, y)
    assert u == v, (u, v)
    u = bdd.apply('or', x, y)
    v = bdd.apply('|', x, y)
    assert u == v, (u, v)
    u = bdd.apply('not', x)
    v = bdd.apply('!', x)
    assert u == v, (u, v)
    u = bdd.apply('xor', x, y)
    v = bdd.apply('^', x, y)
    assert u == v, (u, v)


def test_quantify():
    bdd = _bdd.BDD()
    for var in ['x', 'y']:
        bdd.add_var(var)
    x = bdd.var('x')
    # \E x: x = 1
    r = bdd.quantify(x, ['x'], forall=False)
    assert r == bdd.true, r
    # \A x: x = 0
    r = bdd.quantify(x, ['x'], forall=True)
    assert r == bdd.false, r
    # \E y: x = x
    r = bdd.quantify(x, ['y'], forall=False)
    assert r == x, (r, x)
    # \A y: x = x
    r = bdd.quantify(x, ['y'], forall=True)
    assert r == x, (r, x)
    # \E x: x & y = y
    y = bdd.var('y')
    u = bdd.apply('and', x, y)
    r = bdd.quantify(u, ['x'], forall=False)
    assert r == y, (r, y)
    assert r != x, (r, x)
    # \A x: x & y = 0
    r = bdd.quantify(u, ['x'], forall=True)
    assert r == bdd.false, r
    # \A x: !x | y = y
    not_x = bdd.apply('not', x)
    u = bdd.apply('or', not_x, y)
    r = bdd.quantify(u, ['x'], forall=True)
    assert r == y, (r, y)


def test_add_expr():
    bdd = _bdd.BDD()
    for var in ['x', 'y']:
        bdd.add_var(var)
    # (0 | 1) & x = x
    s = '(True | False) & x'
    u = bdd.add_expr(s)
    x = bdd.var('x')
    assert u == x, (u, x)
    # (x | !y) & x = x
    s = '(x | !y) & x'
    u = bdd.add_expr(s)
    assert u == x, (u, x)
    # x & y & z
    bdd.add_var('z')
    z = bdd.var('z')
    u = bdd.add_expr('x & y & z')
    u_ = bdd.cube(dict(x=True, y=True, z=True))
    assert u == u_, (u, u_)
    # x & !y & z
    u = bdd.add_expr('x & !y & z')
    u_ = bdd.cube(dict(x=True, y=False, z=True))
    assert u == u_, (u, u_)
    # \E x: x & y = y
    y = bdd.var('y')
    u = bdd.add_expr('\E x: x & y')
    assert u == y, (str(u), str(y))
    # \A x: x | !x = 1
    u = bdd.add_expr('\A x: !x | x')
    assert u == bdd.true, u


def test_support():
    # signle var
    bdd = _bdd.BDD()
    bdd.add_var('x')
    x = bdd.var('x')
    supp = bdd.support(x)
    assert supp == set(['x']), supp
    # two vars
    bdd.add_var('y')
    y = bdd.var('y')
    x_and_y = bdd.apply('and', x, y)
    supp = bdd.support(x_and_y)
    assert supp == set(['x', 'y']), supp


if __name__ == '__main__':
    test_support()
