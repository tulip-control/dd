"""Common tests for `cudd`, `cudd_zdd`."""
from nose.tools import assert_raises


class Tests(object):
    DD = None  # `cudd.BDD` or `cudd_zdd.ZDD`

    def test_add_var(self):
        """
        Adds a bdd of variables.

        Args:
            self: (todo): write your description
        """
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
        """
        Compute the length of bdd.

        Args:
            self: (todo): write your description
        """
        bdd = self.DD()
        assert len(bdd) == 0, len(bdd)
        u = bdd.true
        assert len(bdd) == 1, len(bdd)
        del u
        assert len(bdd) == 0, len(bdd)

    def test_levels(self):
        """
        Return a bdd of all levels.

        Args:
            self: (todo): write your description
        """
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
