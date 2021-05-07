"""Common tests for `cudd`, `cudd_zdd`."""
from nose.tools import assert_raises


class Tests(object):
    DD = None  # `cudd.BDD` or `cudd_zdd.ZDD`

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

    def test_incref_decref_locally_inconsistent(self):
        # "Locally inconsistent" here means that
        # from the viewpoint of some `Function` instance,
        # the calls to `incref` and `decref` would result
        # in an incorrect reference count.
        #
        # In this example it so happens that overall
        # the calls to `incref` and `decref` do not
        # result in an incorrect reference count.
        bdd = self.DD()
        bdd.declare('x', 'y')
        u = bdd.add_expr(r'x /\ y')
        v = bdd.add_expr(r'x /\ y')
        bdd.incref(u)
        bdd.decref(v)
        del u, v
        assert len(bdd) == 0, len(bdd)

    def test_decref_incref_locally_inconsistent(self):
        # "Locally inconsistent" here means the
        # same as described in the previous method.
        #
        # The difference with the previous method
        # is that here `decref` is called before
        # `incref`, not after.
        #
        # As in the previous method,
        # overall the calls to `incref` and `decref`
        # result in a correct reference count.
        bdd = self.DD()
        bdd.declare('x', 'y')
        u = bdd.add_expr(r'x /\ y')
        v = bdd.add_expr(r'x /\ y')
        bdd.decref(v)
        bdd.incref(u)
        del u, v
        assert len(bdd) == 0, len(bdd)

    def test_double_incref_decref_locally_inconsistent(self):
        # "Locally inconsistent" here means the
        # same as described in a method above.
        #
        # The main difference with the previous method
        # is that here `decref` is called twice.
        #
        # As in the previous method,
        # overall the calls to `incref` and `decref`
        # result in a correct reference count.
        bdd = self.DD()
        bdd.declare('x', 'y')
        u = bdd.add_expr(r'x /\ y')
        v = bdd.add_expr(r'x /\ y')
        bdd.incref(u)
        bdd.incref(u)
        bdd.decref(v)
        bdd.decref(v)
        del u, v
        assert len(bdd) == 0, len(bdd)

    def test_decref_and_dealloc(self):
        bdd = self.DD()
        bdd.declare('x', 'y')
        u = bdd.add_expr(r'x /\ ~ y')
        assert u.ref == 1, u.ref
        s = str(u)
        bdd.decref(u, recursive=True)
        del u  # calls method `Function.__dealloc__`
        # the execution of `decref` and then
        # `__dealloc__` should result in
        # reference count 0,
        # not a negative value
        v = bdd.add_expr(s)
        assert v.ref == 1, v.ref
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
        u = bdd.add_expr('x /\ ~ y')
        assert u.ref == 1, u.ref
        bdd.decref(u, recursive=True)
        # safe to access the CUDD BDD/ZDD node's
        # reference count because garbage collection
        # has been turned off above
        assert u.ref == 0, u.ref
        # Ensure that `decref` decrements
        # only positive reference counts.
        # No need for `recursive=True`,
        # because this call should have
        # no effect at all.
        bdd.decref(u)
        # safe to access the CUDD BDD/ZDD node's
        # reference count because garbage collection
        # has been turned off above
        assert u.ref == 0, u.ref
