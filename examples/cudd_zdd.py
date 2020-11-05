"""How to use ZDDs with CUDD."""
from dd import cudd_zdd


def main():
    """
    Main function.

    Args:
    """
    zdd = cudd_zdd.ZDD()
    zdd.declare('x', 'y', 'z')
    u = zdd.add_expr('(x /\ y) \/ z')
    let = dict(y=zdd.add_expr('~ x'))
    v = zdd.let(let, u)
    v_ = zdd.add_expr('z')
    assert v == v_, (v, v_)


if __name__ == '__main__':
    main()
