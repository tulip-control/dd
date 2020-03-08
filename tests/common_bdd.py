"""Common tests for `autoref`, `cudd`."""
from nose.tools import assert_raises


class Tests(object):
    DD = None  # `autoref.BDD` or `cudd.BDD`

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
        u_ = b.add_expr('(~ x /\ y)  \/  (x /\ z)')
        assert b.apply('<=>', u, u_)
        # as a reminder of the syntactic nature of BDDs
        # and that ZF is untyped, the below assertion is false.
        # assert u == u_, (b.to_expr(u), b.to_expr(u_))

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

    def test_function_properties(self):
        bdd = self.DD()
        bdd.declare('x', 'y')
        order = dict(x=0, y=1)
        bdd.reorder(order)
        u = bdd.add_expr('x \/ y')
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
