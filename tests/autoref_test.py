import logging

from dd import autoref as _bdd
import dd.bdd
from nose.tools import assert_raises


logging.getLogger('astutils').setLevel('ERROR')


def test_true_false():
    bdd = _bdd.BDD()
    true = bdd.true
    false = bdd.false
    assert false != true
    assert false == ~ true
    assert false == false & true
    assert true == true | false


def test_succ():
    bdd = _bdd.BDD()
    bdd.declare('x')
    u = bdd.var('x')
    level, low, high = bdd.succ(u)
    assert level == 0, level
    assert low == bdd.false, low
    assert high == bdd.true, high


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


def test_var_levels():
    bdd = _bdd.BDD()
    # single variable
    bdd.declare('x')
    level = bdd.level_of_var('x')
    assert level == 0, level
    var = bdd.var_at_level(0)
    assert var == 'x', var
    # two variables
    bdd.declare('y')
    x_level = bdd.level_of_var('x')
    var = bdd.var_at_level(x_level)
    assert var == 'x', var
    y_level = bdd.level_of_var('y')
    var = bdd.var_at_level(y_level)
    assert var == 'y', var
    assert x_level != y_level, (x_level, y_level)
    assert x_level >= 0, x_level
    assert y_level >= 0, y_level


def test_manager_eq():
    bdd = _bdd.BDD()
    assert bdd == bdd
    other = _bdd.BDD()
    assert bdd != other


def test_str():
    bdd = _bdd.BDD()
    s = str(bdd)
    assert isinstance(s, str), s


def test_copy():
    bdd = _bdd.BDD()
    other = _bdd.BDD()
    bdd.declare('x')
    other.declare('x')
    u = bdd.add_expr('~ x')
    v = bdd.copy(u, other)
    v_ = other.add_expr('~ x')
    assert v == v_, (v, v_)
    # copy to same manager
    w = bdd.copy(u, bdd)
    assert u == w, (u, w)


def test_compose():
    bdd = _bdd.BDD()
    for var in ['x', 'y', 'z']:
        bdd.add_var(var)
    u = bdd.add_expr('x /\ ~ y')
    # x |-> y
    sub = dict(x=bdd.var('y'))
    v = bdd.let(sub, u)
    v_ = bdd.false
    assert v == v_, v
    # x |-> z
    sub = dict(x=bdd.var('z'))
    v = bdd.let(sub, u)
    v_ = bdd.add_expr('z /\ ~ y')
    assert v == v_, v
    # x |-> (y \/ z)
    sub = dict(x=bdd.add_expr('y \/ z'))
    v = bdd.let(sub, u)
    v_ = bdd.add_expr('(y \/ z) /\ ~ y')
    assert v == v_, v


def test_apply():
    bdd = _bdd.BDD()
    for var in ['x', 'y', 'z']:
        bdd.add_var(var)
    x = bdd.var('x')
    y = bdd.var('y')
    z = bdd.var('z')
    # (x \/ ~ x) \equiv TRUE
    not_x = bdd.apply('not', x)
    true = bdd.apply('or', x, not_x)
    assert true == bdd.true, true
    # (x /\ ~ x) \equiv FALSE
    false = bdd.apply('and', x, not_x)
    assert false == bdd.false, false
    # (x /\ y) \equiv ~ (~ x \/ ~ y)
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
    # (z \/ ~ y) /\ x = (z /\ x) \/ (~ y /\ x)
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
    # ternary
    u = bdd.apply('ite', x, y, ~ z)
    u_ = bdd.add_expr('(x /\ y) \/ (~ x /\ ~ z)')
    assert u == u_, (u, u_)


def test_quantify():
    bdd = _bdd.BDD()
    for var in ['x', 'y']:
        bdd.add_var(var)
    x = bdd.var('x')
    # \E x: x = 1
    r = bdd.exist(['x'], x)
    assert r == bdd.true, r
    # \A x: x = 0
    r = bdd.forall(['x'], x)
    assert r == bdd.false, r
    # \E y: x = x
    r = bdd.exist(['y'], x)
    assert r == x, (r, x)
    # \A y: x = x
    r = bdd.forall(['y'], x)
    assert r == x, (r, x)
    # (\E x:  x /\ y) \equiv y
    y = bdd.var('y')
    u = bdd.apply('and', x, y)
    r = bdd.exist(['x'], u)
    assert r == y, (r, y)
    assert r != x, (r, x)
    # (\A x:  x /\ y) \equiv FALSE
    r = bdd.forall(['x'], u)
    assert r == bdd.false, r
    # (\A x:  ~ x \/ y) \equiv y
    not_x = bdd.apply('not', x)
    u = bdd.apply('or', not_x, y)
    r = bdd.forall(['x'], u)
    assert r == y, (r, y)


def test_add_expr():
    bdd = _bdd.BDD()
    for var in ['x', 'y']:
        bdd.add_var(var)
    # (FALSE \/ TRUE) /\ x = x
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


def test_ite():
    bdd = _bdd.BDD()
    bdd.declare('x')
    x = bdd.var('x')
    u = bdd.ite(x, bdd.false, bdd.true)
    assert u == ~ x, (u, x)


def test_find_or_add():
    bdd = _bdd.BDD()
    bdd.declare('x', 'y')
    n = len(bdd)
    u = bdd.find_or_add('x', bdd.true, bdd.false)
    m = len(bdd)
    assert n < m, (n, m)
    u_ = bdd.find_or_add('x', bdd.true, bdd.false)
    assert u == u_, (u, u_)
    m_ = len(bdd)
    assert m == m_, (m, m_)


def test_support():
    # single var
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
    # method `Function.support`
    supp_ = x_and_y.support
    assert supp == supp_, (supp, supp_)


def test_count():
    bdd = _bdd.BDD()
    bdd.declare('x', 'y')
    u = bdd.add_expr('x')
    n = bdd.count(u)
    assert n == 1, n
    u = bdd.add_expr('x /\ y')
    n = bdd.count(u)
    assert n == 1, n
    u = bdd.add_expr('x \/ y')
    n = bdd.count(u)
    assert n == 3, n


def test_pick_iter():
    bdd = _bdd.BDD()
    bdd.declare('x', 'y')
    # single var
    u = bdd.add_expr('x')
    models = list(bdd.pick_iter(u))
    models_ = [dict(x=True)]
    assert models == models_, (models, models_)
    # two vars
    u = bdd.add_expr('x \/ y')
    models = list(bdd.pick_iter(u))
    models_ = [
        dict(x=True, y=True),
        dict(x=True, y=False),
        dict(x=False, y=True)]
    for m in models:
        assert m in models_
    for m in models_:
        assert m in models


def test_to_expr():
    bdd = _bdd.BDD()
    bdd.declare('x', 'y')
    u = bdd.add_expr('x')
    s = bdd.to_expr(u)
    assert s == 'x', s
    u = bdd.add_expr('x /\ y')
    s = bdd.to_expr(u)
    assert s == 'ite(x, y, FALSE)', s


def test_dump_load():
    vrs = ['x', 'y', 'z']
    s = 'x \/ y \/ ~ z'
    fname = 'foo.p'
    # dump
    bdd = _bdd.BDD()
    bdd.declare(*vrs)
    u = bdd.add_expr(s)
    bdd.dump(fname, roots=[u])
    # load
    other = _bdd.BDD()
    umap = other.load(fname)
    assert len(umap) == 3, umap


def test_image():
    bdd = _bdd.BDD()
    bdd.declare('x', 'y', 'z')
    action = bdd.add_expr('x => y')
    source = bdd.add_expr('x')
    qvars = {'x'}
    rename = dict(y='x')
    u = _bdd.image(action, source, rename, qvars)
    u_ = bdd.add_expr('x')
    assert u == u_


def test_preimage():
    bdd = _bdd.BDD()
    bdd.declare('x', 'y', 'z')
    action = bdd.add_expr('x <=> y')
    target = bdd.add_expr('x')
    qvars = {'y'}
    rename = dict(x='y')
    u = _bdd.preimage(action, target, rename, qvars)
    u_ = bdd.add_expr('x')
    assert u == u_


def test_reorder():
    bdd = _bdd.BDD()
    bdd.declare('x', 'y', 'z')
    u = bdd.add_expr('(x /\ y) \/ z')
    bdd.reorder()
    assert u in bdd


def test_reorder_2():
    bdd = _bdd.BDD()
    vrs = [
        'x', 'y', 'z', 'a', 'b', 'c', 'e',
        'z1', 'z2', 'z3', 'y1', 'y2', 'y3']
    bdd = _bdd.BDD()
    bdd.declare(*vrs)
    expr_1 = '(~ z \/ (c /\ b)) /\ e /\ (a /\ (~ x \/ y))'
    # Figs. 6.24, 6.25 Baier 2008
    expr_2 = '(z1 /\ y1) \/ (z2 /\ y2) \/ (z3 /\ y3)'
    u = bdd.add_expr(expr_1)
    v = bdd.add_expr(expr_2)
    bdd.collect_garbage()
    n = len(bdd)
    assert n == 23, n
    bdd.reorder()
    n_ = len(bdd)
    assert n > n_, (n, n_)
    bdd.assert_consistent()


def test_configure_dynamic_reordering():
    bdd = _bdd.BDD()
    vrs = [
        'x', 'y', 'z', 'a', 'b', 'c', 'e',
        'z1', 'z2', 'z3', 'y1', 'y2', 'y3']
    expr_1 = '(~ z \/ (c /\ b)) /\ e /\ (a /\ (~ x \/ y))'
    expr_2 = '(z1 /\ y1) \/ (z2 /\ y2) \/ (z3 /\ y3)'
    # w/o dynamic reordering
    bdd = _bdd.BDD()
    bdd.declare(*vrs)
    u = bdd.add_expr(expr_1)
    v = bdd.add_expr(expr_2)
    bdd.collect_garbage()
    n = len(bdd)
    assert n == 23, n
    # with dynamic reordering
    del u, v, bdd
    dd.bdd.REORDER_STARTS = 7
    bdd = _bdd.BDD()
    bdd.declare(*vrs)
    bdd.configure(reordering=True)
    u = bdd.add_expr(expr_1)
    v = bdd.add_expr(expr_2)
    bdd.collect_garbage()
    n = len(bdd)
    assert n < 23, n


def test_collect_garbage():
    bdd = _bdd.BDD()
    n = len(bdd)
    assert n == 1, n
    bdd.declare('x', 'y')
    u = bdd.add_expr('x \/ y')
    bdd.collect_garbage()
    n = len(bdd)
    assert n > 1, n
    del u
    bdd.collect_garbage()
    n = len(bdd)
    assert n == 1, n


def test_copy_vars():
    bdd = _bdd.BDD()
    other = _bdd.BDD()
    vrs = {'x', 'y', 'z'}
    bdd.declare(*vrs)
    _bdd.copy_vars(bdd, other)
    assert vrs.issubset(other.vars)


def test_copy_bdd():
    bdd = _bdd.BDD()
    other = _bdd.BDD()
    bdd.declare('x')
    other.declare('x')
    u = bdd.var('x')
    v = _bdd.copy_bdd(u, other)
    v_ = other.var('x')
    assert v == v_, other.to_expr(v)
    # involution
    u_ = _bdd.copy_bdd(v, bdd)
    assert u == u_, bdd.to_expr(u_)


def test_node_hash():
    bdd = _bdd.BDD()
    bdd.declare('z')
    u = bdd.add_expr('z')
    n = hash(u)
    m = hash(bdd.true)
    assert n != m, (n, m)


def test_add_int():
    bdd = _bdd.BDD()
    bdd.declare('x', 'y')
    u = bdd.add_expr('x \/ ~ y')
    node_id = int(u)
    u_ = bdd._add_int(node_id)
    assert u == u_, (u, u_)
    id2 = int(u_)
    assert node_id == id2, (node_id, id2)
    # test string form
    node_str = str(u)
    s = '@{nid}'.format(nid=node_id)
    assert node_str == s, (node_str, s)


def test_func_len():
    bdd = _bdd.BDD()
    bdd.declare('x', 'y')
    u = bdd.add_expr('x')
    n = len(u)
    assert n == 2, n
    u = bdd.add_expr('x /\ y')
    n = len(u)
    assert n == 3, n


def test_negated():
    bdd = _bdd.BDD()
    bdd.declare('x')
    u = bdd.add_expr('x')
    neg_u = bdd.add_expr('~ x')
    a = u.negated
    b = neg_u.negated
    assert a or b, (a, b)
    assert not (a and b), (a, b)


def test_comparators():
    bdd = _bdd.BDD()
    # `None`
    assert not (bdd.false == None)
    assert not (bdd.true == None)
    assert bdd.false != None
    assert bdd.true != None
    # constant
    assert bdd.false < bdd.true
    assert bdd.false <= bdd.true
    assert bdd.false != bdd.true
    assert bdd.true >= bdd.false
    assert bdd.true > bdd.false
    assert bdd.true == bdd.true
    assert bdd.false == bdd.false
    # non-constant
    bdd.declare('x')
    u = bdd.add_expr('x')
    # compared to false
    assert u > bdd.false
    assert u >= bdd.false
    assert u != bdd.false
    assert bdd.false <= u
    assert bdd.false < u
    assert u == u
    # compared to true
    assert u < bdd.true
    assert u <= bdd.true
    assert u != bdd.true
    assert bdd.true >= u
    assert bdd.true > u


def test_function_properties():
    bdd = _bdd.BDD()
    bdd.declare('x', 'y')
    order = dict(x=0, y=1)
    bdd.reorder(order)
    u = bdd.add_expr('x \/ y')
    y = bdd.add_expr('y')
    # Assigned first because in presence of a bug
    # different property calls could yield
    # different values.
    level = u.level
    assert level == 0, level
    var = u.var
    assert var == 'x', var
    low = u.low
    assert low == y, low
    high = u.high
    assert high == bdd.true, high
    ref = u.ref
    assert ref == 1, ref
    assert not u.negated
    support = u.support
    assert support == {'x', 'y'}, support
    # terminal
    u = bdd.false
    assert u.var is None, u.var
    assert u.low is None, u.low
    assert u.high is None, u.high


if __name__ == '__main__':
    test_support()
