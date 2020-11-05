import logging
import os
from dd.dddmp import Lexer, Parser, load, _rewrite_tables
import networkx as nx
from nose import tools as nt


logging.getLogger('dd.dddmp.parser_logger').setLevel(logging.ERROR)
parser = Parser()


def test_lexer():
    """
    Return a lexer.

    Args:
    """
    lexer = Lexer()
    s = '.ghs?5'
    lexer.lexer.input(s)
    tok = lexer.lexer.token()
    assert tok.value == '.ghs'
    with nt.assert_raises(Exception):
        lexer.lexer.token()


def test_parser():
    """
    Parse input.

    Args:
    """
    parser = Parser()
    with nt.assert_raises(Exception):
        parser.parser.parse(input='.mode C',
                            lexer=parser.lexer.lexer)


def test_sample0():
    """
    Parse sample sample

    Args:
    """
    fname = 'sample0.dddmp'
    bdd, n_vars, ordering, roots = parser.parse(fname)
    h = to_nx(bdd, n_vars, ordering, roots)
    assert len(h) == 5, len(h)
    edges = {
        (5, 3, 0), (5, 4, 0),
        (4, 1, 0), (4, 2, 0),
        (3, 1, 0), (3, 2, 0),
        (2, 1, 0), (2, 1, 1)}
    assert set(h.edges(keys=True)) == edges
    # complemented edges
    assert h[4][2][0]['label'] == '-1'
    assert h[2][1][0]['label'] == '-1'
    # other attributes
    assert n_vars == 50, n_vars
    assert ordering == {'a': 1, 'b': 2, 'c': 3}, ordering
    assert roots == {-5}
    # pd = nx.drawing.nx_pydot.to_pydot(h)
    # pd.write_pdf('bdd.pdf')


def test_sample1():
    """
    Calculate test1 test test1.

    Args:
    """
    fname = 'sample1.dddmp'
    parser.build(debug=True)
    bdd, n_vars, ordering, roots = parser.parse(fname)
    assert len(bdd) == 16, len(bdd)
    assert n_vars == 10, n_vars
    assert roots == {6, -13, -16}, roots


def test_sample2():
    """
    Convert a bdd to - sample. 0.

    Args:
    """
    # x /\ y
    # where x, y have indices 0, 1
    fname = 'sample2.dddmp'
    bdd = load(fname)
    n = len(bdd)
    assert n == 3, n
    n_vars = len(bdd.vars)
    assert n_vars == 2, n_vars
    assert bdd.roots == {3}, bdd.roots
    root = 3
    i, v, w = bdd.succ(root)
    assert i == 0, i
    assert v == -1, v
    i, v, w = bdd.succ(w)
    assert i == 1, i
    assert v == -1, v
    assert w == 1, w
    # overwrite indices with strings
    bdd.vars = dict(x=0, y=1)
    u = bdd.add_expr('x /\ y')
    assert u == root, u


def test_sample3():
    """
    Return a sample3 test3. bdd.

    Args:
    """
    # x /\ y
    # where x, y are at levels 1, 0
    # nodes are labeled with var names
    fname = 'sample3.dddmp'
    bdd = load(fname)
    n = len(bdd)
    assert n == 3, n
    n_vars = len(bdd.vars)
    assert n_vars == 2, n_vars
    assert bdd.roots == {3}, bdd.roots
    root = 3
    u = bdd.add_expr('x /\ y')
    assert root == u, u


def test_load_dddmp():
    """
    Load bdd of bddmp dataset.

    Args:
    """
    # small sample
    fname = 'sample0.dddmp'
    bdd = load(fname)
    n = len(bdd)
    n_vars = len(bdd.vars)
    assert n == 5, n
    assert n_vars == 3, n_vars
    assert bdd.roots == {-5}, bdd.roots
    root = -5
    u = bdd.add_expr('~ ( (a /\ (b \/ c)) \/ (~ a /\ (b \/ ~ c)) )')
    assert u == root, (u, root)
    # larger sample
    fname = 'sample1.dddmp'
    bdd = load(fname)
    n = len(bdd)
    n_vars = len(bdd.vars)
    assert n == 16, n
    assert n_vars == 10, n_vars
    assert bdd.roots == {6, -13, -16}
    varnames = {'G0', 'G1', 'G2', 'G3', 'G5', 'G6',
                'G7', 'TMP1', 'TMP2', 'TMP3'}
    bddvars = set(bdd.vars)
    assert bddvars == varnames, bddvars
    assert bdd.assert_consistent()


def test_rewrite_tables():
    """
    Rewrite all tables in the database.

    Args:
    """
    prefix = 'dddmp_parsetab'
    for ext in ('.py', '.pyc'):
        fname = prefix + ext
        if os.path.isfile(fname):
            os.remove(fname)
    _rewrite_tables()
    assert os.path.isfile(prefix + '.py')


def to_nx(bdd, n_vars, ordering, roots):
    """Convert result of `Parser.parse` to `networkx.MultiDiGraph`."""
    level2var = {ordering[k]: k for k in ordering}
    level2var[n_vars + 1] = 'T'
    h = nx.MultiDiGraph()
    h.roots = roots
    for u in bdd:
        i, v, w = bdd[u]
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


def test_dump_with_cudd_load_with_dddmp():
    """
    Dump a scalar bdd to dump file

    Args:
    """
    from dd import cudd
    fname = 'foo.dddmp'
    # dump
    bdd = cudd.BDD()
    bdd.declare('y', 'x')
    u = bdd.add_expr('x /\ y')
    bdd.dump(fname, [u])
    # load
    bdd = load(fname)
    print(bdd.roots)
    u, = bdd.roots
    u_ = bdd.add_expr('x /\ y')
    assert u == u_, (u, u_)
    expr = bdd.to_expr(u)
    print(expr)


if __name__ == '__main__':
    test_load_dddmp()
