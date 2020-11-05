import logging
from dd import sylvan


logging.getLogger('astutils').setLevel('ERROR')


def test_len():
    """
    Return the length of the length.

    Args:
    """
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
    """
    Test if two true false false otherwise.

    Args:
    """
    b = sylvan.BDD()
    false = b.false
    true = b.true
    assert false != true
    assert false == ~ true
    assert false == false & true
    assert true == true | false
    del true, false


def test_add_var():
    """
    Add a bdd to make a var.

    Args:
    """
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
    """
    Insert a new variables.

    Args:
    """
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
    """
    Add expr expr to bdd.

    Args:
    """
    bdd = sylvan.BDD()
    for var in ['x', 'y']:
        bdd.add_var(var)
    # ((0 \/ 1) /\ x) \equiv x
    s = '(TRUE \/ FALSE) /\ x'
    u = bdd.add_expr(s)
    x = bdd.var('x')
    assert u == x, (u, x)
    # ((x \/ ~ y) /\ x) \equiv x
    s = '(x \/ ~ y) /\ x'
    u = bdd.add_expr(s)
    assert u == x, (u, x)
    # x /\ y /\ z
    bdd.add_var('z')
    z = bdd.var('z')
    u = bdd.add_expr('x /\ y /\ z')
    u_ = bdd.cube(dict(x=True, y=True, z=True))
    assert u == u_, (u, u_)
    # x /\ ~ y /\ z
    u = bdd.add_expr('x /\ ~ y /\ z')
    u_ = bdd.cube(dict(x=True, y=False, z=True))
    assert u == u_, (u, u_)
    # (\E x:  x /\ y) \equiv y
    y = bdd.var('y')
    u = bdd.add_expr('\E x:  x /\ y')
    assert u == y, (str(u), str(y))
    # (\A x:  x \/ ~ x) \equiv TRUE
    u = bdd.add_expr('\A x:  ~ x \/ x')
    assert u == bdd.true, u
    del x, y, z, u, u_


def test_support():
    """
    Create a new support support.

    Args:
    """
    bdd = sylvan.BDD()
    bdd.add_var('x')
    bdd.add_var('y')
    u = bdd.var('x')
    supp = bdd.support(u)
    assert supp == {'x'}, supp
    u = bdd.var('y')
    supp = bdd.support(u)
    assert supp == {'y'}, supp
    u = bdd.add_expr('x /\ y')
    supp = bdd.support(u)
    assert supp == {'x', 'y'}, supp
    del u


def test_compose():
    """
    Compute the test test for a test.

    Args:
    """
    bdd = sylvan.BDD()
    bdd.add_var('x')
    bdd.add_var('y')
    x = bdd.var('x')
    y = bdd.var('y')
    var_sub = dict(x=y)
    y_ = bdd.let(var_sub, x)
    assert y == y_, bdd.to_expr(y_)
    del x, y, y_, var_sub


def test_cofactor():
    """
    Calculate cofactor coefficients.

    Args:
    """
    bdd = sylvan.BDD()
    bdd.add_var('x')
    x = bdd.var('x')
    # u = bdd.let(dict(x=True), x)
    # assert u == bdd.true, u
    # u = bdd.let(dict(x=False), x)
    # u = bdd.true
    # u_ = bdd.false
    # assert u == ~u_
    assert x == bdd.add_expr('x')
    u = bdd.let(dict(x=bdd.false), x)
    u_ = bdd.false
    assert u == u_, (u, u_)
    del x, u, u_


def test_rename():
    """
    Rename a bdd

    Args:
    """
    bdd = sylvan.BDD()
    # single variable
    bdd.add_var('x')
    bdd.add_var('y')
    x = bdd.var('x')
    y = bdd.var('y')
    rename = dict(x='y')
    y_ = bdd.let(rename, x)
    assert y == y_, bdd.to_expr(y_)
    # multiple variables
    bdd.add_var('z')
    bdd.add_var('w')
    s = '(x /\ ~ y) \/ w'
    u = bdd.add_expr(s)
    rename = dict(x='w', y='z', w='y')
    v = bdd.let(rename, u)
    s = '(w /\ ~ z) \/ y'
    v_ = bdd.add_expr(s)
    assert v == v_, bdd.to_expr(v)
    del x, y, y_, u, v, v_


# The function `test_pick_iter` is copied
# from `common.Tests.test_pick_iter`.
def test_pick_iter():
    """
    Iterate over an iterable of a pickle.

    Args:
    """
    b = sylvan.BDD()
    b.add_var('x')
    b.add_var('y')
    # FALSE
    u = b.false
    m = list(b.pick_iter(u))
    assert not m, m
    # TRUE, no care vars
    u = b.true
    m = list(b.pick_iter(u))
    assert m == [{}], m
    # x
    u = b.add_expr('x')
    m = list(b.pick_iter(u))
    m_ = [dict(x=True)]
    assert m == m_, (m, m_)
    # ~ x /\ y
    s = '~ x /\ y'
    u = b.add_expr(s)
    g = b.pick_iter(u, care_vars=set())
    m = list(g)
    m_ = [dict(x=False, y=True)]
    assert m == m_, (m, m_)
    u = b.add_expr(s)
    g = b.pick_iter(u)
    m = list(g)
    assert m == m_, (m, m_)
    # x /\ y
    u = b.add_expr('x /\ y')
    m = list(b.pick_iter(u))
    m_ = [dict(x=True, y=True)]
    assert m == m_, m
    # x
    s = '~ y'
    u = b.add_expr(s)
    # partial
    g = b.pick_iter(u)
    m = list(g)
    m_ = [dict(y=False)]
    equal_list_contents(m, m_)
    # partial
    g = b.pick_iter(u, care_vars=['x', 'y'])
    m = list(g)
    m_ = [
        dict(x=True, y=False),
        dict(x=False, y=False)]
    equal_list_contents(m, m_)
    # care bits x, y
    b.add_var('z')
    s = 'x \/ y'
    u = b.add_expr(s)
    g = b.pick_iter(u, care_vars=['x', 'y'])
    m = list(g)
    m_ = [
        dict(x=True, y=False),
        dict(x=False, y=True),
        dict(x=True, y=True)]
    equal_list_contents(m, m_)


# The function `equal_list_contents` is copied
# from `common.Tests.equal_list_contents`.
def equal_list_contents(x, y):
    """
    Check if two lists are equal.

    Args:
        x: (todo): write your description
        y: (todo): write your description
    """
    for u in x:
        assert u in y, (u, x, y)
    for u in y:
        assert u in x, (u, x, y)


if __name__ == '__main__':
    test_pick_iter()
