import logging
from dd import sylvan


logging.getLogger('astutils').setLevel('ERROR')


def test_len():
    b = sylvan.BDD()
    # constant
    assert len(b) == 0, len(b)
    u = b.false
    assert len(b) == 0, len(b)
    del u
    assert len(b) == 0, len(b)
    # var node
    b.add_var('x')
    u = b.var('x')
    assert len(b) == 1, len(b)
    del u
    assert len(b) == 0, len(b)


def test_true_false():
    b = sylvan.BDD()
    false = b.false
    true = b.true
    assert false != true
    assert false == ~true
    assert false == false & true
    assert true == true | false
    del true, false


def test_add_var():
    bdd = sylvan.BDD()
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


def test_insert_var():
    bdd = sylvan.BDD()
    level = 0
    j = bdd.add_var('x', index=level)
    assert j == 0, j  # initially indices = levels
    x = bdd.var_at_level(level)
    assert x == 'x', x
    level = 101
    bdd.add_var('y', index=level)
    y = bdd.var_at_level(level)
    assert y == 'y', y


def test_add_expr():
    bdd = sylvan.BDD()
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
    # ? x. x & y = y
    y = bdd.var('y')
    u = bdd.add_expr('\E x: x & y')
    assert u == y, (str(u), str(y))
    # ! x. x | !x = 1
    u = bdd.add_expr('\A x: !x | x')
    assert u == bdd.true, u
    del x, y, z, u, u_


def test_support():
    bdd = sylvan.BDD()
    bdd.add_var('x')
    bdd.add_var('y')
    u = bdd.var('x')
    supp = bdd.support(u)
    assert supp == {'x'}, supp
    u = bdd.var('y')
    supp = bdd.support(u)
    assert supp == {'y'}, supp
    u = bdd.add_expr('x & y')
    supp = bdd.support(u)
    assert supp == {'x', 'y'}, supp
    del u


def test_compose():
    bdd = sylvan.BDD()
    bdd.add_var('x')
    bdd.add_var('y')
    x = bdd.var('x')
    y = bdd.var('y')
    var_sub = dict(x=y)
    y_ = bdd.compose(x, var_sub)
    assert y == y_, bdd.to_expr(y_)
    del x, y, y_, var_sub


def test_cofactor():
    bdd = sylvan.BDD()
    bdd.add_var('x')
    x = bdd.var('x')
    # u = bdd.cofactor(x, dict(x=True))
    # assert u == bdd.true, u
    # u = bdd.cofactor(x, dict(x=False))
    # u = bdd.true
    # u_ = bdd.false
    # assert u == ~u_
    assert x == bdd.add_expr('x')
    u = bdd.compose(x, dict(x=bdd.false))
    u_ = bdd.false
    assert u == u_, (u, u_)
    del x, u, u_


def test_rename():
    bdd = sylvan.BDD()
    # single variable
    bdd.add_var('x')
    bdd.add_var('y')
    x = bdd.var('x')
    y = bdd.var('y')
    rename = dict(x='y')
    y_ = bdd.rename(x, rename)
    assert y == y_, bdd.to_expr(y_)
    # multiple variables
    bdd.add_var('z')
    bdd.add_var('w')
    s = '(x & !y) | w'
    u = bdd.add_expr(s)
    rename = dict(x='w', y='z', w='y')
    v = bdd.rename(u, rename)
    s = '(w & !z) | y'
    v_ = bdd.add_expr(s)
    assert v == v_, bdd.to_expr(v)
    del x, y, y_, u, v, v_


if __name__ == '__main__':
    test_cofactor()
