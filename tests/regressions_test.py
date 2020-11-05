from dd import cudd


def test_reordering_setting_restore():
    """
    Restore a new configuration of a new variables.

    Args:
    """
    # Original report at https://github.com/tulip-control/dd/issues/40
    b = cudd.BDD()
    b.configure(reordering=False)
    b.add_var('x')
    b.add_var('y')
    # x /\ y
    s = '~ x /\ y'
    u = b.add_expr(s)
    assert not b.configure()['reordering']
    g = b.pick_iter(u)
    m = list(g)
    m_ = [dict(x=False, y=True)]
    assert m == m_, (m, m_)
    assert not b.configure()['reordering']


if __name__ == '__main__':
    test_reordering_setting_restore()
