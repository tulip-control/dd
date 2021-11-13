"""How to use ZDDs with CUDD."""
import dd.cudd_zdd as _zdd


def zdd_example():
    zdd = _zdd.ZDD()
    zdd.declare('x', 'y', 'z')
    u = zdd.add_expr(r'(x /\ y) \/ z')
    let = dict(y=zdd.add_expr('~ x'))
    v = zdd.let(let, u)
    v_ = zdd.add_expr('z')
    assert v == v_, (v, v_)


if __name__ == '__main__':
    zdd_example()
