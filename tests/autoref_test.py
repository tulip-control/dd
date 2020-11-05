import logging

from dd import autoref as _bdd
import dd.bdd
from nose.tools import assert_raises

from common import Tests
from common_bdd import Tests as BDDTests


logging.getLogger('astutils').setLevel('ERROR')


Tests.DD = _bdd.BDD
BDDTests.DD = _bdd.BDD


def test_find_or_add():
    """
    Test if bdd is a bdd.

    Args:
    """
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


def test_count():
    """
    Compute the bdd of bdd

    Args:
    """
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


def test_dump_load():
    """
    Dump test dataframe

    Args:
    """
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
    """
    Create a bdd of image is_image

    Args:
    """
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
    """
    Determine the bdd of a.

    Args:
    """
    bdd = _bdd.BDD()
    bdd.declare('x', 'y', 'z')
    action = bdd.add_expr('x <=> y')
    target = bdd.add_expr('x')
    qvars = {'y'}
    rename = dict(x='y')
    u = _bdd.preimage(action, target, rename, qvars)
    u_ = bdd.add_expr('x')
    assert u == u_


def test_reorder_2():
    """
    Reorder vrs.

    Args:
    """
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
    """
    Configure the dynamic configuration.

    Args:
    """
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
    """
    Collects the bdd of two bdds.

    Args:
    """
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
    """
    Returns a copy of the copy.

    Args:
    """
    bdd = _bdd.BDD()
    other = _bdd.BDD()
    vrs = {'x', 'y', 'z'}
    bdd.declare(*vrs)
    _bdd.copy_vars(bdd, other)
    assert vrs.issubset(other.vars)


def test_copy_bdd():
    """
    Returns a copy of the bdd.

    Args:
    """
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


def test_func_len():
    """
    Compute the bdd of two scalar values of bdd

    Args:
    """
    bdd = _bdd.BDD()
    bdd.declare('x', 'y')
    u = bdd.add_expr('x')
    n = len(u)
    assert n == 2, n
    u = bdd.add_expr('x /\ y')
    n = len(u)
    assert n == 3, n


if __name__ == '__main__':
    test_support()
