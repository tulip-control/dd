"""Wraps `dd.bdd` to automate reference counting.

For function docstrings, refer to `dd.bdd`.
"""
from dd import bdd as _bdd


class BDD(object):
    """Shared ordered binary decision diagram.

    It takes and returns `Function` instances,
    which automate reference counting.

    Attributes:

      - `vars`: `dict` mapping `variables` to `int` levels
          Do not assign the `dict` itself.

    For docstrings, refer to methods of `dd.bdd.BDD`,
    with the difference that `Function`s replace nodes
    as arguments and returned types.
    """

    def __init__(self, ordering=None):
        bdd = _bdd.BDD(ordering)
        self.vars = bdd.vars
        self._bdd = bdd

    def __eq__(self, other):
        return (self._bdd is other._bdd)

    def __len__(self):
        return len(self._bdd)

    def __contains__(self, u):
        assert u.bdd is self._bdd
        return u.node in self._bdd

    def __str__(self):
        return (
            'Binary decision diagram (`dd.bdd.BDD` wrapper):\n'
            '------------------------\n'
            '\t {n_vars} BDD variables\n'
            '\t {n} nodes\n').format(
                n_vars=len(self.vars), n=len(self))

    def _wrap(self, u):
        """Return `Function` for node `u`.

        @param u: node in `self._bdd`
        @type u: `int`
        """
        assert u in self._bdd
        return Function(u, self._bdd)

    def add_var(self, var):
        return self._bdd.add_var(var)

    def var(self, var):
        r = self._bdd.var(var)
        return self._wrap(r)

    def var_at_level(self, level):
        return self._bdd.var_at_level(level)

    def level_of_var(self, var):
        return self._bdd.level_of_var(var)

    def evaluate(self, u, values):
        assert u in self, u
        return self._bdd.evaluate(u.node, values)

    def support(self, u, as_levels=False):
        assert u in self, u
        return self._bdd.support(u.node, as_levels)

    def compose(self, f, var, g, cache=None):
        assert f in self, f
        assert g in self, g
        r = self._bdd(f.node, var, g.node)
        return self._wrap(r)

    def ite(self, g, u, v):
        assert g in self, g
        assert u in self, u
        assert v in self, v
        r = self._bdd.ite(g.node, u.node, v.node)
        return self._wrap(r)

    def cofactor(self, u, values):
        assert u in self, u
        r = self._bdd.cofactor(u.node, values)
        return self._wrap(r)

    def quantify(self, u, qvars, forall=False):
        assert u in self, u
        r = self._bdd.quantify(u.node, qvars, forall)
        return self._wrap(r)

    def sat_len(self, u):
        assert u in self, u
        return self._bdd.sat_len(u.node)

    def sat_iter(self, u, full=False, care_bits=None):
        assert u in self, u
        return self._bdd.sat_iter(u.node, full, care_bits)

    def add_expr(self, e):
        return self._bdd.add_expr(e)

    def to_expr(self, u):
        return self._bdd.to_expr(u.node)

    def apply(self, op, u, v=None):
        assert u in self, u
        if v is None:
            r = self._bdd.apply(op, u.node)
        else:
            assert v in self, v
            r = self._bdd.apply(op, u.node, v.node)
        return self._wrap(r)

    def cube(self, dvars):
        r = self._bdd.cube(dvars)
        return self._wrap(r)

    def collect_garbage(self, roots=None):
        if roots is not None:
            roots = [u.node for u in roots]
        self._bdd.collect_garbage(roots)

    def dump(self, filename, filetype=None, **kw):
        self._bdd.dump(filename, filetype, **kw)

    @classmethod
    def load(cls, filename):
        bdd = _bdd.BDD.load(filename)
        wrapper = BDD()
        wrapper.vars = bdd.vars
        wrapper._bdd = bdd
        return wrapper

    def assert_consistent(self):
        self._bdd.assert_consistent()

    @property
    def False(self):
        u = self._bdd.False
        return self._wrap(u)

    @property
    def True(self):
        u = self._bdd.True
        return self._wrap(u)


def rename(u, dvars):
    return _bdd.rename(u.node, u.bdd, dvars)


def image(trans, source, rename, qvars, bdd, forall=False):
    assert trans.bdd == source.bdd
    return _bdd.image(trans.node, source.node, rename,
                      qvars, trans.bdd, forall)


def preimage(trans, target, rename, qvars, bdd, forall=False):
    assert trans.bdd == target.bdd
    return _bdd.preimage(trans.node, target.node, rename,
                         qvars, trans.bdd, forall)


def copy_vars(source, target):
    return _bdd.copy_vars(source, target)


def copy_bdd(u, source, target):
    return _bdd.copy_bdd(u, source, target)


class Function(object):
    """Convenience wrapper for edges returned by `BDD`.

    A convenience is the constructor `from_expr`:

    ```
    bdd = BDD({'x': 0, 'y': 1})
    f = bdd.from_expr('x & y', bdd)
    ```

    A function can be created also directly from a goal:

    ```
    u = bdd.add_expr('x & y')
    f = Function(u, bdd)
    ```

    Operations are valid only between functions with
    the same `BDD` in `Function.bdd`.

    After all references to a `Function` have been deleted,
    the reference count of its associated node is decremented.
    To explicitly release a `Function` instance, invoke `del f`.

    The design here is inspired by the PyEDA package.
    """

    def __init__(self, node, bdd):
        assert node in bdd, node
        self.bdd = bdd
        bdd.incref(node)
        self.node = node

    @classmethod
    def from_expr(cls, expr, bdd):
        """Return `Function` for `expr`, after adding it to `bdd`.

        @type expr: `str`
        @type bdd: `BDD`
        """
        u = bdd.add_expr(expr)
        return cls(u, bdd._bdd)

    def to_expr(self):
        """Return Boolean expression of function as `str`."""
        return self.bdd.to_expr(self.node)

    def __del__(self):
        """Decrement reference count of `self.node` in `self.bdd`."""
        self.bdd.decref(self.node)

    def __eq__(self, other):
        assert self.bdd is other.bdd
        return self.node == other.node

    def __invert__(self):
        return self._apply('not', other=None)

    def __and__(self, other):
        return self._apply('and', other)

    def __or__(self, other):
        return self._apply('or', other)

    def __xor__(self, other):
        return self._apply('xor', other)

    def implies(self, other):
        return self._apply('implies', other)

    def bimplies(self, other):
        return self._apply('bimplies', other)

    def _apply(self, op, other):
        """Return result of operation `op` with `other`."""
        # unary op ?
        if other is None:
            u = self.bdd.apply(op, self.node)
        else:
            assert self.bdd is other.bdd, (self.bdd, other.bdd)
            u = self.bdd.apply(op, self.node, other.node)
        return Function(u, self.bdd)

    @property
    def level(self):
        """Return level that function belongs to."""
        i, _, _ = self.bdd._succ[abs(self.node)]
        return i

    @property
    def var(self):
        """Return name of variable annotating function node."""
        i, _, _ = self.bdd._succ[abs(self.node)]
        return self.bdd.var_at_level(i)

    @property
    def low(self):
        """Return "else" node as `Function`."""
        _, v, _ = self.bdd._succ[abs(self.node)]
        return Function(v, self.bdd)

    @property
    def high(self):
        """Return "then" node as `Function`."""
        _, _, w = self.bdd._succ[abs(self.node)]
        return Function(w, self.bdd)

    @property
    def ref(self):
        """Return reference cound of `self.node` in `self.bdd`."""
        return self.bdd._ref[abs(self.node)]
