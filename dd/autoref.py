"""Wraps `dd.bdd` to automate reference counting.

For function docstrings, refer to `dd.bdd`.
"""
# Copyright 2015 by California Institute of Technology
# All rights reserved. Licensed under BSD-3.
#
import logging
import warnings

from dd import _abc
from dd import bdd as _bdd


log = logging.getLogger(__name__)


class BDD(_abc.BDD):
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
    # omitted docstrings are inheritted from `super()`

    def __init__(self, levels=None):
        manager = _bdd.BDD(levels)
        self._bdd = manager
        self.vars = manager.vars

    def __eq__(self, other):
        return (self._bdd is other._bdd)

    def __len__(self):
        return len(self._bdd)

    def __contains__(self, u):
        assert self is u.bdd
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
        return Function(u, self)

    def configure(self, **kw):
        return self._bdd.configure(**kw)

    def succ(self, u):
        i, v, w = self._bdd.succ(u.node)
        v = self._wrap(v)
        w = self._wrap(w)
        return i, v, w

    def add_var(self, var, level=None):
        return self._bdd.add_var(var, level=level)

    def var(self, var):
        r = self._bdd.var(var)
        return self._wrap(r)

    def var_at_level(self, level):
        return self._bdd.var_at_level(level)

    def level_of_var(self, var):
        return self._bdd.level_of_var(var)

    def copy(self, u, other):
        assert u in self, u
        if self is other:
            log.warning('copying node to same manager')
            return u
        r = self._bdd.copy(u.node, other._bdd)
        return other._wrap(r)

    def support(self, u, as_levels=False):
        assert u in self, u
        return self._bdd.support(u.node, as_levels)

    def let(self, definitions, u):
        assert u in self, u
        d = definitions
        var = next(iter(d))
        value = d[var]
        if isinstance(value, Function):
            d = {
                var: value.node
                for var, value in d.items()}
        r = self._bdd.let(d, u.node)
        return self._wrap(r)

    def evaluate(self, u, values):
        warnings.warn(
            'call the method `let` instead',
            DeprecationWarning)
        assert u in self, u
        return self._bdd.evaluate(u.node, values)

    def compose(self, f, var, g):
        warnings.warn(
            'call the method `let` instead',
            DeprecationWarning)
        assert f in self, f
        assert g in self, g
        r = self._bdd.compose(f.node, var, g.node)
        return self._wrap(r)

    def rename(self, u, dvars):
        warnings.warn(
            'call the method `let` instead',
            DeprecationWarning)
        r = self._bdd.rename(u.node, dvars)
        return self._wrap(r)

    def cofactor(self, u, values):
        warnings.warn(
            'call the method `let` instead',
            DeprecationWarning)
        assert u in self, u
        r = self._bdd.cofactor(u.node, values)
        return self._wrap(r)

    def quantify(self, u, qvars, forall=False):
        assert u in self, u
        r = self._bdd.quantify(u.node, qvars, forall)
        return self._wrap(r)

    def forall(self, qvars, u):
        return self.quantify(u, qvars, forall=True)

    def exist(self, qvars, u):
        return self.quantify(u, qvars, forall=False)

    def ite(self, g, u, v):
        assert g in self, g
        assert u in self, u
        assert v in self, v
        r = self._bdd.ite(g.node, u.node, v.node)
        return self._wrap(r)

    def find_or_add(self, var, low, high):
        """Return node `IF var THEN high ELSE low`."""
        level = self.level_of_var(var)
        r = self._bdd.find_or_add(level, low.node, high.node)
        return self._wrap(r)

    def sat_len(self, u, n=None):
        warnings.warn(
            'call the method `count` instead',
            DeprecationWarning)
        return self.count(u, n)

    def count(self, u, nvars=None):
        assert u in self, u
        return self._bdd.count(u.node, nvars)

    def pick_iter(self, u, care_vars=None):
        assert u in self, u
        return self._bdd.pick_iter(u.node, care_vars)

    def sat_iter(self, u, care_bits=None):
        warnings.warn(
            'call the method `pick_iter` instead',
            DeprecationWarning)
        return self.pick_iter(u, care_bits)

    def add_expr(self, e):
        r = self._bdd.add_expr(e)
        return self._wrap(r)

    def to_expr(self, u):
        assert u in self, u
        return self._bdd.to_expr(u.node)

    def apply(self, op, u, v=None, w=None):
        assert u in self, u
        if v is None:
            r = self._bdd.apply(op, u.node)
        elif w is None:
            assert v in self, v
            r = self._bdd.apply(op, u.node, v.node)
        else:
            assert w in self, w
            r = self._bdd.apply(op, u.node, v.node, w.node)
        return self._wrap(r)

    def _add_int(self, i):
        r = self._bdd._add_int(i)
        return self._wrap(r)

    def cube(self, dvars):
        r = self._bdd.cube(dvars)
        return self._wrap(r)

    def collect_garbage(self, roots=None):
        if roots is not None:
            roots = [u.node for u in roots]
        self._bdd.collect_garbage(roots)

    def dump(self, filename, roots=None,
             filetype=None, **kw):
        if roots is not None:
            roots = [u.node for u in roots]
        self._bdd.dump(filename, roots=roots,
                       filetype=filetype)

    def load(self, filename, levels=True):
        umap = self._bdd.load(filename, levels=levels)
        umap = {u: self._wrap(umap[u]) for u in umap}
        return umap

    def assert_consistent(self):
        self._bdd.assert_consistent()

    @property
    def false(self):
        u = self._bdd.false
        return self._wrap(u)

    @property
    def true(self):
        u = self._bdd.true
        return self._wrap(u)


def image(trans, source, rename, qvars, forall=False):
    assert trans.bdd is source.bdd
    u = _bdd.image(trans.node, source.node, rename,
                   qvars, trans.manager, forall)
    return trans.bdd._wrap(u)


def preimage(trans, target, rename, qvars, forall=False):
    assert trans.bdd is target.bdd
    u = _bdd.preimage(trans.node, target.node, rename,
                      qvars, trans.manager, forall)
    return trans.bdd._wrap(u)


def reorder(bdd, order=None):
    """Apply Rudell's sifting algorithm to `bdd`."""
    _bdd.reorder(bdd._bdd, order=order)


def copy_vars(source, target):
    _bdd.copy_vars(source._bdd, target._bdd)


def copy_bdd(u, target):
    r = _bdd.copy_bdd(u.node, u.manager, target._bdd)
    return target._wrap(r)


class Function(_abc.Operator):
    """Convenience wrapper for edges returned by `BDD`.

    ```
    bdd = BDD(dict(x=0, y=1))
    u = bdd.add_expr('x & y')
    f = Function(u, bdd)
    ```

    Attributes:

    - `node`: `int` that describes edge (signed node)
    - `bdd`: `dd.autoref.BDD` instance that node belongs to
    - `manager`: `dd.bdd.BDD` instance that node belongs to

    Operations are valid only between functions with
    the same `BDD` in `Function.bdd`.

    After all references to a `Function` have been deleted,
    the reference count of its associated node is decremented.
    To explicitly release a `Function` instance, invoke `del f`.

    The design here is inspired by the PyEDA package.
    """

    def __init__(self, node, bdd):
        assert node in bdd._bdd, node
        self.bdd = bdd
        self.manager = bdd._bdd
        self.node = node
        self.manager.incref(node)

    def __hash__(self):
        return self.node

    def to_expr(self):
        """Return Boolean expression of function as `str`."""
        return self.manager.to_expr(self.node)

    def __int__(self):
        return self.node

    def __len__(self):
        return len(self.manager.descendants([self.node]))

    def __del__(self):
        """Decrement reference count of `self.node` in `self.bdd`."""
        self.manager.decref(self.node)

    def __eq__(self, other):
        if other is None:
            return False
        assert self.bdd is other.bdd, (self.bdd, other.bdd)
        return self.node == other.node

    def __ne__(self, other):
        if other is None:
            return True
        assert self.bdd is other.bdd, (self.bdd, other.bdd)
        return not (self == other)

    def __le__(self, other):
        return (other | ~ self) == self.bdd.true

    def __lt__(self, other):
        return self <= other and self != other

    def __invert__(self):
        return self._apply('not', other=None)

    def __and__(self, other):
        return self._apply('and', other)

    def __or__(self, other):
        return self._apply('or', other)

    def implies(self, other):
        return self._apply('implies', other)

    def equiv(self, other):
        return self._apply('equiv', other)

    def _apply(self, op, other):
        """Return result of operation `op` with `other`."""
        # unary op ?
        if other is None:
            u = self.manager.apply(op, self.node)
        else:
            assert self.bdd is other.bdd, (self.bdd, other.bdd)
            u = self.manager.apply(op, self.node, other.node)
        return Function(u, self.bdd)

    @property
    def level(self):
        i, _, _ = self.manager._succ[abs(self.node)]
        return i

    @property
    def var(self):
        i, _, _ = self.manager._succ[abs(self.node)]
        return self.manager.var_at_level(i)

    @property
    def low(self):
        _, v, _ = self.manager._succ[abs(self.node)]
        return Function(v, self.bdd)

    @property
    def high(self):
        _, _, w = self.manager._succ[abs(self.node)]
        return Function(w, self.bdd)

    @property
    def ref(self):
        return self.manager._ref[abs(self.node)]

    @property
    def negated(self):

        return self.node < 0

    @property
    def support(self):
        return self.manager.support(self.node)
