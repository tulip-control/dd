"""Common tests for `autoref`, `cudd`."""
from nose.tools import assert_raises


class Tests(object):
    DD = None  # `autoref.BDD` or `cudd.BDD`

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
        v = b.var('x')
        w = b.var('y')
        u = b.find_or_add('z', v, w)
        u_ = b.add_expr('(~ z /\ x)  \/  (z /\ y)')
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
