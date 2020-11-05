"""Test module `dd._copy`."""
from dd import autoref
from dd import cudd
from dd import _copy


def test_involution():
    """
    Test if a test is a solution.

    Args:
    """
    _test_involution(autoref)
    _test_involution(cudd)


def _test_involution(mod):
    """
    Test if a bdd_1 and bdd.

    Args:
        mod: (todo): write your description
    """
    bdd_1, bdd_2 = _setup(mod)
    u = bdd_1.add_expr('x /\ ~ y')
    v = _copy.copy_bdd(u, bdd_2)
    u_ = _copy.copy_bdd(v, bdd_1)
    assert u == u_, (u, u_)


def test_bdd_mapping():
    """
    Test if the test mapping.

    Args:
    """
    _test_bdd_mapping(autoref)
    _test_bdd_mapping(cudd)


def _test_bdd_mapping(mod):
    """
    Test if a bdd is equal bdd.

    Args:
        mod: (todo): write your description
    """
    bdd_1, bdd_2 = _setup(mod)
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


def _setup(mod):
    """
    Initialize bdd module.

    Args:
        mod: (todo): write your description
    """
    bdd_1 = mod.BDD()
    bdd_2 = mod.BDD()
    bdd_1.declare('x', 'y')
    bdd_2.declare('x', 'y')
    return bdd_1, bdd_2


def test_dump_load_same_order():
    """
    Determine whether the test test test set.

    Args:
    """
    _test_dump_load_same_order(autoref)
    _test_dump_load_same_order(cudd)


def _test_dump_load_same_order(mod):
    """
    Dump the order of all the same order.

    Args:
        mod: (todo): write your description
    """
    b = mod.BDD()
    b.declare('x', 'y', 'z')
    expr = 'x /\ ~ y'
    u = b.add_expr(expr)
    # dump
    fname = 'hoho.json'
    nodes = [u]
    _copy.dump_json(nodes, fname)
    # load
    target = mod.BDD()
    roots = _copy.load_json(
        fname, target, load_order=True)
    # assert
    v, = roots
    v_ = target.add_expr(expr)
    assert v == v_, (v, v_)
    # copy to source BDD manager
    u_ = target.copy(v, b)
    assert u == u_, (u, u_)


def test_dump_load_different_order():
    """
    Determine whether the test load_different.

    Args:
    """
    _test_dump_load_different_order(autoref)
    _test_dump_load_different_order(cudd)


def _test_dump_load_different_order(mod):
    """
    Dump a json dump of a json file.

    Args:
        mod: (todo): write your description
    """
    source = mod.BDD()
    source.declare('x', 'y')
    expr = ' x <=> y '
    u = source.add_expr(expr)
    # dump
    fname = 'hoho.json'
    nodes = [u]
    _copy.dump_json(nodes, fname)
    # load
    target = mod.BDD()
    target.declare('y', 'x')
    roots = _copy.load_json(
        fname, target, load_order=False)
    # assert
    v, = roots
    v_ = target.add_expr(expr)
    assert v == v_, (v, v_)
