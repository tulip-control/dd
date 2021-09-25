"""Test the module `dd.cudd_add`.

"agd" abbreviates
"algebraic decision diagrams".
"""
# This file is released in the public domain.
#
import dd.cudd_add as _agd


def test_zero_one():
    agd = _agd.ADD()
    # zero
    zero = agd.zero
    assert zero.var is None, zero.var
    assert zero.level > 0, zero.level
    assert zero.low is None, zero.low
    assert zero.high is None, zero.high
    # one
    one = agd.one
    assert one.var is None, one.var
    assert one.level > 0, one.level
    assert one.low is None, one.low
    assert one.high is None, one.high
    # zero, one
    assert zero.level == one.level, (
        zero.level, one.level)
    print('completed testing zero and one')


def test_constants():
    agd = _agd.ADD()
    # 2
    two = agd.constant(2)
    assert two.var is None, two.var
    assert two.level == agd.zero.level, (
        two.level, agd.zero.level)
    assert two.low is None, two.low
    assert two.high is None, two.high
    value = agd.value_of(two)
    assert value == 2, value
    # 2.0
    two_ = agd.constant(2.0)
    assert two_ == two, (two_, two)
    assert two_.var is None, two_.var
    assert two_.level == two.level, (
        two_.level, two.level)
    assert two_.low is None, two_.low
    assert two_.high is None, two_.high
    value = agd.value_of(two_)
    assert value == 2.0, value
    print('completed testing constants')


def test_vars():
    agd = _agd.ADD()
    agd.declare('x', 'y', 'z')
    # x
    u = agd.var('x')
    assert u.var == 'x', u.var
    assert u.level == 0, u.level
    assert u.low == agd.zero, u.low
    assert u.high == agd.one, (u.high, agd.one)
    # y
    v = agd.var('y')
    assert v.var == 'y', v.var
    assert v.level == 1, v.level
    assert v.low == agd.zero, v.low
    assert v.high == agd.one, v.high
    # z
    u = agd.var('z')
    assert u.var == 'z', u.var
    assert u.level == 2, u.level
    assert u.low == agd.zero, u.low
    assert u.high == agd.one, u.high
    print('completed testing variables')


def test_support():
    agd = _agd.ADD()
    agd.declare('x', 'y', 'z')
    x = agd.var('x')
    y = agd.var('y')
    xy = agd.apply('and', x, y)
    support = agd.support(xy)
    support_ = {'x', 'y'}
    assert support == support_, support
    u = agd.add_expr(r'(~ x /\ y) \/ z')
    support = agd.support(u)
    support_ = {'x', 'y', 'z'}
    assert support == support_, support
    print('completed testing basic ADDs')


def test_let():
    agd = _agd.ADD()
    agd.declare('x', 'y', 'z')
    u = agd.var('x') & agd.var('y')
    let = dict(y=agd.var('z'))
    v = agd.let(let, u)
    v_ = agd.var('x') & agd.var('z')
    assert v == v_, (v, v_)
    print('completed testing let')


def test_to_expr():
    agd = _agd.ADD()
    agd.declare('x', 'y')
    # x
    u = agd.var('x')
    expr = agd.to_expr(u)
    assert expr == 'x', expr
    # y
    u = agd.var('y')
    expr = agd.to_expr(u)
    assert expr == 'y', expr
    # x /\ ~ y
    u = agd.add_expr(r'x /\ ~ y')
    expr = agd.to_expr(u)
    expr_ = 'ite(x, ite(y, 0.0, 1.0), 0.0)'
    assert expr == expr_, expr
    print('completed testing `to_expr`')


if __name__ == '__main__':
    test_zero_one()
    test_constants()
    test_vars()
    test_support()
    test_let()
    test_to_expr()
