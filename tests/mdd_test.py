"""Tests of the module `dd.mdd`."""
import logging

import dd.bdd
import dd.mdd


logger = logging.getLogger(__name__)


def test_ite():
    dvars = dict(
        x=dict(level=0, len=2),
        y=dict(level=1, len=2))
    mdd = dd.mdd.MDD(dvars)
    u = mdd.find_or_add(0, -1, 1)
    v = mdd.find_or_add(1, -1, 1)
    g = mdd.find_or_add(0, -1, 1)
    r_ = mdd.find_or_add(0, v, 1)
    r = mdd.ite(g, u, v)
    assert r == r_, (r, r_)


def test_find_or_add():
    dvars = dict(x=dict(level=0, len=4),
                 y=dict(level=1, len=2))
    m = dd.mdd.MDD(dvars)
    u = m.find_or_add(0, 1, -1, 1, 1)
    # m.dump('hehe.pdf')
    print(m.to_expr(u))


def test_bdd_to_mdd():
    ordering = {'x': 0, 'y': 1}
    bdd = dd.bdd.BDD(ordering)
    u = bdd.add_expr(r'x /\ ~ y')
    bdd.incref(u)
    # BDD -> MDD
    dvars = dict(
        x=dict(level=1, len=2, bitnames=['x']),
        y=dict(level=0, len=2, bitnames=['y']))
    mdd, umap = dd.mdd.bdd_to_mdd(bdd, dvars)
    # mdd.dump('mdd.pdf')
    # bdd.dump('bdd.pdf')
    v = umap[abs(u)]
    if u < 0:
        v = -v
    print(v)
    bdd.decref(u)


if __name__ == '__main__':
    test_bdd_to_mdd()
