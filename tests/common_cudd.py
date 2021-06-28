"""Common tests for `cudd`, `cudd_zdd`."""
import pytest


class Tests:
    def setup_method(self):
        self.DD = None  # `cudd.BDD` or `cudd_zdd.ZDD`
        self.MODULE = None  # `cudd` or `cudd_zdd`

    def test_add_var(self):
        bdd = self.DD()
        bdd.add_var('x')
        bdd.add_var('y')
        jx = bdd._index_of_var['x']
        jy = bdd._index_of_var['y']
        assert jx == 0, jx
        assert jy == 1, jy
        x = bdd._var_with_index[0]
        y = bdd._var_with_index[1]
        assert x == 'x', x
        assert y == 'y', y
        assert bdd.vars == {'x', 'y'}, bdd.vars
        x = bdd.var('x')
        y = bdd.var('y')
        assert x != y, (x, y)

    def test_len(self):
        bdd = self.DD()
        assert len(bdd) == 0, len(bdd)
        u = bdd.true
        assert len(bdd) == 1, len(bdd)
        del u
        assert len(bdd) == 0, len(bdd)

    def test_levels(self):
        bdd = self.DD()
        bdd.add_var('x', index=0)
        bdd.add_var('y', index=2)
        bdd.add_var('z', index=10)
        ix = bdd.level_of_var('x')
        iy = bdd.level_of_var('y')
        iz = bdd.level_of_var('z')
        # before any reordering, levels match var indices
        assert ix == 0, ix
        assert iy == 2, iy
        assert iz == 10, iz
        x = bdd.var_at_level(0)
        y = bdd.var_at_level(2)
        z = bdd.var_at_level(10)
        assert x == 'x', x
        assert y == 'y', y
        assert z == 'z', z

    def test_var_at_level_exceptions(self):
        bdd = self.DD()
        # no variables
        with pytest.raises(ValueError):
            bdd.var_at_level(-1)
        with pytest.raises(ValueError):
            bdd.var_at_level(0)
        with pytest.raises(ValueError):
            bdd.var_at_level(1)
        with pytest.raises(ValueError):
            # no var at level CUDD_CONST_INDEX
            bdd.var_at_level(bdd.false.level)
        with pytest.raises(OverflowError):
            bdd.var_at_level(bdd.false.level + 1)
        # 1 declared variable
        bdd.declare('x')
        level = bdd.level_of_var('x')
        assert level == 0, level
        var = bdd.var_at_level(0)
        assert var == 'x', var
        with pytest.raises(ValueError):
            bdd.var_at_level(-1)
        with pytest.raises(ValueError):
            bdd.var_at_level(1)
        with pytest.raises(ValueError):
            # no var at level CUDD_CONST_INDEX
            bdd.var_at_level(bdd.false.level)
        with pytest.raises(OverflowError):
            bdd.var_at_level(bdd.false.level + 1)
        bdd._var_with_index = dict()
        with pytest.raises(ValueError):
            bdd.var_at_level(0)

    def test_incref_decref_locally_inconsistent(self):
        # "Locally inconsistent" here means that
        # from the viewpoint of some `Function` instance,
        # the calls to `incref` and `decref` would result
        # in an incorrect reference count.
        #
        # In this example overall the calls to `incref`
        # and `decref` result in an incorrect reference count.
        bdd = self.DD()
        bdd.declare('x', 'y')
        u = bdd.add_expr(r'x /\ y')  # ref cnt = 1
        v = bdd.add_expr(r'x /\ y')  # ref cnt = 2
        bdd.incref(u)  # ref cnt = 3
        bdd.decref(v)  # ref cnt = 2
        del u, v  # ref cnt = 1
        # this assertion implies that `DD.__dealloc__`
        # would raise an exception (that would be
        # ignored)
        assert len(bdd) > 0, len(bdd)
        u = bdd.add_expr(r'x /\ y')  # ref cnt = 2
        u._ref = 2
        bdd.decref(u)  # ref cnt = 1

    def test_decref_incref_locally_inconsistent(self):
        # "Locally inconsistent" here means the
        # same as described in the previous method.
        #
        # The difference with the previous method
        # is that here `decref` is called before
        # `incref`, not after.
        #
        # In this example overall the calls to `incref`
        # and `decref` result in an incorrect reference count.
        bdd = self.DD()
        bdd.declare('x', 'y')
        u = bdd.add_expr(r'x /\ y')  # ref cnt = 1
        v = bdd.add_expr(r'x /\ y')  # ref cnt = 2
        bdd.decref(v)  # ref cnt = 1
        bdd.incref(u)  # ref cnt = 2
        del u, v  # ref cnt = 1
        # this assertion implies that `DD.__dealloc__`
        # would raise an exception (that would be
        # ignored)
        assert len(bdd) > 0, len(bdd)
        u = bdd.add_expr(r'x /\ y')  # ref cnt = 2
        u._ref = 2
        bdd.decref(u)  # ref cnt = 1

    def test_double_incref_decref_locally_inconsistent(self):
        # "Locally inconsistent" here means the
        # same as described in a method above.
        #
        # The main difference with the previous method
        # is that here `decref` is called twice.
        #
        # Overall, the calls to `incref` and `decref`
        # would have resulted in a correct reference count
        # with an earlier implementation.
        #
        # In any case, this pattern of calls to
        # `incref` and `decref` now raises
        # a `RuntimeError`.
        bdd = self.DD()
        bdd.declare('x', 'y')
        u = bdd.add_expr(r'x /\ y')  # ref cnt = 1
        v = bdd.add_expr(r'x /\ y')  # ref cnt = 2
        bdd.incref(u)  # ref cnt = 3
        bdd.incref(u)  # ref cnt = 4
        bdd.decref(v)  # ref cnt = 3
        with pytest.raises(RuntimeError):
            bdd.decref(v)
        del u, v  # ref cnt = 2
        assert len(bdd) > 0, len(bdd)
        u = bdd.add_expr(r'x /\ y')  # ref cnt = 3
        u._ref = 3
        bdd.decref(u)  # ref cnt = 2
        bdd.decref(u)  # ref cnt = 1

    def test_decref_and_dealloc(self):
        bdd = self.DD()
        bdd.declare('x', 'y')
        u = bdd.add_expr(r'x /\ ~ y')
        assert u.ref == 1, u.ref
        s = int(u)
        bdd.decref(u, recursive=True)
        del u  # calls method `Function.__dealloc__`
        # the execution of `decref` and then
        # `__dealloc__` should result in
        # reference count 0,
        # not a negative value
        v = bdd._add_int(s)
        assert v.ref == 1, v.ref
        bdd.decref(v)
        del v
        # the following check passes when
        # `u.ref = 0 - 1`,
        # because the reference count is an
        # unsigned integer, so subtracting 1
        # results in a saturated positive value,
        # which is ignored by the function
        # `Cudd_CheckZeroRef` (which checks
        # `node->ref != 0 && node->ref != DD_MAXREF`)
        assert len(bdd) == 0, len(bdd)

    def test_decref(self):
        bdd = self.DD()
        # Turn off garbage collection to prevent the
        # memory for the CUDD BDD/ZDD node below from
        # being deallocated when the reference count
        # of the node reaches 0.
        # If that happened, then further access to
        # the attribute `u.ref` would have been unsafe.
        bdd.configure(
            reordering=False,
            garbage_collection=False)
        bdd.declare('x', 'y')
        u = bdd.add_expr(r'x /\ ~ y')
        assert u.ref == 1, u.ref
        assert u._ref == 1, u._ref
        bdd.decref(u, recursive=True)
        # CAUTION: `u.node is NULL` hereafter
        assert u._ref == 0, u._ref
        # Ensure that `decref` decrements
        # only positive reference counts.
        # No need for `recursive=True`,
        # because this call should have
        # no effect at all.
        with pytest.raises(RuntimeError):
            bdd.decref(u)
        assert u._ref == 0, u._ref
        assert len(bdd) == 0, len(bdd)

    def test_decref_ref_lower_bound(self):
        bdd = self.DD()
        bdd.declare('x', 'y')
        u = bdd.add_expr(r'x /\ ~ y')
        assert u._ref == 1, u._ref
        assert u.ref == 1, u.ref
        # `recursive=True` is necessary here
        # because after `u._ref` becomes `0`,
        # we cannot any more dereference
        # the successor nodes of `u.node`.
        #
        # The reason is that memory for the
        # BDD/ZDD node pointed to by `u.node`
        # may be deallocated after its
        # reference count becomes 0.
        bdd.decref(u, recursive=True)
        # `u` should not be used after
        # the reference count of the BDD/ZDD node
        # pointed to by `u` becomes 0.
        # This avoids accessing deallocated memory.
        assert u._ref == 0, u._ref
        # Ensure that the method `decref` decrements
        # only positive reference counts.
        # `recursive=True` is irrelevant here,
        # because this call should have
        # no effect at all.
        #
        # Again, `u` is not used in any way
        # that could access deallocated memory.
        with pytest.raises(RuntimeError):
            bdd.decref(u)
        assert u._ref == 0, u._ref
        # check also with `recursive=True`
        with pytest.raises(RuntimeError):
            bdd.decref(u, recursive=True)
        # check also `incref`
        with pytest.raises(RuntimeError):
            bdd.incref(u)
        assert len(bdd) == 0, len(bdd)

    def test_dealloc_wrong_ref_lower_bound(self):
        bdd = self.DD()
        bdd.declare('x', 'y')
        u = bdd.add_expr(r'x /\ ~ y')
        # make an erroneous external modification
        assert u.ref == 1, u.ref
        u._ref = -1  # erroneous value
        with pytest.raises(AssertionError):
            self.MODULE._test_call_dealloc(u)
        assert u.ref == 1, u.ref
        assert u._ref == -1, u._ref
        u._ref = 1  # restore
        del u
        assert len(bdd) == 0, len(bdd)

    def test_dealloc_multiple_calls(self):
        bdd = self.DD()
        bdd.declare('x', 'y')
        u = bdd.add_expr(r'x /\ ~ y')
        assert u.ref == 1, u.ref
        assert u._ref == 1, u._ref
        self.MODULE._test_call_dealloc(u)
        self.MODULE._test_call_dealloc(u)
        assert u._ref == 0, u._ref
        assert len(bdd) == 0, len(bdd)
