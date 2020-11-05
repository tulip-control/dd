"""Test multi-valued decision diagrams."""
import logging
import dd.mdd


logger = logging.getLogger(__name__)


def test_find_or_add():
    """
    Find the test test or test.

    Args:
    """
    dvars = dict(x=dict(level=0, len=4),
                 y=dict(level=1, len=2))
    m = dd.mdd.MDD(dvars)
    u = m.find_or_add(0, 1, -1, 1, 1)
    # pd = dd.mdd.to_pydot(m)
    # pd.write_pdf('hehe.pdf')
    print(m.to_expr(u))


def test_bdd_to_mdd():
    """
    Convert a bdd file

    Args:
    """
    from dd.bdd import BDD

    ordering = {'x': 0, 'y': 1}
    bdd = BDD(ordering)
    u = bdd.add_expr('x /\ ~ y')
    bdd.incref(u)
    # BDD -> MDD
    dvars = dict(
        x=dict(level=1, len=2, bitnames=['x']),
        y=dict(level=0, len=2, bitnames=['y']))
    mdd, umap = dd.mdd.bdd_to_mdd(bdd, dvars)
    # pd = dd.mdd.to_pydot(mdd)
    # pd.write_pdf('mdd.pdf')
    # bdd.dump('bdd.pdf')
    v = umap[abs(u)]
    if u < 0:
        v = -v
    print(v)
    bdd.decref(u)


if __name__ == '__main__':
    test_bdd_to_mdd()
