import logging
from dd.bdd import BDD, preimage
import dd.bdd
import nose.tools as nt
import networkx as nx
import networkx.algorithms.isomorphism as iso


logging.getLogger('tulip.ltl_parser_log').setLevel(logging.ERROR)


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
    u = 2
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
    assert g.is_essential(2, 'y')
    assert g.is_essential(3, 'y')
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
    assert g.support(2) == {'x', 'y'}
    assert g.support(3) == {'y'}
    g = x_or_y()
    assert g.support(2) == {'x', 'y'}
    assert g.support(3) == {'y'}


def test_sat_len():
    g = x_and_y()
    assert g.sat_len(2) == 1
    g = x_or_y()
    assert g.sat_len(2) == 3
    assert g.sat_len(-2) == 1
    with nt.assert_raises(Exception):
        g.sat_len()
    assert g.sat_len(2) == 3


def test_sat_iter():
    # x & y
    g = x_and_y()
    u = 2
    s = [{'x': 1, 'y': 1}]
    compare_iter_to_list_of_sets(u, g, s)
    # x | y
    g = x_or_y()
    u = 2
    s = [{'x': 1}, {'x': 0, 'y': 1}]
    compare_iter_to_list_of_sets(u, g, s)
    # x & !y
    g = x_and_not_y()
    u = -2
    s = [{'x': 1, 'y': 0}]
    compare_iter_to_list_of_sets(u, g, s)


def compare_iter_to_list_of_sets(u, g, s):
    for d in g.sat_iter(u):
        assert d in s
        s.remove(d)
    assert not s


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
    assert ordering == h.ordering

    r = nx.MultiDiGraph()
    r.add_node(1, index=3)
    r.add_node(2, index=0)
    r.add_node(3, index=1)
    r.add_node(4, index=2)

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
    # elimination rule
    i = 0
    v = -1
    w = 1
    n = len(g)
    u = g.find_or_add(i, v, v)
    assert len(g) == n
    assert u == v
    assert not g._pred
    # add new node
    n = len(g)
    u = g.find_or_add(i, v, w)
    assert u != v
    assert len(g) == n + 1
    assert g._succ[u] == (i, -1, 1)
    assert (i, v, w) in g._pred
    # add existing
    r = g.find_or_add(i, v, w)
    assert len(g) == n + 1
    assert u == r
    # only non-terminals can be added
    with nt.assert_raises(AssertionError):
        g.find_or_add(2, -1, 1)
    # low and high must already exist
    with nt.assert_raises(AssertionError):
        g.find_or_add(0, 3, 4)


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

    a = g.add_expr('x && y')
    b = g.add_expr('x || z')
    c = g.compose(a, ordering['y'], b)
    d = g.add_expr('x && (x || z)')
    assert c == d

    ordering = {'x': 0, 'y': 1, 'z': 2, 'w': 3}
    g = BDD(ordering)

    a = g.add_expr('(x && y) || z')
    b = g.add_expr('(y || z) && x')
    c = g.compose(a, ordering['z'], b)
    assert c == b

    ordering = {'x': 0, 'y': 1, 'z': 2, 'w': 3}
    g = BDD(ordering)

    a = g.add_expr('(x && y) || (!z || (w && y && x))')
    b = g.add_expr('(y || z) && x')
    c = g.compose(a, ordering['y'], b)
    d = g.add_expr(
        '(x && ((y || z) && x)) ||'
        ' (!z || (w && ((y || z) && x) && x))')
    assert c == d


def test_cofactor():
    ordering = {'x': 0, 'y': 1, 'z': 2}
    g = BDD(ordering)

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


def test_quantify():
    ordering = {'x': 0, 'y': 1, 'z': 2}
    g = BDD(ordering)

    e = g.add_expr('x && y')
    x = g.add_expr('x')
    y = g.add_expr('y')
    assert g.quantify(e, {'x'}) == y
    assert g.quantify(e, {'x'}, forall=True) == -1
    assert g.quantify(e, {'y'}) == x
    assert g.quantify(e, {'x'}, forall=True) == -1

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


def test_rename():
    ordering = {'x': 0, 'xp': 1}
    g = BDD(ordering)
    x = g.add_expr('x')
    xp = g.add_expr('xp')
    dvars = {'x': 'xp'}
    xrenamed = dd.bdd.rename(x, g, dvars)
    assert xrenamed == xp, xrenamed
    ordering = {'x': 0, 'xp': 1,
                'y': 2, 'yp': 3,
                'z': 4, 'zp': 5}
    g = BDD(ordering)
    u = g.add_expr('x && y && z')
    dvars = {'x': 'xp', 'y': 'yp', 'z': 'zp'}
    urenamed = dd.bdd.rename(u, g, dvars)
    up = g.add_expr('xp && yp && zp')
    assert urenamed == up, urenamed
    # assertion violations
    # non-neighbors
    dvars = {'x': 'yp'}
    with nt.assert_raises(AssertionError):
        dd.bdd.rename(u, g, dvars)
    # u not in bdd
    dvars = {'x': 'xp'}
    with nt.assert_raises(AssertionError):
        dd.bdd.rename(15, g, dvars)
    # y essential for u
    dvars = {'xp': 'y'}
    with nt.assert_raises(AssertionError):
        dd.bdd.rename(u, g, dvars)
    # old and new vars intersect
    dvars = {'x': 'x'}
    with nt.assert_raises(AssertionError):
        dd.bdd.rename(u, g, dvars)


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
    for i in xrange(4):
        f = preimage(t, f, rename, qvars, g)
    end = f
    assert start == end

    # forall z exists x, y
    t = g.add_expr(
        '('
        '    ((x & y) -> (zp & xp & !yp)) | '
        '    ((x & y) -> (!zp & !xp & yp))'
        ') & '
        '(!(x & y) -> false)')
    f = g.add_expr('x && !y')
    ep = preimage(t, f, rename, qvars, g)
    p = g.quantify(ep, {'zp'}, forall=True)
    assert p == -1

    f = g.add_expr('(x & !y) | (!x & y)')
    ep = preimage(t, f, rename, qvars, g)
    p = g.quantify(ep, {'zp'}, forall=True)
    assert p == g.add_expr('x & y')


def test_to_pydot():
    g = x_and_y()
    g.roots.add(2)
    pd = dd.bdd.to_pydot(g)
    r = nx.from_pydot(pd)
    f = lambda x: str(abs(x))
    for u in g:
        assert f(u) in r, u
    for u, (i, v, w) in g._succ.iteritems():
        if v is None or w is None:
            assert v is None, v
            assert w is None, w
            continue
        assert r.has_edge(f(u), f(v)), (u, v)
        assert r.has_edge(f(u), f(w)), (u, w)


def x_or_y():
    g = two_vars_xy()
    g._succ[2] = (0, 3, 1)
    return g


def x_and_y():
    g = two_vars_xy()
    g._succ[2] = (0, -1, 3)
    return g


def two_vars_xy():
    ordering = {'x': 0, 'y': 1}
    g = BDD(ordering)
    g._succ[2] = (0, -1, 1)
    g._succ[3] = (1, -1, 1)
    return g


def x_and_not_y():
    # remember:
    # 2 = !(x & !y)
    # -2 = x & !y
    ordering = {'x': 0, 'y': 1}
    g = BDD(ordering)
    g._succ[2] = (0, 1, 3)
    g._succ[3] = (1, -1, 1)
    return g


def ref_var(i):
    h = nx.MultiDiGraph()
    h.add_node(1, index=2)
    h.add_node(2, index=i)
    h.add_edge(2, 1, value=False, complement=True)
    h.add_edge(2, 1, value=True, complement=False)
    return h


def ref_x_and_y():
    h = nx.MultiDiGraph()
    h.add_node(1, index=2)
    h.add_node(2, index=0)
    h.add_node(3, index=1)
    h.add_edge(2, 1, value=False, complement=True)
    h.add_edge(2, 3, value=True, complement=False)
    h.add_edge(3, 1, value=False, complement=True)
    h.add_edge(3, 1, value=True, complement=False)
    return h


def ref_x_or_y():
    h = nx.MultiDiGraph()
    h.add_node(1, index=2)
    h.add_node(2, index=0)
    h.add_node(3, index=1)
    h.add_edge(2, 3, value=False, complement=False)
    h.add_edge(2, 1, value=True, complement=False)
    h.add_edge(3, 1, value=False, complement=True)
    h.add_edge(3, 1, value=True, complement=False)
    return h


def compare(u, bdd, h):
    g = dd.bdd.to_nx(bdd, [u])
    nx.to_pydot(g).write_pdf('g.pdf')
    post = nx.descendants(g, u)
    post.add(u)
    r = g.subgraph(post)
    # nx.to_pydot(r).write_pdf('g.pdf')
    # nx.to_pydot(r).write_pdf('r.pdf')
    # nx.to_pydot(h).write_pdf('h.pdf')
    nm = lambda x, y: x['index'] == y['index']
    em = lambda x, y: (
        bool(x[0]['value']) == bool(y[0]['value']) and
        bool(x[0]['complement']) == bool(y[0]['complement']))
    gm = iso.GraphMatcher(r, h, node_match=nm, edge_match=em)
    assert gm.is_isomorphic()
    d = gm.mapping
    assert d[1] == 1


if __name__ == '__main__':
    test_ite()
