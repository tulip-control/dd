import logging
from dd.bdd import BDD, preimage
from dd import autoref
from dd import bdd as _bdd
import nose.tools as nt
import networkx as nx
import networkx.algorithms.isomorphism as iso


def test_add_var():
    b = BDD()
    #
    # automated level selection
    # first var
    j = b.add_var('x')
    assert len(b.vars) == 1, b.vars
    assert 'x' in b.vars, b.vars
    assert b.vars['x'] == 0, b.vars
    assert j == 0, j
    # second var
    j = b.add_var('y')
    assert len(b.vars) == 2, b.vars
    assert 'y' in b.vars, b.vars
    assert b.vars['y'] == 1, b.vars
    assert j == 1, j
    # third var
    j = b.add_var('z')
    assert len(b.vars) == 3, b.vars
    assert 'z' in b.vars, b.vars
    assert b.vars['z'] == 2, b.vars
    assert j == 2, j
    #
    # explicit level selection
    b = BDD()
    j = b.add_var('x', level=35)
    assert len(b.vars) == 1, b.vars
    assert 'x' in b.vars, b.vars
    assert b.vars['x'] == 35, b.vars
    assert j == 35, j
    j = b.add_var('y', level=5)
    assert len(b.vars) == 2, b.vars
    assert 'y' in b.vars, b.vars
    assert b.vars['y'] == 5, b.vars
    assert j == 5, j
    # attempt to add var at an existing level
    with nt.assert_raises(AssertionError):
        b.add_var('z', level=35)
    with nt.assert_raises(AssertionError):
        b.add_var('z', level=5)
    #
    # mixing automated and
    # explicit level selection
    b = BDD()
    b.add_var('x', level=2)
    b.add_var('y')
    assert len(b.vars) == 2, b.vars
    assert 'x' in b.vars, b.vars
    assert 'y' in b.vars, b.vars
    assert b.vars['x'] == 2, b.vars
    assert b.vars['y'] == 1, b.vars
    with nt.assert_raises(AssertionError):
        b.add_var('z')
    b.add_var('z', level=0)


def test_var():
    b = BDD()
    with nt.assert_raises(AssertionError):
        b.var('x')
    j = b.add_var('x')
    u = b.var('x')
    assert u > 0, u
    level, low, high = b.succ(u)
    assert level == j, (level, j)
    assert low == b.false, low
    assert high == b.true, high


def test_assert_consistent():
    g = two_vars_xy()
    assert g.assert_consistent()
    g = x_or_y()
    assert g.assert_consistent()
    g._succ[2] = (5, 1, 2)
    with nt.assert_raises(AssertionError):
        g.assert_consistent()
    g = x_or_y()
    g.roots.add(2)
    g._succ[4] = (0, 10, 1)
    with nt.assert_raises(AssertionError):
        g.assert_consistent()
    g = x_or_y()
    g.roots.add(2)
    g._succ[1] = (2, None, 1)
    with nt.assert_raises(AssertionError):
        g.assert_consistent()
    g = x_and_y()
    assert g.assert_consistent()


def test_level_to_variable():
    ordering = {'x': 0, 'y': 1}
    g = BDD(ordering)
    assert g.var_at_level(0) == 'x'
    assert g.var_at_level(1) == 'y'
    with nt.assert_raises(AssertionError):
        g.var_at_level(10)


def test_descendants():
    ordering = dict(x=0, y=1)
    b = BDD(ordering)
    u = b.add_expr('x && y')
    v = b.add_expr('x | y')
    roots = [u, v]
    nodes = b.descendants(roots)
    nodes_u = b.descendants([u])
    nodes_v = b.descendants([v])
    assert u in nodes_u, nodes_u
    assert v in nodes_v, nodes_v
    assert u in nodes, nodes
    assert v in nodes, nodes
    assert 1 in nodes_u, nodes_u
    assert 1 in nodes_v, nodes_v
    assert 1 in nodes, nodes
    assert len(nodes_u) == 3, nodes_u
    assert len(nodes_v) == 3, nodes_v
    assert nodes_u != nodes_v, (nodes_u, nodes_v)
    assert len(nodes) == 4, nodes
    assert nodes == nodes_u.union(nodes_v), (
        nodes, b._succ)
    # no roots
    roots = []
    nodes = b.descendants(roots)
    assert len(nodes) == 0, nodes


def test_evaluate():
    # x, y
    g = two_vars_xy()
    u = 2
    assert g.evaluate(u, {'x': 1}) == 1
    assert g.evaluate(u, {'x': 0}) == -1
    u = 3
    assert g.evaluate(u, {'y': 1}) == 1
    assert g.evaluate(u, {'y': 0}) == -1
    # x & y
    g = x_and_y()
    u = 4
    # missing value for y
    with nt.assert_raises(KeyError):
        g.evaluate(u, {'x': 1})
    assert g.evaluate(u, {'x': 0, 'y': 0}) == -1
    assert g.evaluate(u, {'x': 0, 'y': 1}) == -1
    assert g.evaluate(u, {'x': 1, 'y': 0}) == -1
    assert g.evaluate(u, {'x': 1, 'y': 1}) == 1
    # x & !y
    g = x_and_not_y()
    u = -2
    assert g.evaluate(u, {'x': 0, 'y': 0}) == -1
    assert g.evaluate(u, {'x': 0, 'y': 1}) == -1
    assert g.evaluate(u, {'x': 1, 'y': 0}) == 1
    assert g.evaluate(u, {'x': 1, 'y': 1}) == -1
    # !(x & !y) = !x | y
    u = 2
    assert g.evaluate(u, {'x': 0, 'y': 0}) == 1
    assert g.evaluate(u, {'x': 0, 'y': 1}) == 1
    assert g.evaluate(u, {'x': 1, 'y': 0}) == -1
    assert g.evaluate(u, {'x': 1, 'y': 1}) == 1


def test_is_essential():
    g = two_vars_xy()
    assert g.is_essential(2, 'x')
    assert not g.is_essential(2, 'y')
    assert g.is_essential(3, 'y')
    assert not g.is_essential(3, 'x')
    g = x_and_y()
    assert g.is_essential(2, 'x')
    assert g.is_essential(3, 'y')
    assert g.is_essential(4, 'x')
    assert g.is_essential(4, 'y')
    assert not g.is_essential(3, 'x')
    assert not g.is_essential(-1, 'x')
    assert not g.is_essential(-1, 'y')
    assert not g.is_essential(1, 'x')
    assert not g.is_essential(1, 'y')
    # variable not in the ordering
    assert not g.is_essential(2, 'z')


def test_support():
    g = two_vars_xy()
    assert g.support(2) == {'x'}
    assert g.support(3) == {'y'}
    g = x_and_y()
    assert g.support(4) == {'x', 'y'}
    assert g.support(3) == {'y'}
    g = x_or_y()
    assert g.support(4) == {'x', 'y'}
    assert g.support(3) == {'y'}


def test_sat_len():
    g = x_and_y()
    assert g.sat_len(4) == 1
    g = x_or_y()
    r = g.sat_len(4)
    assert r == 3, r
    r = g.sat_len(4, n=2)
    assert r == 3, r
    r = g.sat_len(-4)
    assert r == 1, r
    r = g.sat_len(-4, n=2)
    assert r == 1, r
    r = g.sat_len(4, 3)
    assert r == 6, r
    r = g.sat_len(-4, 3)
    assert r == 2, r
    with nt.assert_raises(Exception):
        g.sat_len()
    r = g.sat_len(4)
    assert r == 3, r
    g = _bdd.BDD()
    g.add_var('x')
    g.add_var('y')
    u = g.add_expr('x & y ')
    r = g.sat_len(u)
    assert r == 1, r


def test_sat_iter():
    # x & y
    g = x_and_y()
    u = 4
    bits = {'x', 'y'}
    s = [{'x': 1, 'y': 1}]
    compare_iter_to_list_of_sets(u, g, s, bits)
    # care_bits == support (default)
    bits = None
    compare_iter_to_list_of_sets(u, g, s, bits)
    #
    # x | y
    g = x_or_y()
    u = 4
    # support
    bits = None
    s = [{'x': 1, 'y': 0}, {'x': 1, 'y': 1},
         {'x': 0, 'y': 1}]
    compare_iter_to_list_of_sets(u, g, s, bits)
    # only what appears along traversal
    bits = set()
    s = [{'x': 1}, {'x': 0, 'y': 1}]
    compare_iter_to_list_of_sets(u, g, s, bits)
    # bits < support
    bits = {'x'}
    s = [{'x': 1}, {'x': 0, 'y': 1}]
    compare_iter_to_list_of_sets(u, g, s, bits)
    bits = {'y'}
    s = [{'x': 1, 'y': 0},{'x': 1, 'y': 1},
         {'x': 0, 'y': 1}]
    compare_iter_to_list_of_sets(u, g, s, bits)
    #
    # x & !y
    g = x_and_not_y()
    u = -2
    bits = {'x', 'y'}
    s = [{'x': 1, 'y': 0}]
    compare_iter_to_list_of_sets(u, g, s, bits)
    # gaps in order
    order = {'x': 0, 'y': 1, 'z': 2}
    bdd = BDD(order)
    u = bdd.add_expr('x & z')
    (m,) = bdd.sat_iter(u)
    assert m == {'x': 1, 'z': 1}, m


def compare_iter_to_list_of_sets(u, g, s, care_bits):
    s = list(s)
    for d in g.sat_iter(u, care_bits):
        assert d in s, d
        s.remove(d)
    assert not s, s


def test_enumerate_minterms():
    # non-empty cube
    cube = dict(x=False)
    bits = ['x', 'y', 'z']
    r = _bdd._enumerate_minterms(cube, bits)
    p = set_from_generator_of_dict(r)
    q = set()
    for y in (False, True):
        for z in (False, True):
            m = (('x', False), ('y', y), ('z', z))
            q.add(m)
    assert p == q, (p, q)
    # empty cube
    cube = dict()
    bits = ['x', 'y', 'z']
    r = _bdd._enumerate_minterms(cube, bits)
    p = set_from_generator_of_dict(r)
    q = set()
    for x in (False, True):
        for y in (False, True):
            for z in (False, True):
                m = (('x', x), ('y', y), ('z', z))
                q.add(m)
    assert p == q, (p, q)
    # fewer bits than cube
    cube = dict(x=False, y=True)
    bits = set()
    r = _bdd._enumerate_minterms(cube, bits)
    p = set_from_generator_of_dict(r)
    q = {(('x', False), ('y', True))}
    assert p == q, (p, q)


def set_from_generator_of_dict(gen):
    r = list(gen)
    p = {tuple(sorted(m.items(), key=lambda x: x[0]))
         for m in r}
    return p


def test_isomorphism():
    ordering = {'x': 0}
    g = BDD(ordering)
    g.roots.update([2, 3])
    g._succ[2] = (0, -1, 1)
    g._succ[3] = (0, -1, 1)
    h = g.reduction()
    assert set(h) == {1, 2}, set(h)
    assert 0 not in h
    assert h._succ[1] == (1, None, None)
    assert h._succ[2] == (0, -1, 1)
    assert h.roots == {2}


def test_elimination():
    ordering = {'x': 0, 'y': 1}
    g = BDD(ordering)
    g.roots.add(2)
    # high == low, so node 2 is redundant
    g._succ[2] = (0, 3, 3)
    g._succ[3] = (1, -1, 1)
    h = g.reduction()
    assert set(h) == {1, 2}


def test_reduce_combined():
    """Fig.5 in 1986 Bryant TOC"""
    ordering = {'x': 0, 'y': 1, 'z': 2}
    g = BDD(ordering)
    g.roots.add(2)
    g._succ[2] = (0, 3, 4)
    g._succ[3] = (1, -1, 5)
    g._succ[4] = (1, 5, 6)
    g._succ[5] = (2, -1, 1)
    g._succ[6] = (2, -1, 1)
    h = g.reduction()
    assert 1 in h
    assert ordering == h.vars

    r = nx.MultiDiGraph()
    r.add_node(1, level=3)
    r.add_node(2, level=0)
    r.add_node(3, level=1)
    r.add_node(4, level=2)

    r.add_edge(2, 3, value=False, complement=False)
    r.add_edge(2, 4, value=True, complement=False)
    r.add_edge(3, 4, value=True, complement=False)
    r.add_edge(3, 1, value=False, complement=True)
    r.add_edge(4, 1, value=False, complement=True)
    r.add_edge(4, 1, value=True, complement=False)

    (u, ) = h.roots
    compare(u, h, r)
    # r.write('r.pdf')
    # h.write('h.pdf')


def test_find_or_add():
    ordering = {'x': 0, 'y': 1}
    g = BDD(ordering)
    # init
    n = len(g)
    m = g._min_free
    assert n == 1, n
    assert m == 2, m
    # elimination rule
    i = 0
    v = -1
    w = 1
    n = len(g)
    u = g.find_or_add(i, v, v)
    n_ = len(g)
    assert n == n_, (n, n_)
    assert u == v, (u, v)
    assert len(g._pred) == 1, g._pred
    t = (2, None, None)
    assert t in g._pred, g._pred
    assert g._pred[t] == 1, g._pred
    # unchanged min_free
    v = 1
    m = g._min_free
    g.find_or_add(i, v, v)
    m_ = g._min_free
    assert m_ == m, (m_, m)
    # add new node
    g = BDD(ordering)
    v = -1
    w = 1
    n = len(g)
    m = g._min_free
    assert n == 1, n
    u = g.find_or_add(i, v, w)
    n_ = len(g)
    m_ = g._min_free
    assert u != v, (u, v)
    assert n_ == n + 1, (n, n_)
    assert m_ == m + 1, (m, m_)
    assert g._succ[u] == (i, -1, 1)
    assert (i, v, w) in g._pred
    assert abs(u) in g._ref
    assert g._ref[abs(u)] == 0
    # terminal node `v`: 2 refs + 1 ref by manager
    assert g._ref[abs(v)] == 3, g._ref
    # independent increase of reference counters
    v = u
    w = w
    refv = g._ref[abs(v)]
    refw = g._ref[w]
    u = g.find_or_add(i, v, w)
    refv_ = g._ref[abs(v)]
    refw_ = g._ref[w]
    assert refv + 1 == refv_, (refv, refv_)
    assert refw + 1 == refw_, (refw, refw_)
    # add existing
    n = len(g)
    m = g._min_free
    refv = g._ref[abs(v)]
    refw = g._ref[w]
    r = g.find_or_add(i, v, w)
    n_ = len(g)
    m_ = g._min_free
    refv_ = g._ref[abs(v)]
    refw_ = g._ref[w]
    assert n == n_, (n, n_)
    assert m == m_, (m, m_)
    assert u == r, u
    assert refv == refv_, (refv, refv_)
    assert refw == refw_, (refw, refw_)
    # only non-terminals can be added
    with nt.assert_raises(AssertionError):
        g.find_or_add(2, -1, 1)
    # low and high must already exist
    with nt.assert_raises(AssertionError):
        g.find_or_add(0, 3, 4)
    # canonicity of complemented edges
    # v < 0, w > 0
    g = BDD(ordering)
    i = 0
    v = -1
    w = 1
    u = g.find_or_add(i, v, w)
    assert u > 0, u
    # v > 0, w < 0
    v = 1
    w = -1
    u = g.find_or_add(i, v, w)
    assert u < 0, u
    assert abs(u) in g._succ, u
    _, v, w = g._succ[abs(u)]
    assert v < 0, v
    assert w > 0, w
    # v < 0, w < 0
    v = -1
    w = -2
    u = g.find_or_add(i, v, w)
    assert u < 0, u
    _, v, w = g._succ[abs(u)]
    assert v > 0, v
    assert w > 0, w


def test_next_free_int():
    g = BDD()
    # contiguous
    g._succ = {1, 2, 3}
    n = g._next_free_int(start=1, debug=True)
    assert n == 4, n
    n = g._next_free_int(start=3, debug=True)
    assert n == 4, n
    # with blanks
    g._succ = {1, 3}
    n = g._next_free_int(start=1, debug=True)
    assert n == 2, n
    n = g._next_free_int(start=3)
    assert n == 4, n
    # full
    g._succ = {1, 2, 3}
    g.max_nodes = 3
    with nt.assert_raises(Exception):
        g._next_free_int(start=1)


def test_collect_garbage():
    # all nodes are garbage
    g = BDD({'x': 0, 'y': 1})
    u = g.add_expr('x & y')
    n = len(g)
    assert n == 4, n
    uref = g._ref[abs(u)]
    assert uref == 0, uref
    _, v, w = g._succ[abs(u)]
    vref = g._ref[abs(v)]
    wref = g._ref[w]
    # terminal node `v`: 6 refs + 1 ref by manager
    assert vref == 6, vref
    assert wref == 1, wref
    g.collect_garbage()
    n = len(g)
    assert n == 1, n
    assert u not in g, g._succ
    assert w not in g, g._succ
    # some nodes not garbage
    # projection of x is garbage
    g = BDD({'x': 0, 'y': 1})
    u = g.add_expr('x & y')
    n = len(g)
    assert n == 4, n
    g._ref[abs(u)] += 1
    uref = g._ref[abs(u)]
    assert uref == 1, uref
    g.collect_garbage()
    n = len(g)
    assert n == 3, n


def test_top_cofactor():
    ordering = {'x': 0, 'y': 1}
    g = BDD(ordering)
    x = ordering['x']
    y = ordering['y']
    u = g.find_or_add(y, -1, 1)
    assert g._top_cofactor(u, x) == (u, u)
    assert g._top_cofactor(u, y) == (-1, 1)
    u = g.find_or_add(x, -1, 1)
    assert g._top_cofactor(u, x) == (-1, 1)
    assert g._top_cofactor(-u, x) == (1, -1)


def test_ite():
    ordering = {'x': 0, 'y': 1}
    g = BDD(ordering)
    # x
    ix = ordering['x']
    x = g.find_or_add(ix, -1, 1)
    h = ref_var(ix)
    compare(x, g, h)
    # y
    iy = ordering['y']
    y = g.find_or_add(iy, -1, 1)
    h = ref_var(iy)
    compare(y, g, h)
    # x and y
    u = g.ite(x, y, -1)
    h = ref_x_and_y()
    compare(u, g, h)
    # x or y
    u = g.ite(x, 1, y)
    h = ref_x_or_y()
    compare(u, g, h)
    # negation
    assert g.ite(x, -1, 1) == -x, g._succ
    assert g.ite(-x, -1, 1) == x, g._succ


def test_add_expr():
    ordering = {'x': 0, 'y': 1}
    g = BDD(ordering)
    # x
    ix = ordering['x']
    u = g.add_expr('x')
    h = ref_var(ix)
    compare(u, g, h)
    # x and y
    u = g.add_expr('x && y')
    h = ref_x_and_y()
    compare(u, g, h)


def test_compose():
    ordering = {'x': 0, 'y': 1, 'z': 2}
    g = BDD(ordering)
    # x & (x | z)
    a = g.add_expr('x && y')
    b = g.add_expr('x || z')
    c = g.compose(a, 'y', b)
    d = g.add_expr('x && (x || z)')
    assert c == d, (c, d)
    # (y | z) & x
    ordering = {'x': 0, 'y': 1, 'z': 2, 'w': 3}
    g = BDD(ordering)
    a = g.add_expr('(x && y) || z')
    b = g.add_expr('(y || z) && x')
    c = g.compose(a, 'z', b)
    assert c == b, (c, b)
    # long expr
    ordering = {'x': 0, 'y': 1, 'z': 2, 'w': 3}
    g = BDD(ordering)
    a = g.add_expr('(x && y) || (!z || (w && y && x))')
    b = g.add_expr('(y || !z) && x')
    c = g.compose(a, 'y', b)
    d = g.add_expr(
        '(x && ((y || !z) && x)) ||'
        ' (!z || (w && ((y || !z) && x) && x))')
    assert c == d, (c, d)
    # complemented edges
    ordering = {'x': 0, 'y': 1}
    g = BDD(ordering)
    f = g.add_expr('x <-> y')
    var = 'y'
    new_level = 0
    var_node = g.find_or_add(new_level, -1, 1)
    u = g.compose(f, var, var_node)
    assert u == 1, g.to_expr(u)


def test_cofactor():
    ordering = {'x': 0, 'y': 1, 'z': 2}
    g = BDD(ordering)
    # u not in g
    with nt.assert_raises(AssertionError):
        g.cofactor(5, {'x': 0, 'y': 1, 'z': 0})
    # x & y
    e = g.add_expr('x && y')
    x = g.add_expr('x')
    assert g.cofactor(x, {'x': 0}) == -1
    assert g.cofactor(x, {'x': 1}) == 1
    assert g.cofactor(-x, {'x': 0}) == 1
    assert g.cofactor(-x, {'x': 1}) == -1
    y = g.add_expr('y')
    assert g.cofactor(e, {'x': 1}) == y
    assert g.cofactor(e, {'x': 0}) == -1
    assert g.cofactor(e, {'y': 1}) == x
    assert g.cofactor(e, {'y': 0}) == -1

    assert g.cofactor(-e, {'x': 0}) == 1
    assert g.cofactor(-e, {'x': 1}) == -y
    assert g.cofactor(-e, {'y': 0}) == 1
    assert g.cofactor(-e, {'y': 1}) == -x


def test_swap():
    # x, y
    g = BDD({'x': 0, 'y': 1})
    x = g.add_expr('x')
    y = g.add_expr('y')
    g.incref(x)
    g.incref(y)
    n = len(g)
    assert n == 3, n
    nold, n = g.swap('x', 'y')
    assert n == 3, n
    assert nold == n, nold
    assert g.vars == {'y': 0, 'x': 1}, g.vars
    assert g.assert_consistent()
    # functions remain invariant
    x_ = g.add_expr('x')
    y_ = g.add_expr('y')
    assert x == x_, (x, x_, g._succ)
    assert y == y_, (y, y_, g._succ)
    # external reference counts remain unchanged
    assert g._ref[abs(x)] == 1
    assert g._ref[abs(y)] == 1
    # x & y
    g = BDD({'x': 0, 'y': 1})
    u = g.add_expr('x & y')
    g.incref(u)
    nold, n = g.swap('x', 'y')
    assert nold == n, (nold, n)
    assert g.vars == {'y': 0, 'x': 1}, g.vars
    u_ = g.add_expr('x & y')
    assert u == u_, (u, u_)
    assert g.assert_consistent()
    # reference counts unchanged
    assert g._ref[abs(u)] == 1
    # x & !y
    # tests handling of complement edges
    e = 'x & !y'
    g = x_and_not_y()
    u = g.add_expr(e)
    g.incref(u)
    g.collect_garbage()
    n = len(g)
    assert n == 3, n
    nold, n = g.swap('x', 'y')
    assert n == 3, n
    assert nold == n, nold
    assert g.vars == {'x': 1, 'y': 0}
    assert g.assert_consistent()
    u_ = g.add_expr(e)
    # function u must have remained unaffected
    assert u_ == u, (u, u_, g._succ)
    # invert swap of:
    # x & !y
    nold, n = g.swap('x', 'y')
    assert n == 3, n
    assert nold == n, nold
    assert g.vars == {'x': 0, 'y': 1}
    assert g.assert_consistent()
    u_ = g.add_expr(e)
    assert u_ == u, (u, u_, g._succ)
    # Figs. 6.24, 6.25 Baier 2008
    g = BDD({'z1': 0, 'y1': 1, 'z2': 2,
             'y2': 3, 'z3': 4, 'y3': 5})
    u = g.add_expr('(z1 & y1) | (z2 & y2) | (z3 & y3)')
    g.incref(u)
    n = len(g)
    assert n == 16, n
    g.collect_garbage()
    n = len(g)
    assert n == 7, n
    # sift to inefficient order
    g.swap('y1', 'z2')  # z1, z2, y1, y2, z3, y3
    g.swap('y2', 'z3')  # z1, z2, y1, z3, y2, y3
    g.swap('y1', 'z3')  # z1, z2, z3, y1, y2, y3
    n = len(g)
    assert n == 15, n
    assert g.assert_consistent()
    new_ordering = {
        'z1': 0, 'z2': 1, 'z3': 2,
        'y1': 3, 'y2': 4, 'y3': 5}
    assert g.vars == new_ordering, g.vars
    u_ = g.add_expr('(z1 & y1) | (z2 & y2) | (z3 & y3)')
    assert u_ == u, (u, u_, g._succ)
    # g.dump('g.pdf')


def test_sifting():
    # Figs. 6.24, 6.25 Baier 2008
    g = BDD({'z1': 0, 'z2': 1, 'z3': 2,
             'y1': 3, 'y2': 4, 'y3': 5})
    u = g.add_expr('(z1 & y1) | (z2 & y2) | (z3 & y3)')
    g.incref(u)
    g.collect_garbage()
    n = len(g)
    assert n == 15, n
    _bdd.reorder(g)
    u_ = g.add_expr('(z1 & y1) | (z2 & y2) | (z3 & y3)')
    g.incref(u)
    g.collect_garbage()
    g.assert_consistent()
    assert u == u_, (u, u_)


def test_request_reordering():
    ctx = Dummy()
    # reordering off
    n = ctx._last_len
    assert n is None, n
    _bdd._request_reordering(ctx)
    # reordering on
    ctx._last_len = 1
    ctx.length = 3  # >= 2 = 2 * _last_len
    # large growth
    with nt.assert_raises(_bdd._NeedsReordering):
        _bdd._request_reordering(ctx)
    ctx._last_len = 2
    ctx.length = 3  # < 4 = 2 * _last_len
    # small growth
    _bdd._request_reordering(ctx)


def test_reordering_context():
    ctx = Dummy()
    # top context
    ctx.assert_(False)
    with _bdd._ReorderingContext(ctx):
        ctx.assert_(True)
        raise _bdd._NeedsReordering()
    ctx.assert_(False)
    # nested context
    ctx._reordering_context = True
    with nt.assert_raises(_bdd._NeedsReordering):
        with _bdd._ReorderingContext(ctx):
            ctx.assert_(True)
            raise _bdd._NeedsReordering()
    ctx.assert_(True)
    # other exception
    ctx._reordering_context = False
    with nt.assert_raises(AssertionError):
        with _bdd._ReorderingContext(ctx):
            ctx.assert_(True)
            raise AssertionError()
    ctx.assert_(False)
    ctx._reordering_context = True
    with nt.assert_raises(Exception):
        with _bdd._ReorderingContext(ctx):
            raise Exception()
    ctx.assert_(True)


class Dummy(object):
    """To test state machine for nesting context."""

    def __init__(self):
        self._reordering_context = False
        self._last_len = None
        self.length = 1

    def __len__(self):
        return self.length

    def assert_(self, value):
        c = self._reordering_context
        assert c is value, c


def test_dynamic_reordering():
    b = TrackReorderings()
    [b.add_var(var) for var in ['x', 'y', 'z', 'a', 'b', 'c', 'e']]
    # add expr with reordering off
    assert not b.reordering_is_on()
    assert b.n_swaps == 0, b.n_swaps
    u = b.add_expr('x /\ y /\ z')
    assert b.n_swaps == 0, b.n_swaps
    b.incref(u)
    n = len(b)
    assert n == 7, n
    # add expr with reordering on
    b._last_len = 6
    assert b.reordering_is_on()
    v = b.add_expr('a /\ b')
    assert b.reordering_is_on()
    assert b.n_swaps == 0, b.n_swaps
    b.incref(v)
    n = len(b)
    assert n == 10, n
    # add an expr that triggers reordering
    assert b.reordering_is_on()
    w = b.add_expr('z \/ (~a /\ x /\ ~y)')
    assert b.reordering_is_on()
    n_swaps = b.n_swaps
    assert n_swaps > 0, n_swaps
    b.incref(w)
    assert u in b, (w, b._succ)
    assert v in b, (v, b._succ)
    assert w in b, (w, b._succ)
    # add another expr that triggers reordering
    old_n_swaps = n_swaps
    assert b.reordering_is_on()
    r = b.add_expr('(~ z \/ (c /\ b)) /\ e /\ (a /\ (~x \/ y))')
    b.add_expr('(e \/ ~ a) /\ x /\ (b \/ ~ y)')
    n_swaps = b.n_swaps
    assert n_swaps > old_n_swaps, (n_swaps, old_n_swaps)
    assert b.reordering_is_on()


class TrackReorderings(_bdd.BDD):
    """To record invocations of reordering."""

    def __init__(self, *arg, **kw):
        self.n_swaps = 0
        super(TrackReorderings, self).__init__(*arg, **kw)

    def swap(self, *arg, **kw):
        self.n_swaps += 1
        return super(TrackReorderings, self).swap(*arg, **kw)

    def reordering_is_on(self):
        d = self.configure()
        r = d['reordering']
        return r is True


def test_dump_load():
    prefix = 'test_dump_load'
    fname = prefix + '.p'
    dvars = dict(x=0, y=1)
    # dump
    b = BDD(dvars)
    e = 'x & !y'
    u_dumped = b.add_expr(e)
    b.dump(fname, [u_dumped])
    b.dump(fname)  # no roots
    # load
    b = BDD(dvars)
    b.add_expr('x | y')
    u_new = b.add_expr(e)
    umap = b.load(fname)
    u_loaded = umap[abs(u_dumped)]
    if u_dumped < 0:
        u_loaded = -u_loaded
    assert u_loaded == u_new, (
        u_dumped, u_loaded, u_new, umap)
    assert b.assert_consistent()


def test_dump_load_manager():
    prefix = 'test_dump_load_manager'
    g = BDD({'x': 0, 'y': 1})
    e = 'x & !y'
    u = g.add_expr(e)
    g.incref(u)
    fname = prefix + '.p'
    g._dump_manager(fname)
    h = g._load_manager(fname)
    assert g.assert_consistent()
    u_ = h.add_expr(e)
    assert u == u_, (u, u_)
    # h.dump(prefix + '.pdf')


def test_quantify():
    ordering = {'x': 0, 'y': 1, 'z': 2}
    g = BDD(ordering)
    # x & y
    e = g.add_expr('x && ! y')
    x = g.add_expr('x')
    not_y = g.add_expr('! y')
    assert g.quantify(e, {'x'}) == not_y
    assert g.quantify(e, {'x'}, forall=True) == -1
    assert g.quantify(e, {'y'}) == x
    assert g.quantify(e, {'x'}, forall=True) == -1
    # x | y | z
    e = g.add_expr('x || y || z')
    xy = g.add_expr('x || y')
    yz = g.add_expr('y || z')
    zx = g.add_expr('z || x')
    assert g.quantify(e, {'x'})
    assert g.quantify(e, {'y'})
    assert g.quantify(e, {'z'})
    assert g.quantify(e, {'z'}, forall=True) == xy
    assert g.quantify(e, {'x'}, forall=True) == yz
    assert g.quantify(e, {'y'}, forall=True) == zx
    # complement edges
    u = -x
    v = g.quantify(u, {'y'}, forall=True)
    assert v == -x, g.to_expr(v)
    # multiple values: test recursion
    e = g.add_expr('x & y & z')
    x = g.add_expr('x')
    r = g.quantify(e, {'y', 'z'})
    assert r == x, r


def test_quantifier_syntax():
    b = BDD()
    [b.add_var(var) for var in ['x', 'y']]
    # constants
    u = b.add_expr('\E x: True')
    assert u == b.true, u
    u = b.add_expr('\E x, y: True')
    assert u == b.true, u
    u = b.add_expr('\E x: False')
    assert u == b.false, u
    u = b.add_expr('\A x: True')
    assert u == b.true, u
    u = b.add_expr('\A x: False')
    assert u == b.false, u
    u = b.add_expr('\A x, y: False')
    assert u == b.false, u
    # variables
    u = b.add_expr('\E x: x')
    assert u == b.true, u
    u = b.add_expr('\A x: x')
    assert u == b.false, u
    u = b.add_expr('\E x, y: x')
    assert u == b.true, u
    u = b.add_expr('\E x, y: y')
    assert u == b.true, u
    u = b.add_expr('\A x: y')
    assert u == b.var('y'), u
    u = b.add_expr('\A x: ! y')
    u_ = b.apply('not', b.var('y'))
    assert u == u_, (u, u_)


def test_rename():
    ordering = {'x': 0, 'xp': 1}
    g = BDD(ordering)
    x = g.add_expr('x')
    xp = g.add_expr('xp')
    dvars = {'x': 'xp'}
    xrenamed = _bdd.rename(x, g, dvars)
    assert xrenamed == xp, xrenamed
    ordering = {'x': 0, 'xp': 1,
                'y': 2, 'yp': 3,
                'z': 4, 'zp': 5}
    g = BDD(ordering)
    u = g.add_expr('x && y && ! z')
    dvars = {'x': 'xp', 'y': 'yp', 'z': 'zp'}
    urenamed = _bdd.rename(u, g, dvars)
    up = g.add_expr('xp && yp && ! zp')
    assert urenamed == up, urenamed
    # assertion violations
    # non-neighbors
    dvars = {'x': 'yp'}
    r = _bdd.rename(u, g, dvars)
    r_ = g.add_expr('yp && y && ! z')
    assert r == r_, (r, r_)
    # u not in bdd
    dvars = {'x': 'xp'}
    with nt.assert_raises(AssertionError):
        _bdd.rename(1000, g, dvars)
    # y essential for u
    dvars = {'xp': 'y'}
    with nt.assert_raises(AssertionError):
        _bdd.rename(u, g, dvars)
    # old and new vars intersect
    dvars = {'x': 'x'}
    with nt.assert_raises(AssertionError):
        _bdd.rename(u, g, dvars)


def test_rename_syntax():
    b = BDD()
    [b.add_var(var) for var in ['x', 'y', 'z', 'w']]
    # single substitution
    u = b.add_expr('\S y / x: True')
    assert u == b.true, u
    u = b.add_expr('\S y / x: False')
    assert u == b.false, u
    u = b.add_expr('\S y / x: x')
    u_ = b.add_expr('y')
    assert u == u_, (u, u_)
    u = b.add_expr('\S y / x: z')
    u_ = b.add_expr('z')
    assert u == u_, (u, u_)
    u = b.add_expr('\S y / x: x & z')
    u_ = b.add_expr('y & z')
    assert u == u_, (u, u_)
    # multiple substitution
    u = b.add_expr('\S y / x,  w / z: x & z')
    u_ = b.add_expr('y & w')
    assert u == u_, (u, u_)
    u = b.add_expr('\S y / x,  w / z: z | ! x')
    u_ = b.add_expr('w | ! y')
    assert u == u_, (u, u_)


def test_image_rename_map_checks():
    ordering = {'x': 0, 'xp': 1,
                'y': 2, 'yp': 3,
                'z': 4, 'zp': 5}
    bdd = BDD(ordering)
    # non-adjacent
    rename = {0: 2, 3: 4}
    qvars = set()
    r = _bdd.image(1, 1, rename, qvars, bdd)
    assert r == 1, r
    r = _bdd.preimage(1, 1, rename, qvars, bdd)
    assert r == 1, r
    # overlapping keys and values
    rename = {0: 1, 1: 2}
    with nt.assert_raises(AssertionError):
        _bdd.image(1, 1, rename, qvars, bdd)
    with nt.assert_raises(AssertionError):
        _bdd.preimage(1, 1, rename, qvars, bdd)
    # may be in support after quantification ?
    trans = bdd.add_expr('x -> xp')
    source = bdd.add_expr('x & y')
    qvars = {0}
    rename = {1: 0, 3: 2}
    with nt.assert_raises(AssertionError):
        _bdd.image(trans, source, rename, qvars, bdd)
    # in support of `target` ?
    qvars = set()
    target = bdd.add_expr('y & yp')
    rename = {2: 3}
    with nt.assert_raises(AssertionError):
        _bdd.preimage(trans, target, rename, qvars, bdd)


def test_preimage():
    # exists: x, y
    # forall: z
    ordering = {'x': 0, 'xp': 1,
                'y': 2, 'yp': 3,
                'z': 4, 'zp': 5}
    rename = {0: 1, 2: 3, 4: 5}
    g = BDD(ordering)
    f = g.add_expr('!x')
    t = g.add_expr('x <-> !xp')
    qvars = {1, 3}
    p = preimage(t, f, rename, qvars, g)
    x = g.add_expr('x')
    assert x == p, (x, p)
    # a cycle
    # (x & y) -> (!x & y) ->
    # (!x & !y) -> (x & !y) -> wrap around
    t = g.add_expr(
        '((x & y) -> (!xp & yp)) && '
        '((!x & y) -> (!xp & !yp)) && '
        '((!x & !y) -> (xp & !yp)) && '
        '((x & !y) -> (xp & yp))')
    f = g.add_expr('x && y')
    p = preimage(t, f, rename, qvars, g)
    assert p == g.add_expr('x & !y')
    f = g.add_expr('x && !y')
    p = preimage(t, f, rename, qvars, g)
    assert p == g.add_expr('!x & !y')
    # backward reachable set
    f = g.add_expr('x & y')
    oldf = None
    while oldf != f:
        p = preimage(t, f, rename, qvars, g)
        oldf = f
        f = g.apply('or', p, oldf)
    assert f == 1
    # go around once
    f = g.add_expr('x & y')
    start = f
    for i in range(4):
        f = preimage(t, f, rename, qvars, g)
    end = f
    assert start == end
    # forall z exists x, y
    t = g.add_expr(
        '('
        '    ((x & y) -> (zp & xp & !yp)) | '
        '    ((x & y) -> (!zp & !xp & yp))'
        ') & '
        '(!(x & y) -> False)')
    f = g.add_expr('x && !y')
    ep = preimage(t, f, rename, qvars, g)
    p = g.quantify(ep, {'zp'}, forall=True)
    assert p == -1
    f = g.add_expr('(x & !y) | (!x & y)')
    ep = preimage(t, f, rename, qvars, g)
    p = g.quantify(ep, {'zp'}, forall=True)
    assert p == g.add_expr('x & y')


def test_assert_valid_ordering():
    ordering = {'x': 0, 'y': 1}
    _bdd._assert_valid_ordering(ordering)
    incorrect_ordering = {'x': 0, 'y': 2}
    with nt.assert_raises(AssertionError):
        _bdd._assert_valid_ordering(incorrect_ordering)


def test_assert_refined_ordering():
    ordering = {'x': 0, 'y': 1}
    new_ordering = {'z': 0, 'x': 1, 'w': 2, 'y': 3}
    _bdd._assert_isomorphic_orders(ordering, new_ordering, ordering)


def test_to_pydot():
    def f(x):
        return str(abs(x))
    # with roots
    g = x_and_y()
    pd = _bdd.to_pydot([4, 2], g)
    r = nx.drawing.nx_pydot.from_pydot(pd)
    for u in g:
        assert f(u) in r, (u, r.nodes())
    for u in g._succ:
        i, v, w = g._succ[u]
        if v is None or w is None:
            assert v is None, v
            assert w is None, w
            continue
        assert r.has_edge(f(u), f(v)), (u, v)
        assert r.has_edge(f(u), f(w)), (u, w)
    # no roots
    pd = _bdd.to_pydot(None, g)
    r = nx.drawing.nx_pydot.from_pydot(pd)
    assert len(r) == 7, r.nodes()  # 3 hidden nodes for levels


def test_function_wrapper():
    levels = dict(x=0, y=1, z=2)
    bdd = autoref.BDD(levels)
    u = bdd.add_expr('x & y')
    assert u.bdd is bdd, (repr(u.bdd), repr(bdd))
    assert abs(u.node) in bdd._bdd, (u.node, bdd._bdd._succ)
    # operators
    x = bdd.add_expr('x')
    z = bdd.add_expr('z')
    v = x.implies(z)
    w = u & ~v
    w_ = bdd.add_expr('(x & y) & !((! x) | z)')
    assert w_ == w, (w_, w)
    r = (u | v) ^ w
    r_ = bdd.add_expr(
        '( (x & y) | ((! x) | z) ) ^'
        '( (x & y) & !((! x) | z) )')
    assert r_ == r, (r_, r)
    p = bdd.add_expr('y')
    q = p.equiv(x)
    q_ = bdd.add_expr('x <-> y')
    assert q_ == q, (q_, q)
    # to_expr
    s = q.to_expr()
    assert s == 'ite(x, y, (! y))', s
    # equality
    p_ = bdd.add_expr('y')
    assert p_ == p, p_
    # decref and collect garbage
    bdd.collect_garbage()
    n = len(bdd)
    assert n > 1, bdd._bdd._ref
    del p
    del q, q_
    del r, r_
    bdd.collect_garbage()
    m = len(bdd)
    assert m > 1, bdd._bdd._ref
    assert m < n, (m, n)
    del u
    del v
    del w, w_
    del x
    del z
    bdd.collect_garbage()
    n = len(bdd)
    assert n == 2, bdd._bdd._ref
    del p_
    bdd.collect_garbage()
    n = len(bdd)
    assert n == 1, bdd._bdd._ref
    # properties
    bdd = autoref.BDD({'x': 0, 'y': 1, 'z': 2})
    u = bdd.add_expr('x | !y')
    assert u.level == 0, u.level
    assert u.var == 'x', u.var
    y = bdd.add_expr('!y')
    assert u.low == y, (u.low.node, y.node)
    assert u.high.node == 1, u.high.node
    assert u.ref == 1, u.ref


def x_or_y():
    g = two_vars_xy()
    u = 4
    t = (0, 3, 1)
    assert_valid_succ_pred(u, t, g)
    g._succ[u] = t
    g._pred[t] = u
    g._ref[u] = 1
    g._min_free = u + 1
    g.assert_consistent()
    return g


def x_and_y():
    g = two_vars_xy()
    u = 4
    t = (0, -1, 3)
    assert_valid_succ_pred(u, t, g)
    g._succ[u] = t
    g._pred[t] = u
    g._ref[u] = 1
    g._min_free = u + 1
    return g


def two_vars_xy():
    ordering = {'x': 0, 'y': 1}
    g = BDD(ordering)
    u = 2
    t = (0, -1, 1)
    assert_valid_succ_pred(u, t, g)
    g._succ[u] = t
    g._pred[t] = u
    g._ref[u] = 1
    u = 3
    t = (1, -1, 1)
    assert_valid_succ_pred(u, t, g)
    g._succ[u] = t
    g._pred[t] = u
    g._ref[u] = 1
    g._min_free = u + 1
    return g


def x_and_not_y():
    # remember:
    # 2 = !(x & !y)
    # -2 = x & !y
    ordering = {'x': 0, 'y': 1}
    g = BDD(ordering)
    u = 3
    v = -1
    w = 1
    t = (1, v, w)
    assert_valid_succ_pred(u, t, g)
    g._succ[u] = t
    g._pred[t] = u
    g._ref[abs(v)] += 1
    g._ref[abs(w)] += 1
    g._ref[abs(u)] = 0
    u = 2
    v = 1
    w = 3
    t = (0, v, w)
    assert_valid_succ_pred(u, t, g)
    g._succ[u] = t
    g._pred[t] = u
    g._ref[abs(v)] += 1
    g._ref[abs(w)] += 1
    g._ref[abs(u)] = 0
    g._min_free = 4
    return g


def assert_valid_succ_pred(u, t, g):
    assert u > 1, u
    assert isinstance(t, tuple), t
    assert len(t) == 3, t
    assert t[0] >= 0, t
    assert u not in g._succ, g._succ
    assert t not in g._pred, g._pred


def ref_var(i):
    h = nx.MultiDiGraph()
    h.add_node(1, level=2)
    h.add_node(2, level=i)
    h.add_edge(2, 1, value=False, complement=True)
    h.add_edge(2, 1, value=True, complement=False)
    return h


def ref_x_and_y():
    h = nx.MultiDiGraph()
    h.add_node(1, level=2)
    h.add_node(2, level=0)
    h.add_node(3, level=1)
    h.add_edge(2, 1, value=False, complement=True)
    h.add_edge(2, 3, value=True, complement=False)
    h.add_edge(3, 1, value=False, complement=True)
    h.add_edge(3, 1, value=True, complement=False)
    return h


def ref_x_or_y():
    h = nx.MultiDiGraph()
    h.add_node(1, level=2)
    h.add_node(2, level=0)
    h.add_node(3, level=1)
    h.add_edge(2, 3, value=False, complement=False)
    h.add_edge(2, 1, value=True, complement=False)
    h.add_edge(3, 1, value=False, complement=True)
    h.add_edge(3, 1, value=True, complement=False)
    return h


def compare(u, bdd, h):
    g = _bdd.to_nx(bdd, [u])
    # nx.drawing.nx_pydot.to_pydot(g).write_pdf('g.pdf')
    post = nx.descendants(g, u)
    post.add(u)
    r = g.subgraph(post)
    # nx.drawing.nx_pydot.to_pydot(r).write_pdf('r.pdf')
    # nx.drawing.nx_pydot.to_pydot(h).write_pdf('h.pdf')
    gm = iso.GraphMatcher(r, h, node_match=_nm, edge_match=_em)
    assert gm.is_isomorphic()
    d = gm.mapping
    assert d[1] == 1


def _nm(x, y):
    return x['level'] == y['level']


def _em(x, y):
    return (
        bool(x[0]['value']) == bool(y[0]['value']) and
        bool(x[0]['complement']) == bool(y[0]['complement']))

if __name__ == '__main__':
    log = logging.getLogger('astutils')
    log.setLevel(logging.ERROR)
    log = logging.getLogger('dd.bdd')
    log.setLevel(logging.INFO)
    log.addHandler(logging.StreamHandler())
    test_dynamic_reordering()
