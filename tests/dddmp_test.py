import logging
import time
from dd import dddmp
import networkx as nx


logging.getLogger('dd.dddmp.parser_logger').setLevel(logging.ERROR)
parser = dddmp.Parser()


def test_sample0():
    fname = 'sample0.txt'
    bdd, n_vars, ordering, roots = parser.parse(fname)
    h = to_nx(bdd, n_vars, ordering, roots)
    assert len(h) == 5, len(h)
    edges = {
        (5, 3, 0), (5, 4, 0),
        (4, 1, 0), (4, 2, 0),
        (3, 1, 0), (3, 2, 0),
        (2, 1, 0), (2, 1, 1)}
    assert set(h.edges_iter(keys=True)) == edges
    # complemented edges
    assert h[4][2][0]['label'] == '-1'
    assert h[2][1][0]['label'] == '-1'
    # other attributes
    assert n_vars == 50, n_vars
    assert ordering == {'a': 1, 'b': 2, 'c': 3}, ordering
    assert roots == {-5}
    # pd = nx.to_pydot(h)
    # pd.write_pdf('bdd.pdf')


def test_sample1():
    fname = 'sample1.txt'
    parser.build(debug=True)
    bdd, n_vars, ordering, roots = parser.parse(fname)
    assert len(bdd) == 16, len(bdd)
    assert n_vars == 10, n_vars
    assert roots == {6, -13, -16}, roots


def test_bdd_from_dddmp():
    fname = 'sample0.txt'
    bdd = dddmp.load_bdd(fname)
    print bdd


def load_bdd_2_masters():
    fname = 'bdd_16_masters.txt'
    t0 = time.time()
    bdd, n, ordering, roots = parser.parse(fname)
    t1 = time.time()
    print('finished: {t}'.format(t=t1 - t0))
    print(len(bdd))


def to_nx(bdd, n_vars, ordering, roots):
    level2var = {k: v for v, k in ordering.iteritems()}
    level2var[n_vars + 1] = 'T'
    h = nx.MultiDiGraph()
    h.roots = roots
    for u, (i, v, w) in bdd.iteritems():
        assert u >= 0, u
        label = level2var[i]
        h.add_node(u, label=label)
        # terminal ?
        if v is None or w is None:
            assert v is None
            assert w is None
            continue
        complemented = '-1' if v < 0 else ' '
        h.add_edge(u, abs(v), label=complemented, style='dashed')
        assert w >= 0, w  # "then" edge cannot be complemented
        h.add_edge(u, w)
    return h


if __name__ == '__main__':
    test_bdd_from_dddmp()
