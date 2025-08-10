"""Common tests for `autoref`, `cudd`."""
# This file is released in the public domain.
#
import os

import pytest


class Tests:
    def setup_method(self):
        self.DD = None  # `autoref.BDD` or `cudd.BDD`

    def test_succ(self):
        bdd = self.DD()
        bdd.declare('x')
        u = bdd.var('x')
        level, low, high = bdd.succ(u)
        assert level == 0, level
        assert low == bdd.false, low
        assert high == bdd.true, high

    def test_find_or_add(self):
        b = self.DD()
        for var in ['x', 'y', 'z']:
            b.add_var(var)
        u = b.find_or_add('x', b.false, b.true)
        u_ = b.var('x')
        assert u == u_, b.to_expr(u)
        u = b.find_or_add('y', b.false, b.true)
        u_ = b.var('y')
        assert u == u_, b.to_expr(u)
        v = b.var('y')
        w = b.var('z')
        u = b.find_or_add('x', v, w)
        u_ = b.add_expr(r'(~ x /\ y)  \/  (x /\ z)')
        assert b.apply('<=>', u, u_) == b.true
        assert u == u_, (b.to_expr(u), b.to_expr(u_))

    def test_function(self):
        bdd = self.DD()
        bdd.add_var('x')
        # x
        x = bdd.var('x')
        # assert not x.negated
        low = x.low
        assert low == bdd.false, low
        high = x.high
        assert high == bdd.true, high
        assert x.var == 'x', x.var
        # ~ x
        not_x = ~x
        # assert not_x.negated
        low = not_x.low
        assert low == bdd.false, low
        high = not_x.high
        assert high == bdd.true, high
        assert not_x.var == 'x', not_x.var
        # constant nodes
        false = bdd.false
        assert false.var is None, false.var
        true = bdd.true
        assert true.var is None, true.var
        not_x_ = bdd.add_expr('~ x')
        assert not_x == not_x_, (
            not_x, not_x_)
        # y
        bdd.add_var('y')
        y = bdd.var('y')
        # x & y
        x_and_y = x & y
        negated = x_and_y.negated
        assert not negated, negated
        var = x_and_y.var
        assert var == 'x', var
        low = x_and_y.low
        assert low == bdd.false, low.var
        y_ = x_and_y.high
        assert y == y_, y_.var
        x_and_y_ = bdd.add_expr(r'x /\ y')
        assert x_and_y == x_and_y_, (
            x_and_y, x_and_y_)
        # x | y
        x_or_y = x | y
        negated = x_or_y.negated
        assert not negated, negated
        var = x_or_y.var
        assert var == 'x', var
        low = x_or_y.low
        assert low == y, low.var
        high = x_or_y.high
        assert high == bdd.true, high.var
        x_or_y_ = bdd.add_expr(r'x \/ y')
        assert x_or_y == x_or_y_, (
            x_or_y, x_or_y_)
        # x ^ y
        x_xor_y = x ^ y
        negated = x_xor_y.negated
        assert negated, negated
        var = x_xor_y.var
        assert var == 'x', var
        high = x_xor_y.high
        assert high == y, high.var
        neg_y = x_xor_y.low
        negated = neg_y.negated
        assert negated, negated
        var = neg_y.var
        assert var == 'y', var
        low = neg_y.low
        assert low == bdd.false, low.var
        high = neg_y.high
        assert high == bdd.true, high.var
        x_xor_y_ = bdd.add_expr('x ^ y')
        assert x_xor_y == x_xor_y_, (
            x_xor_y, x_xor_y_)

    def test_function_properties(self):
        bdd = self.DD()
        bdd.declare('x', 'y')
        order = dict(x=0, y=1)
        bdd.reorder(order)
        u = bdd.add_expr(r'x \/ y')
        y = bdd.add_expr('y')
        # Assigned first because in presence of a bug
        # different property calls could yield
        # different values.
        level = u.level
        assert level == 0, level
        var = u.var
        assert var == 'x', var
        low = u.low
        assert low == y, low
        high = u.high
        assert high == bdd.true, high
        ref = u.ref
        assert ref == 1, ref
        assert not u.negated
        support = u.support
        assert support == {'x', 'y'}, support
        # terminal
        u = bdd.false
        assert u.var is None, u.var
        assert u.low is None, u.low
        assert u.high is None, u.high

    def test_negated(self):
        bdd = self.DD()
        bdd.declare('x')
        u = bdd.add_expr('x')
        neg_u = bdd.add_expr('~ x')
        a = u.negated
        b = neg_u.negated
        assert a or b, (a, b)
        assert not (a and b), (a, b)

    def test_dump_pdf(self):
        bdd = self.DD()
        bdd.declare('x', 'y', 'z')
        u = bdd.add_expr(r'x /\ y')
        v = bdd.add_expr(r'y /\ ~ z')
        fname = 'bdd.pdf'
        roots = [u, v]
        self.rm_file(fname)
        bdd.dump(fname, roots)
        assert os.path.isfile(fname)

    def test_dump_load_json(self):
        bdd = self.DD()
        bdd.declare('x', 'y', 'z')
        u = bdd.add_expr(r'(z /\ x /\ y) \/ x \/ ~ y')
        fname = 'foo.json'
        bdd.dump(fname, [u])
        u_, = bdd.load(fname)
        assert u == u_, len(u_)
        # test `ValueError`
        with pytest.raises(ValueError):
            bdd.dump(fname, None)
        with pytest.raises(ValueError):
            bdd.dump(fname, list())
        with pytest.raises(ValueError):
            bdd.dump(fname, dict())

    def rm_file(self, fname):
        if os.path.isfile(fname):
            os.remove(fname)
