"""How to use algrebaric decision diagrams (ADDs).

This example requires that the module `dd.cudd_add`
be installed. The module `dd.cudd_add` is written
in Cython, and requires compiling, in order to be
installed. For details on how to install
`dd.cudd_add`, read the main `README.md` file
of the package `dd`.
"""
import dd.cudd_add as _agd


def example_agd():
    agd = _agd.ADD()
    agd.declare('x', 'y', 'z')
    one = agd.constant(1)
    two = agd.constant(2)
    x = agd.var('x')
    y = agd.var('y')
    u = agd.apply('+', one, x)
    v = agd.apply('*', y, two)
    r = agd.apply('-', u, v)
    print(r)
    values = dict(
        x=agd.constant(1),
        y=agd.constant(1))
    p = agd.let(values, r)
    print(p)
    assert p == agd.constant(0)


if __name__ == '__main__':
    example_agd()
