"""Test module `dd._copy`."""
from dd import cudd
from dd import _copy


def test_involution():
    bdd_1, bdd_2 = _setup()
    u = bdd_1.add_expr('x /\ ~ y')
    v = _copy.copy_bdd(u, bdd_2)
    u_ = _copy.copy_bdd(v, bdd_1)
    assert u == u_, (u, u_)


def test_bdd_mapping():
    bdd_1, bdd_2 = _setup()
    u = bdd_1.add_expr('x /\ ~ y')
    cache = dict()
    u_ = _copy.copy_bdd(u, bdd_2, cache)
    d = {bdd_1._add_int(k): v for k, v in cache.items()}
    _check_bdd_mapping(d, bdd_1, bdd_2)


def _check_bdd_mapping(umap, old_bdd, new_bdd):
    """Raise `AssertionError` if `umap` is inconsistent.

    Asserts that each variable is declared in both managers,
    and at the same level.
    """
    # add terminal to map
    umap[old_bdd.true] = new_bdd.true
    for u, v in umap.items():
        assert u in old_bdd, u
        assert v in new_bdd, v
        assert u.var == v.var
        assert u.level == v.level
        assert u.negated == v.negated
        # terminal ?
        if u.var is None:
            continue
        # non-terminal
        low = _map_node(u.low, umap)
        high = _map_node(u.high, umap)
        assert low == v.low
        assert high == v.high


def _map_node(u, umap):
    """Map node, accounting for complement."""
    z = _copy._flip(u, u)
    r = umap[z]
    return _copy._flip(r, u)


def _setup():
    bdd_1 = cudd.BDD()
    bdd_2 = cudd.BDD()
    bdd_1.declare('x', 'y')
    bdd_2.declare('x', 'y')
    return bdd_1, bdd_2


def test_dump_load():
    b = cudd.BDD()
    b.declare('x', 'y', 'z')
    u = b.add_expr('x /\ ~ y')
    # dump
    fname = 'hoho.json'
    nodes = [u]
    _copy.dump_json(nodes, fname)
    # load
    target = cudd.BDD()
    roots = _copy.load_json(fname, target)
    # assert
    v, = roots
    u_ = target.copy(v, b)
    assert u == u_, (u, u_)
