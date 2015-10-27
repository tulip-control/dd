import logging
from dd import cudd
from nose.tools import assert_raises


logging.getLogger('astutils').setLevel('ERROR')


def test_true_false():
    bdd = cudd.BDD()
    true = bdd.true
    false = bdd.false
    assert false != true
    assert false == ~true
    assert false == false & true
    assert true == true | false
    del true, false


def test_add_var():
    bdd = cudd.BDD()
    bdd.add_var('x')
    bdd.add_var('y')
    jx = bdd._index_of_var['x']
    jy = bdd._index_of_var['y']
    assert jx == 0, jx
    assert jy == 1, jy
    x = bdd._var_with_index[0]
    y = bdd._var_with_index[1]
    assert x == 'x', x
    assert y == 'y', y
    assert bdd.vars == {'x', 'y'}, bdd.vars
    x = bdd.var('x')
    y = bdd.var('y')
    assert x != y, (x, y)
    del x, y


def test_var_cofactor():
    bdd = cudd.BDD()
    bdd.add_var('x')
    x = bdd.var('x')
    values = dict(x=False)
    u = bdd.cofactor(x, values)
    assert u == bdd.false, u
    values = dict(x=True)
    u = bdd.cofactor(x, values)
    assert u == bdd.true, u
    del x, u


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


def test_richcmp():
    bdd = cudd.BDD()
    assert bdd == bdd
    other = cudd.BDD()
    assert bdd != other


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


def test_contains():
    bdd = cudd.BDD()
    true = bdd.true
    assert true in bdd
    bdd.add_var('x')
    x = bdd.var('x')
    assert x in bdd
    # undefined `__contains__`
    other_bdd = cudd.BDD()
    other_true = other_bdd.true
    with assert_raises(AssertionError):
        other_true in bdd
    del x, true, other_true


def test_str():
    bdd = cudd.BDD()
    s = str(bdd)
    s + 'must be a string'


def test_levels():
    bdd = cudd.BDD()
    bdd.add_var('x', index=0)
    bdd.add_var('y', index=2)
    bdd.add_var('z', index=10)
    ix = bdd.level_of_var('x')
    iy = bdd.level_of_var('y')
    iz = bdd.level_of_var('z')
    # before any reordering, levels match var indices
    assert ix == 0, ix
    assert iy == 2, iy
    assert iz == 10, iz
    x = bdd.var_at_level(0)
    y = bdd.var_at_level(2)
    z = bdd.var_at_level(10)
    assert x == 'x', x
    assert y == 'y', y
    assert z == 'z', z


def test_cofactor():
    bdd = cudd.BDD()
    for var in ['x', 'y']:
        bdd.add_var(var)
    x = bdd.var('x')
    y = bdd.var('y')
    # x & y
    u = bdd.apply('and', x, y)
    r = bdd.cofactor(u, dict(x=False, y=False))
    assert r == bdd.false, r
    r = bdd.cofactor(u, dict(x=True, y=False))
    assert r == bdd.false, r
    r = bdd.cofactor(u, dict(x=False, y=True))
    assert r == bdd.false, r
    r = bdd.cofactor(u, dict(x=True, y=True))
    assert r == bdd.true, r
    # x & !y
    not_y = bdd.apply('not', y)
    u = bdd.apply('and', x, not_y)
    r = bdd.cofactor(u, dict(x=False, y=False))
    assert r == bdd.false, r
    r = bdd.cofactor(u, dict(x=True, y=False))
    assert r == bdd.true, r
    r = bdd.cofactor(u, dict(x=False, y=True))
    assert r == bdd.false, r
    r = bdd.cofactor(u, dict(x=True, y=True))
    assert r == bdd.false, r
    # !x | y
    not_x = bdd.apply('not', x)
    u = bdd.apply('or', not_x, y)
    r = bdd.cofactor(u, dict(x=False, y=False))
    assert r == bdd.true, r
    r = bdd.cofactor(u, dict(x=True, y=False))
    assert r == bdd.false, r
    r = bdd.cofactor(u, dict(x=False, y=True))
    assert r == bdd.true, r
    r = bdd.cofactor(u, dict(x=True, y=True))
    assert r == bdd.true, r
    del x, not_x, y, not_y, u, r


def test_apply():
    bdd = cudd.BDD()
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
    r = bdd.cofactor(u, dict(x=False, y=False))
    assert r == bdd.false, r
    r = bdd.cofactor(u, dict(x=True, y=False))
    assert r == bdd.true, r
    r = bdd.cofactor(u, dict(x=False, y=True))
    assert r == bdd.true, r
    r = bdd.cofactor(u, dict(x=True, y=True))
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
    del x, not_x, y, not_y, z, u, v, w, r, true, false


def test_quantify():
    bdd = cudd.BDD()
    for var in ['x', 'y']:
        bdd.add_var(var)
    x = bdd.var('x')
    # ? x. x = 1
    r = bdd.quantify(x, ['x'], forall=False)
    assert r == bdd.true, r
    # ! x. x = 0
    r = bdd.quantify(x, ['x'], forall=True)
    assert r == bdd.false, r
    # ? y. x = x
    r = bdd.quantify(x, ['y'], forall=False)
    assert r == x, (r, x)
    # ! y. x = x
    r = bdd.quantify(x, ['y'], forall=True)
    assert r == x, (r, x)
    # ? x. x & y = y
    y = bdd.var('y')
    u = bdd.apply('and', x, y)
    r = bdd.quantify(u, ['x'], forall=False)
    assert r == y, (r, y)
    assert r != x, (r, x)
    # ! x. x & y = 0
    r = bdd.quantify(u, ['x'], forall=True)
    assert r == bdd.false, r
    # ! x. !x | y = y
    not_x = bdd.apply('not', x)
    u = bdd.apply('or', not_x, y)
    r = bdd.quantify(u, ['x'], forall=True)
    assert r == y, (r, y)
    del x, not_x, y, r, u


def test_cube():
    bdd = cudd.BDD()
    for var in ['x', 'y', 'z']:
        bdd.add_var(var)
    # x
    x = bdd.var('x')
    c = bdd.cube(['x'])
    assert x == c, (x, c)
    # x & y
    y = bdd.var('y')
    u = bdd.apply('and', x, y)
    c = bdd.cube(['x', 'y'])
    assert u == c, (u, c)
    # x & !y
    not_y = bdd.apply('not', y)
    u = bdd.apply('and', x, not_y)
    d = dict(x=True, y=False)
    c = bdd.cube(d)
    assert u == c, (u, c)
    del c, x, y, not_y, u


def test_add_expr():
    bdd = cudd.BDD()
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
    u_ = bdd.cube({'x', 'y', 'z'})
    assert u == u_, (u, u_)
    # x & !y & z
    u = bdd.add_expr('x & !y & z')
    u_ = bdd.cube(dict(x=True, y=False, z=True))
    assert u == u_, (u, u_)
    # ? x. x & y = y
    y = bdd.var('y')
    u = bdd.add_expr('? x. x & y')
    assert u == y, (str(u), str(y))
    # ! x. x | !x = 1
    u = bdd.add_expr('! x. !x | x')
    assert u == bdd.true, u
    del x, y, z, u, u_


def test_dump_load():
    bdd = cudd.BDD()
    for var in ['x', 'y', 'z', 'w']:
        bdd.add_var(var)
    u = bdd.add_expr('(x & !w) | z')
    fname = 'bdd.txt'
    bdd.dump(u, fname)
    u_ = bdd.load(fname)
    assert u == u_
    del u, u_


def test_load_sample0():
    bdd = cudd.BDD()
    names = ['a', 'b', 'c']
    for var in names:
        bdd.add_var(var)
    fname = 'sample0.txt'
    u = bdd.load(fname)
    n = len(u)
    assert n == 5, n
    s = '! ( (a & (b |c)) | (!a & (b | !c)) )'
    u_ = bdd.add_expr(s)
    assert u == u_, (u, u_)
    del u, u_


def test_and_exists():
    bdd = cudd.BDD()
    for var in ['x', 'y']:
        bdd.add_var(var)
    # ? x. x & y = y
    x = bdd.add_expr('x')
    y = bdd.add_expr('y')
    qvars = ['x']
    r = cudd.and_exists(x, y, qvars, bdd)
    assert r == y, (r, y)
    # ? x. x & !x = 0
    not_x = bdd.apply('not', x)
    r = cudd.and_exists(x, not_x, qvars, bdd)
    assert r == bdd.false
    del x, not_x, y, r


def test_or_forall():
    bdd = cudd.BDD()
    for var in ['x', 'y']:
        bdd.add_var(var)
    # ! x y. x | ! y = 0
    x = bdd.var('x')
    not_y = bdd.add_expr('!y')
    qvars = ['x', 'y']
    r = cudd.or_forall(x, not_y, qvars, bdd)
    assert r == bdd.false, r
    del x, not_y, r


def test_support():
    # signle var
    bdd = cudd.BDD()
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
    del x, y, x_and_y


def test_rename():
    bdd = cudd.BDD()
    for var in ['x', 'y']:
        bdd.add_var(var)
    # x -> y
    x = bdd.var('x')
    supp = bdd.support(x)
    assert supp == set(['x']), supp
    d = dict(x='y')
    f = cudd.rename(x, bdd, d)
    supp = bdd.support(f)
    assert supp == set(['y']), supp
    y = bdd.var('y')
    assert f == y, (f, y)
    # x, y -> z, w
    for var in ['z', 'w']:
        bdd.add_var(var)
    not_y = bdd.apply('not', y)
    u = bdd.apply('or', x, not_y)
    supp = bdd.support(u)
    assert supp == set(['x', 'y']), supp
    d = dict(x='z', w='y')
    f = cudd.rename(u, bdd, d)
    supp = bdd.support(f)
    assert supp == set(['z', 'w']), supp
    z = bdd.var('z')
    w = bdd.var('w')
    not_w = bdd.apply('not', w)
    f_ = bdd.apply('or', z, not_w)
    assert f == f_, (f, f_)
    # x -> x
    d = dict(x='y', y='x')
    with assert_raises(AssertionError):
        cudd.rename(u, bdd, d)
    del x, y, not_y, z, w, not_w, u, f, f_


def test_reorder():
    bdd = cudd.BDD()
    dvars = ['x', 'y', 'z']
    for var in dvars:
        bdd.add_var(var)
    for i, var in enumerate(dvars):
        level = bdd.level_of_var(var)
        assert level == i, (var, level, i)
    order = dict(y=0, z=1, x=2)
    cudd.reorder(bdd, order)
    for var, level_ in order.iteritems():
        level = bdd.level_of_var(var)
        assert level == level_, (var, level, level_)


def test_copy_bdd_same_indices():
    # each va has same index in each `BDD`
    bdd = cudd.BDD()
    other = cudd.BDD()
    assert bdd != other
    dvars = ['x', 'y', 'z']
    for var in dvars:
        bdd.add_var(var)
        other.add_var(var)
    s = '(x & y) | !z'
    u0 = bdd.add_expr(s)
    u1 = cudd.copy_bdd(u0, bdd, other)
    u2 = cudd.copy_bdd(u1, other, bdd)
    # involution
    assert u0 == u2, (u0, u2)
    # confirm
    w = other.add_expr(s)
    assert w == u1, (w, u1)
    # different nodes
    u3 = cudd.copy_bdd(other.true, other, bdd)
    assert u3 != u2, (u3, u2)
    # same bdd
    with assert_raises(AssertionError):
        cudd.copy_bdd(u0, bdd, bdd)
    del u0, u1, u2, u3, w


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
    u0 = bdd.add_expr('(x | !y) & !z')
    with assert_raises(AssertionError):
        cudd.copy_bdd(u0, bdd, other)
    del u0


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
    cudd.reorder(other, order)
    # confirm resultant order
    for var, level_ in order.iteritems():
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
    s = '(x | !y) & w & (z | !w)'
    u0 = bdd.add_expr(s)
    u1 = cudd.copy_bdd(u0, bdd, other)
    u2 = cudd.copy_bdd(u1, other, bdd)
    assert u0 == u2, (u0, u2)
    u3 = cudd.copy_bdd(other.false, other, bdd)
    assert u3 != u2, (u3, u2)
    # verify
    w = other.add_expr(s)
    assert w == u1, (w, u1)
    del u0, u1, u2, u3, w


def test_function():
    bdd = cudd.BDD()
    bdd.add_var('x')
    # x
    x = bdd.var('x')
    assert not x.negated
    low = x.low
    assert low == bdd.false, low
    high = x.high
    assert high == bdd.true, high
    # ! x
    not_x = ~x
    assert not_x.negated
    low = not_x.low
    assert low == bdd.false, low
    high = not_x.high
    assert high == bdd.true, high
    del x, not_x, low, high


if __name__ == '__main__':
    test_load()
