"""Ordered binary decision diagrams.


References
==========

Randal E. Bryant
    "Graph-based algorithms for Boolean function manipulation"
    IEEE Transactions on Computers
    Vol. C-35, No.8, August, 1986, pp.677--690

Karl S. Brace, Richard L. Rudell, Randal E. Bryant
    "Efficient implementation of a BDD package"
    27th ACM/IEEE Design Automation Conference (DAC), 1990
    pp.40--45

Richard Rudell
    "Dynamic variable ordering for
    ordered binary decision diagrams"
    IEEE/ACM International Conference on
    Computer-Aided Design (ICCAD), 1993
    pp.42--47

Christel Baier and Joost-Pieter Katoen
    "Principles of model checking"
    MIT Press, 2008
    section 6.7, pp.381--421

Fabio Somenzi
    "Binary decision diagrams"
    Calculational system design, Vol.173
    NATO Science Series F: Computer and systems sciences
    pp.303--366, IOS Press, 1999

Henrik R. Andersen
    "An introduction to binary decision diagrams"
    Lecture notes for "Efficient Algorithms and Programs", 1999
    The IT University of Copenhagen
"""
# Copyright 2014 by California Institute of Technology
# All rights reserved. Licensed under BSD-3.
#
try:
    from collections.abc import Mapping
except ImportError:
    from collections import Mapping
import logging
import pickle
import sys
import warnings

from dd import _abc
from dd import _parser
from dd import _compat
from dd._compat import items
# inline:
# import networkx
# import pydot


logger = logging.getLogger(__name__)
REORDER_STARTS = 100
REORDER_FACTOR = 2
GROWTH_FACTOR = 2
# for python 3
try:
    xrange(0)
except NameError:
    xrange = range


def _request_reordering(bdd):
    """Raise `NeedsReordering` if `len(bdd)` >= threshold."""
    if bdd._last_len is None:
        return
    if len(bdd) >= REORDER_FACTOR * bdd._last_len:
        raise _NeedsReordering()


def _try_to_reorder(func):
    """Decorator that serves reordering requests."""
    def _wrapper(bdd, *args, **kwargs):
        with _ReorderingContext(bdd):
            return func(bdd, *args, **kwargs)
        logger.info('Reordering needed...')
        # disable reordering requests while swapping
        bdd._last_len = None
        reorder(bdd)
        len_after = len(bdd)
        # try again, reordering disabled to avoid livelock
        with _ReorderingContext(bdd):
            r = func(bdd, *args, **kwargs)
        # enable reordering requests
        bdd._last_len = GROWTH_FACTOR * len_after
        return r
    return _wrapper


class _ReorderingContext(object):
    """Context manager that tracks decorator nesting."""

    def __init__(self, bdd):
        self.bdd = bdd
        self.nested = None

    def __enter__(self):
        self.nested = self.bdd._reordering_context
        self.bdd._reordering_context = True

    def __exit__(self, ex_type, ex_value, tb):
        self.bdd._reordering_context = self.nested
        if ex_type is _NeedsReordering and not self.nested:
            return True


class _NeedsReordering(Exception):
    """Raise this to request reordering."""
    pass


class BDD(_abc.BDD):
    """Shared ordered binary decision diagram.

    The terminal node is 1.
    Nodes are positive integers, edges signed integers.
    Complemented edges are represented as negative integers.
    Values returned by methods are edges, possibly complemented.

    Attributes:
      - `vars`: `dict` mapping `variables` to `int` levels
      - `roots`: (optional) edges
      - `max_nodes`: raise `Exception` if this limit is reached.
        The default value is `sys.maxsize` in Python 3 and
        `sys.maxint` in Python 2. Increase it if needed.

    To ensure that the target node of a returned edge
    is not garbage collected during reordering,
    increment its reference counter:

    `bdd.incref(edge)`

    To ensure that `ite` maintains reducedness add new
    nodes using `find_or_add` to keep the table updated,
    or call `update_predecessors` prior to calling `ite`.
    """
    # omitted docstrings are inheritted from `super()`
    # "nat" below means "natural number",
    # i.e., int >= 0

    def __init__(self, levels=None):
        if levels is None:
            levels = dict()
        _assert_valid_ordering(levels)
        # (level, low, high) -> node
        # tuple(nat, int, nat) -> nat
        self._pred = dict()
        # node -> (level, low, high)
        # nat -> tuple(nat, int, nat)
        self._succ = dict()
        # reference counters
        # node -> reference count
        # nat -> nat
        self._ref = dict()
        # all smaller positive integers
        # are used as node indices, and
        # no larger integers are used
        # as node indices
        # nat
        self._min_free = 2
        # cache for ternary conditional
        # ("ite" is an initialism for
        #  "if-then-else")
        # (condition, then, else) -> edge
        # (int, int, int) -> int
        self._ite_table = dict()
        # mapping from variable names to
        # levels of variables
        # var name -> level
        # str -> nat
        self.vars = dict()
        # mapping from levels of variables
        # to variable names,
        # inverse of `self.vars`
        # level -> var name
        # nat -> str
        self._level_to_var = dict()
        # handle no vars
        self._init_terminal(len(self.vars))
        # for decorator nesting
        self._reordering_context = False
        # after last reordering
        self._last_len = None
        for var, level in levels.items():
            self.add_var(var, level)
        # set of edges
        # optional
        self.roots = set()
        try:
            # Python 2, for xrange
            self.max_nodes = sys.maxint
        except AttributeError:
            self.max_nodes = sys.maxsize

    def __copy__(self):
        bdd = BDD(self.vars)
        bdd._pred = dict(self._pred)
        bdd._succ = dict(self._succ)
        bdd._ref = dict(self._ref)
        bdd._min_free = self._min_free
        bdd.roots = set(self.roots)
        bdd.max_nodes = self.max_nodes
        return bdd

    def __del__(self):
        """Assert that all remaining nodes are garbage."""
        self.decref(1)  # free ref from `self._init_terminal`
        self.collect_garbage()
        if not all(v == 0 for v in self._ref.values()):
            raise AssertionError((
                'There are nodes still referenced '
                'upon shutdown. Details:\n'
                '{_ref}').format(_ref=self._ref))

    def __len__(self):
        return len(self._succ)

    def __contains__(self, u):
        return abs(u) in self._succ

    def __iter__(self):
        return iter(self._succ)

    def __str__(self):
        return (
            'Binary decision diagram:\n'
            '------------------------\n'
            'var levels: {self.vars}\n'
            'roots: {self.roots}\n').format(self=self)

    def configure(self, **kw):
        """Read and apply parameter values.

        First read parameter values (returned as `dict`),
        then apply `kw`. Available keyword arguments:

        - `'reordering'`: if `True` then enable, else disable
        """
        d = dict(
            reordering=(self._last_len is not None))
        for k, v in kw.items():
            if k == 'reordering':
                if v:
                    self._last_len = max(
                        REORDER_STARTS, len(self))
                else:
                    self._last_len = None
            else:
                raise Exception(
                    'Unknown parameter "{k}"'.format(k=k))
        return d

    @property
    def ordering(self):
        raise DeprecationWarning(
            'use `dd.bdd.BDD.vars` instead of `.ordering`')

    def _init_terminal(self, level):
        """Place constant node `1`.

        Used for initialization and to shift node `1` to
        lower levels, as fresh variables are being added.
        """
        u = 1
        t = (level, None, None)
        told = self._succ.setdefault(u, t)
        self._pred.pop(told, None)
        self._succ[u] = t
        self._pred[t] = u
        self._ref.setdefault(u, 1)

    def succ(self, u):
        """Return `(level, low, high)` for `abs(u)`."""
        return self._succ[abs(u)]

    def incref(self, u):
        """Increment reference count of node `u`."""
        self._ref[abs(u)] += 1

    def decref(self, u):
        """Decrement reference count of node `u`, with 0 as min."""
        if self._ref[abs(u)] <= 0:
            warnings.warn((
                'The method `dd.bdd.BDD.decref` was called '
                'for BDD node {u} with reference count {n}. '
                'This call has no effect. Calling `decref` '
                'for a node with nonpositive reference count '
                'may indicate a programming error.'
                ).format(u=u, n=self._ref[abs(u)]),
                UserWarning)
            return
        self._ref[abs(u)] -= 1

    def ref(self, u):
        """Return reference count of edge `u`."""
        return self._ref[abs(u)]

    def add_var(self, var, level=None):
        """Declare a variable named `var` at `level`.

        The new variable is Boolean-valued.

        If `level` is absent, then add the new variable
        at the bottom level.

        Raise `ValueError` if:
        - `var` already exists at a level
          different than the given `level`, or
        - the given `level` is already used by
          another variable
        - `level` is not given and `var` does not exist,
          and the next level larger than the
          current bottom level is already used by
          another variable.

        If `var` already exists, and either `level`
        is not given, or `var` has `level`,
        then return without raising exceptions.

        @param var: name of new variable to declare
        @type var: `str`
        @param level: level of new variable to declare
        @type level: `int`
        @return: level of variable `var`
        """
        # var already exists ?
        if var in self.vars:
            k = self.vars[var]
            if level is not None:
                assert level == k, (var, k, level)
            return k
        # assume next level is unoccupied
        if level is None:
            level = len(self.vars)
        # level occupied ?
        try:
            other = self.var_at_level(level)
        except AssertionError:
            other = None
        assert other is None, (
            ('level {level} occupied by {var}, '
             'choose another level').format(
                level=level, var=other))
        self.vars[var] = level
        self._level_to_var[level] = var
        self._init_terminal(len(self.vars))
        return level

    @_try_to_reorder
    def var(self, var):
        assert var in self.vars, (
            'undefined variable "{v}", '
            'known variables are:\n {d}').format(
                v=var, d=self.vars)
        j = self.vars[var]
        u = self.find_or_add(j, -1, 1)
        return u

    def var_at_level(self, level):
        if level not in self._level_to_var:
            raise AssertionError(
                'level {j} does not exist'.format(j=level))
        return self._level_to_var[level]

    def level_of_var(self, var):
        return self.vars.get(var)

    @property
    def var_levels(self):
        return dict(self.vars)

    def _map_to_level(self, d):
        """Map keys of `d` to variable levels using `self.vars`.

        If `d` is an iterable but not a mapping,
        then an iterable is returned.

        @type d: `dict` or `set`
        """
        if not d:
            return d
        # are keys variable names ?
        u = next(iter(d))
        if u not in self.vars:
            for level in d:
                assert level in self._level_to_var, level
            return d
        if isinstance(d, Mapping):
            r = {
                self.vars[var]: bool(val)
                for var, val in items(d)}
        else:
            r = {self.vars[k] for k in d}
        return r

    def _top_var(self, *nodes):
        return min(map(lambda x: self._succ[abs(x)][0], nodes))

    def copy(self, u, other):
        """Transfer BDD with root `u` to `other`.

        @type other: `BDD`
        """
        return copy_bdd(u, self, other)

    def descendants(self, roots):
        """Return nodes reachable from `roots`.

        Nodes pointed to by references in `roots` are included.
        Nodes are represented as positive integers.
        """
        if not roots:
            return set()
        visited = {1}
        for u in roots:
            self._descendants(u, visited)
        abs_roots = set(abs(u) for u in roots)
        assert abs_roots.issubset(visited), (abs_roots, visited)
        return visited

    def _descendants(self, u, visited):
        r = abs(u)
        if r == 1 or r in visited:
            return
        _, v, w = self._succ[r]
        self._descendants(v, visited)
        self._descendants(w, visited)
        visited.add(r)

    def is_essential(self, u, var):
        """Return `True` if `var` is essential for node `u`.

        @param var: level in `vars`
        @type var: `int`
        """
        i = self.vars.get(var)
        if i is None:
            return False
        iu, v, w = self._succ[abs(u)]
        # var above node u ?
        if i < iu:
            return False
        if i == iu:
            return True
        # u depends on node labeled with var ?
        if self.is_essential(v, var):
            return True
        if self.is_essential(w, var):
            return True
        return False

    def support(self, u, as_levels=False):
        levels = set()
        nodes = set()
        self._support(u, levels, nodes)
        if as_levels:
            return levels
        return {self.var_at_level(i) for i in levels}

    def _support(self, u, levels, nodes):
        """Recurse to collect variables in support."""
        # exhausted all vars ?
        if len(levels) == len(self.vars):
            return
        # visited ?
        r = abs(u)
        if r in nodes:
            return
        nodes.add(r)
        # terminal ?
        if r == 1:
            return
        # add var
        i, v, w = self._succ[r]
        levels.add(i)
        # recurse
        self._support(v, levels, nodes)
        self._support(w, levels, nodes)

    def levels(self, skip_terminals=False):
        """Return generator of tuples `(u, i, v, w)`.

        Where `i` ranges from terminals to root.

        @param skip_terminals: if `True`, then omit
            terminal nodes.
        """
        if skip_terminals:
            n = len(self.vars) - 1
        else:
            n = len(self.vars)
        for i in xrange(n, -1, -1):
            for u, (j, v, w) in items(self._succ):
                if i != j:
                    continue
                yield u, i, v, w

    def _levels(self):
        """Return `dict` from levels to `set`s of nodes."""
        n = len(self.vars)
        levels = {i: set() for var, i in items(self.vars)}
        levels[n] = set()
        for u, (i, v, w) in items(self._succ):
            levels[i].add(u)
        levels.pop(n)
        return levels

    @_try_to_reorder
    def reduction(self):
        """Return copy reduced with respect to `self.vars`.

        This function has educational value.
        """
        # terminals
        bdd = BDD(self.vars)
        umap = {1: 1}
        # non-terminals
        for u, i, v, w in self.levels(skip_terminals=True):
            assert u > 0, u
            p, q = umap[abs(v)], umap[abs(w)]
            p = _flip(p, v)
            q = _flip(q, w)
            r = bdd.find_or_add(i, p, q)
            assert r > 0, r
            umap[u] = r
        for v in self.roots:
            p = umap[abs(v)]
            p = _flip(p, v)
            bdd.roots.add(p)
        return bdd

    def undeclare_vars(self, *vrs):
        """Remove unused variables `vrs` from `self.vars`.

        Asserts that each variable in `vrs` corresponds to
        an empty level.

        If `vrs` is empty, then remove all unused variables.

        Garbage collection may need to be called before
        calling `undeclare_vars`, in order to collect
        unreferenced nodes to obtain empty levels.
        """
        for var in vrs:
            assert var in self.vars, var
        full_levels = {i for i, _, _ in _compat.values(self._succ)}
        # remove only unused variables
        for var in vrs:
            level = self.level_of_var(var)
            assert level not in full_levels, (var, level)
        # keep unused variables not in `vrs`
        if vrs:
            full_levels |= {
                level for var, level in items(self.vars)
                if var not in vrs}
        # map old to new levels
        n = 1 + len(self.vars)  # include terminal
        new_levels = [i for i in range(n) if i in full_levels]
        new_levels = {i: new for new, i in enumerate(new_levels)}
        # update variables and level declarations
        rm_vars = {var for var, level in items(self.vars)
                   if level not in full_levels}
        self.vars = {var: new_levels[old] for var, old in items(self.vars)
                     if old in full_levels}
        self._level_to_var = {k: var for var, k in items(self.vars)}
        # update node levels
        self._succ = {
            u: (new_levels[i], v, w)
            for u, (i, v, w) in items(self._succ)}
        self._pred = {v: k for k, v in items(self._succ)}
        # clear cache
        self._ite_table = dict()
        return rm_vars

    def let(self, definitions, u):
        d = definitions
        if not d:
            logger.warning(
                'Call to `BDD.let` with no effect: '
                '`defs` is empty.')
            return u
        var = next(iter(definitions))
        value = d[var]
        if isinstance(value, bool):
            return self.cofactor(u, d)
        elif isinstance(value, int):
            return self.compose(u, d)
        try:
            value + 's'
        except TypeError:
            raise ValueError(
                'Key must be var name as `str`, '
                'or Boolean value as `bool`, '
                'or BDD node as `int`.')
        return self.rename(u, d)

    @_try_to_reorder
    def compose(self, f, var_sub):
        """Return substitutions `var_sub` in `f`.

        @param f: node
        @param var_sub: `dict` that maps variables to BDD nodes
        """
        cache = dict()
        if len(var_sub) == 1:
            (var, g), = var_sub.items()
            j = self.level_of_var(var)
            r = self._compose(f, j, g, cache)
        else:
            dvars = {
                self.level_of_var(var): g
                for var, g in var_sub.items()}
            r = self._vector_compose(f, dvars, cache)
        return r

    def _compose(self, f, j, g, cache):
        # terminal ?
        if abs(f) == 1:
            return f
        # cached ?
        if (f, g) in cache:
            return cache[(f, g)]
        # independent of j ?
        i, v, w = self._succ[abs(f)]
        # below j ?
        if j < i:
            return f
        elif i == j:
            r = self.ite(g, w, v)
            # complemented edge ?
            if f < 0:
                r = -r
        else:
            assert i < j, (i, j)
            k, _, _ = self._succ[abs(g)]
            z = min(i, k)
            f0, f1 = self._top_cofactor(f, z)
            g0, g1 = self._top_cofactor(g, z)
            p = self._compose(f0, j, g0, cache)
            q = self._compose(f1, j, g1, cache)
            r = self.find_or_add(z, p, q)
        cache[(f, g)] = r
        return r

    def _vector_compose(self, f, level_sub, cache):
        # terminal ?
        if abs(f) == 1:
            return f
        # cached ?
        r = cache.get(abs(f))
        if r is not None:
            assert r > 0, r
            # complement ?
            if f < 0:
                r = -r
            return r
        # recurse
        i, v, w = self._succ[abs(f)]
        p = self._vector_compose(v, level_sub, cache)
        q = self._vector_compose(w, level_sub, cache)
        # map this level
        var = self.var_at_level(i)
        g = level_sub.get(i, self.var(var))
        r = self.ite(g, q, p)
        # memoize
        cache[abs(f)] = r
        # complement ?
        if f < 0:
            r = -r
        return r

    @_try_to_reorder
    def rename(self, u, dvars):
        """Efficient rename to non-essential neighbors.

        @param dvars: `dict` from variabe levels to variable levels
            or from variable names to variable names
        """
        return rename(u, self, dvars)

    def _top_cofactor(self, u, i):
        """Return restriction for assignment to single variable.

        @param u: node
        @param i: variable level
        """
        # terminal node ?
        if abs(u) == 1:
            return (u, u)
        # non-terminal node
        iu, v, w = self._succ[abs(u)]
        # u independent of var ?
        if i < iu:
            return (u, u)
        assert iu == i, 'for i > iu, call cofactor instead'
        # u labeled with var
        # complement ?
        if u < 0:
            v, w = -v, -w
        return (v, w)

    @_try_to_reorder
    def cofactor(self, u, values):
        """Substitute Boolean `values` for variables in `u`.

        @param u: node
        @param values: `dict` that maps var names to `bool`
        """
        values = self._map_to_level(values)
        cache = dict()
        ordvar = sorted(values)
        j = 0
        assert abs(u) in self, u
        return self._cofactor(u, j, ordvar, values, cache)

    def _cofactor(self, u, j, ordvar, values, cache):
        """Recurse to compute cofactor."""
        # terminal ?
        if abs(u) == 1:
            return u
        # memoized ?
        if u in cache:
            return cache[u]
        i, v, w = self._succ[abs(u)]
        n = len(ordvar)
        # skip nonessential variables
        while j < n:
            if ordvar[j] < i:
                j += 1
            else:
                break
        if j == n:
            # exhausted valuation
            return u
        assert j < n, (j, n)
        # recurse
        if i in values:
            val = values[i]
            if bool(val):
                v = w
            r = self._cofactor(v, j, ordvar, values, cache)
        else:
            p = self._cofactor(v, j, ordvar, values, cache)
            q = self._cofactor(w, j, ordvar, values, cache)
            r = self.find_or_add(i, p, q)
        # complement ?
        if u < 0:
            r = -r
        cache[u] = r
        return r

    @_try_to_reorder
    def quantify(self, u, qvars, forall=False):
        """Return existential or universal abstraction.

        @param u: node
        @param qvars: `set` of quantified variables
        @param forall: if `True`,
            then quantify `qvars` universally,
            else existentially.
        """
        qvars = self._map_to_level(qvars)
        cache = dict()
        ordvar = sorted(qvars)
        j = 0
        return self._quantify(u, j, ordvar, qvars, forall, cache)

    def _quantify(self, u, j, ordvar, qvars, forall, cache):
        """Recurse to quantify variables."""
        # terminal ?
        if abs(u) == 1:
            return u
        if u in cache:
            return cache[u]
        i, v, w = self._succ[abs(u)]
        # complement ?
        if u < 0:
            v, w = -v, -w
        n = len(ordvar)
        # skip nonessential variables
        while j < n:
            if ordvar[j] < i:
                j += 1
            else:
                break
        else:
            # exhausted valuation
            return u
        # recurse
        p = self._quantify(v, j, ordvar, qvars, forall, cache)
        q = self._quantify(w, j, ordvar, qvars, forall, cache)
        if i in qvars:
            if forall:
                r = self.ite(p, q, -1)  # conjoin
            else:
                r = self.ite(p, 1, q)  # disjoin
        else:
            r = self.find_or_add(i, p, q)
        cache[u] = r
        return r

    def forall(self, qvars, u):
        return self.quantify(u, qvars, forall=True)

    def exist(self, qvars, u):
        return self.quantify(u, qvars, forall=False)

    @_try_to_reorder
    def ite(self, g, u, v):
        # wrap so reordering can delete unreferenced nodes
        return self._ite(g, u, v)

    def _ite(self, g, u, v):
        """Recurse to compute ternary conditional."""
        # is g terminal ?
        if g == 1:
            return u
        elif g == -1:
            return v
        # g is non-terminal
        # already computed ?
        r = (g, u, v)
        w = self._ite_table.get(r)
        if w is not None:
            return w
        z = min(self._succ[abs(g)][0],
                self._succ[abs(u)][0],
                self._succ[abs(v)][0])
        g0, g1 = self._top_cofactor(g, z)
        u0, u1 = self._top_cofactor(u, z)
        v0, v1 = self._top_cofactor(v, z)
        p = self._ite(g0, u0, v0)
        q = self._ite(g1, u1, v1)
        w = self.find_or_add(z, p, q)
        # cache
        self._ite_table[r] = w
        return w

    def find_or_add(self, i, v, w):
        """Return reference to node at level `i` with successors `v, w`.

        If such a node exists already,
        then it is quickly found in the cached table,
        and the reference returned.

        @param i: level in `range(n_vars - 1)`
        @param v: low edge
        @param w: high edge
        """
        _request_reordering(self)
        assert 0 <= i < len(self.vars), i
        assert abs(v) in self, v
        assert abs(w) in self, w
        # ensure canonicity of complemented edges
        if w < 0:
            v, w = -v, -w
            r = -1
        else:
            r = 1
        # eliminate
        if v == w:
            return r * v
        # already exists ?
        t = (i, v, w)
        u = self._pred.get(t)
        if u is not None:
            return r * u
        # find a free integer
        u = self._min_free
        assert u > 1, u
        assert u not in self, (self._succ, u)
        # add node
        self._pred[t] = u
        self._succ[u] = t
        self._ref[u] = 0
        self._min_free = self._next_free_int(u)
        # increment reference counters
        self.incref(v)
        self.incref(w)
        return r * u

    def _next_free_int(self, start):
        """Return the smallest unused integer larger than `start`."""
        assert start >= 1, start
        for i in xrange(start, self.max_nodes):
            if i not in self._succ:
                return i
        raise Exception('full: reached `self.max_nodes` nodes.')

    def collect_garbage(self, roots=None):
        """Recursively remove nodes with zero reference count.

        Removal starts from the nodes in `roots` with zero
        reference count. If no `roots` are given, then
        all nodes are scanned for zero reference counts.

        @type roots: `set`, Caution: it is modified
        """
        n = len(self)
        if roots is None:
            roots = self._ref
        dead = {u for u in roots if not self._ref[abs(u)]}
        # keep terminal
        if 1 in dead:
            dead.remove(1)
        while dead:
            u = dead.pop()
            assert u != 1, u
            # remove
            i, v, w = self._succ.pop(u)
            u_ = self._pred.pop((i, v, w))
            uref = self._ref.pop(u)
            self._min_free = min(u, self._min_free)
            assert u == u_, (u, u_)
            assert not uref, uref
            assert self._min_free > 1, self._min_free
            # decrement reference counters
            self.decref(v)
            self.decref(w)
            # died ?
            if not self._ref[abs(v)] and abs(v) != 1:
                dead.add(abs(v))
            if not self._ref[w] and w != 1:
                dead.add(w)
        self._ite_table = dict()
        m = len(self)
        k = n - m
        assert k >= 0, (n, m)

    def update_predecessors(self):
        """Update table that maps (level, low, high) to nodes."""
        for u, t in items(self._succ):
            if abs(u) == 1:
                continue
            self._pred[t] = u

    def swap(self, x, y, all_levels=None):
        """Permute adjacent variables `x` and `y`.

        Swapping invokes the garbage collector,
        so be sure to `incref` nodes that should remain.

        @param x, y: variable name or level
        @type x, y: `str` or `int`
        """
        if all_levels is None:
            self.collect_garbage()
            all_levels = self._levels()
        logger.debug(
            'swap variables "{x}" and "{y}"'.format(x=x, y=y))
        x = self.vars.get(x, x)
        y = self.vars.get(y, y)
        assert 0 <= x < len(self.vars), x
        assert 0 <= y < len(self.vars), y
        # ensure x < y
        if x > y:
            x, y = y, x
        assert x < y, (x, y)
        assert abs(x - y) == 1, (x, y)
        # count nodes
        oldsize = len(self._succ)
        # collect levels x and y
        levels = {x: dict(), y: dict()}
        for j in (x, y):
            for u in all_levels[j]:
                i, v, w = self._succ[abs(u)]
                assert i == j, (i, x, y)
                u_ = self._pred.pop((i, v, w))
                assert u == u_, (u, u_)
                levels[j][u] = (v, w)
        # move level y up
        for u, (v, w) in items(levels[y]):
            i, _, _ = self._succ[u]
            assert i == y, (i, y)
            r = (x, v, w)
            self._succ[u] = r
            assert r not in self._pred, r
            self._pred[r] = u
        # move level x down
        # first x nodes independent of y
        done = set()
        for u, (v, w) in items(levels[x]):
            i, _, _ = self._succ[u]
            assert i == x, (i, x)
            iv, v0, v1 = self._low_high(v)
            iw, w0, w1 = self._low_high(w)
            # dependeds on y ?
            if iv <= y or iw <= y:
                continue
            # independent of y
            r = (y, v, w)
            self._succ[u] = r
            assert r not in self._pred, r
            self._pred[r] = u
            done.add(u)
        # x nodes dependent on y
        garbage = set()
        xfresh = set()
        for u, (v, w) in items(levels[x]):
            if u in done:
                continue
            i, _, _ = self._succ[u]
            assert i == x, (i, x)
            self.decref(v)
            self.decref(w)
            # possibly dead
            garbage.add(abs(v))
            garbage.add(w)
            # calling cofactor can fail because y moved
            iv, v0, v1 = self._swap_cofactor(v, y)
            iw, w0, w1 = self._swap_cofactor(w, y)
            # x node depends on y
            assert y <= iv and y <= iw, (iv, iw, y)
            assert y == iv or y == iw, (iv, iw, y)
            # complemented edge ?
            if v < 0 and y == iv:
                v0, v1 = -v0, -v1
            p = self.find_or_add(y, v0, w0)
            q = self.find_or_add(y, v1, w1)
            assert q >= 0, q
            assert p != q, (
                'No elimination: node depends on both x and y')
            if self._succ[abs(p)][0] == y:
                xfresh.add(abs(p))
            if self._succ[q][0] == y:
                xfresh.add(q)
            r = (x, p, q)
            self._succ[u] = r
            assert r not in self._pred, (u, r, levels, self._pred)
            self._pred[r] = u
            self.incref(p)
            self.incref(q)
            # garbage collection could be interleaved
            # but only if there is substantial loss of efficiency
        # swap x and y in `vars`
        vx = self.var_at_level(x)
        self.vars[vx] = y
        vy = self.var_at_level(y)
        self.vars[vy] = x
        # reset
        self._level_to_var[y] = vx
        self._level_to_var[x] = vy
        self._ite_table = dict()
        # count nodes
        self.collect_garbage(garbage)
        newsize = len(self._succ)
        # new levels
        newx = set()
        newy = set()
        for u in levels[x]:
            if u not in self._succ:
                continue
            i, _, _ = self._succ[u]
            if i == x:
                newy.add(u)
            elif i == y:
                newx.add(u)
            else:
                raise AssertionError((u, i, x, y))
        for u in xfresh:
            i, _, _ = self._succ[u]
            assert i == y, (u, i, x, y)
            newx.add(u)
        for u in levels[y]:
            if u not in self._succ:
                continue
            i, _, _ = self._succ[u]
            assert i == x, (u, i, x, y)
            newy.add(u)
        all_levels[x] = newy
        all_levels[y] = newx
        return (oldsize, newsize)

    def _low_high(self, u):
        """Return level, low, and high.

        If node `u` is a leaf,
        then `u` is returned as low and high.

        This method is similar to the
        method `succ`, but different.

        @type u: `int`
        @return: (level, low, high)
        @rtype: `tuple(int, int, int)`
        """
        i, v, w = self._succ[abs(u)]
        if abs(u) == 1:
            return i, u, u
        return i, v, w

    def _swap_cofactor(self, u, y):
        """Return cofactor of node `u` wrt level `y`.

        If node `u` is above level `y`, that means
        it was at level `y` when the swap started.
        To account for this, `y` is returned as the node level.
        """
        i, v, w = self._succ[abs(u)]
        if y < i:
            return (i, u, u)
        else:
            # restore index of y node that moved up
            return (y, v, w)

    def count(self, u, nvars=None):
        n = nvars
        if abs(u) not in self:
            raise ValueError(u)
        # index those levels in support separately
        levels = {
            self.level_of_var(var)
            for var in self.support(u)}
        k = len(levels)
        if n is None:
            n = k
        slack = n - k
        if slack < 0:
            raise ValueError(slack)
        map_level = dict()
        for new, old in enumerate(sorted(levels)):
            map_level[old] = new + slack
        old, _, _ = self._succ[1]
        map_level[old] = n
        map_level['all'] = n
        r = self._sat_len(u, map_level, d=dict())
        i, _, _ = self._succ[abs(u)]
        i = map_level[i]
        return r * 2**i

    def _sat_len(self, u, map_level, d):
        """Recurse to compute the number of models."""
        # terminal ?
        if u == 1:
            return 1
        if u == -1:
            return 0
        i, v, w = self._succ[abs(u)]
        i = map_level[i]
        # memoized ?
        if abs(u) in d:
            n = d[abs(u)]
            # complement ?
            if u < 0:
                n = 2**(map_level['all'] - i) - n
            return n
        # non-terminal
        nv = self._sat_len(v, map_level, d)
        nw = self._sat_len(w, map_level, d)
        iv, _, _ = self._succ[abs(v)]
        iw, _, _ = self._succ[w]
        iv = map_level[iv]
        iw = map_level[iw]
        # sum
        n = (nv * 2**(iv - i - 1) +
             nw * 2**(iw - i - 1))
        d[abs(u)] = n
        # complement ?
        if u < 0:
            n = 2**(map_level['all'] - i) - n
        return n

    def pick_iter(self, u, care_vars=None):
        # empty ?
        if not self._succ:
            return
        # non-empty
        assert abs(u) in self._succ, u
        cube = dict()
        value = True
        support = self.support(u)
        if care_vars is None:
            care_vars = support
        missing = {v for v in support if v not in care_vars}
        if missing:
            logger.warning((
                'Missing bits:  '
                'support - care_vars = {missing}').format(
                    missing=missing))
        for cube in self._sat_iter(u, cube, value):
            for m in _enumerate_minterms(cube, care_vars):
                yield m

    def _sat_iter(self, u, cube, value):
        """Recurse to enumerate models."""
        if u < 0:
            value = not value
        # terminal ?
        if abs(u) == 1:
            if value:
                cube = {
                    self._level_to_var[i]: v
                    for i, v in items(cube)}
                yield cube
            return
        # non-terminal
        i, v, w = self._succ[abs(u)]
        d0 = dict(cube)
        d0[i] = False
        d1 = dict(cube)
        d1[i] = True
        for x in self._sat_iter(v, d0, value):
            yield x
        for x in self._sat_iter(w, d1, value):
            yield x

    def assert_consistent(self):
        """Raise `AssertionError` if not a valid BDD."""
        for root in self.roots:
            assert abs(root) in self._succ, root
        # inverses
        succ_keys = set(self._succ)
        succ_values = set(self._succ.values())
        pred_keys = set(self._pred)
        pred_values = set(self._pred.values())
        assert succ_keys == pred_values, (
            succ_keys.symmetric_difference(pred_values))
        assert pred_keys == succ_values, (
            pred_keys.symmetric_difference(succ_values))
        # uniqueness
        n = len(succ_keys)
        n_ = len(succ_values)
        assert n == n_, (n - n_)
        for u, (i, v, w) in items(self._succ):
            assert isinstance(i, int), i
            # terminal ?
            if v is None:
                assert w is None, w
                continue
            else:
                assert abs(v) in self._succ, v
            if w is None:
                assert v is None, v
                continue
            else:
                assert w >= 0, w  # "high" is regular edge
                assert w in self._succ, w
            # var order should increase
            for x in (v, w):
                ix, _, _ = self._succ[abs(x)]
                assert i < ix, (u, i)
            # `_pred` contains inverse of `_succ`
            assert (i, v, w) in self._pred, (i, v, w)
            assert self._pred[(i, v, w)] == u, u
            # reference count
            assert u in self._ref, u
            assert self._ref[u] >= 0, self._ref[u]
        return True

    @_try_to_reorder
    def add_expr(self, e):
        return _parser.add_expr(e, self)

    def to_expr(self, u):
        assert u in self, u
        return self._to_expr(u)

    def _to_expr(self, u):
        if u == 1:
            return 'TRUE'
        if u == -1:
            return 'FALSE'
        i, v, w = self._succ[abs(u)]
        var = self._level_to_var[i]
        p = self._to_expr(v)
        q = self._to_expr(w)
        # pure var ?
        if p == 'FALSE' and q == 'TRUE':
            s = var
        else:
            s = 'ite({var}, {q}, {p})'.format(var=var, p=p, q=q)
        # complemented ?
        if u < 0:
            s = '(~ {s})'.format(s=s)
        return s

    def apply(self, op, u, v=None, w=None):
        assert abs(u) in self, u
        assert v is None or abs(v) in self, v
        assert w is None or abs(w) in self, w
        if op in ('~', 'not', '!'):
            assert v is None, v
            assert w is None, w
            return -u
        elif op in ('or', r'\/', '|', '||'):
            assert v is not None, v
            assert w is None, w
            return self.ite(u, 1, v)
        elif op in ('and', '/\\', '&', '&&'):
            assert v is not None, v
            assert w is None, w
            return self.ite(u, v, -1)
        elif op in ('xor', '^'):
            assert v is not None, v
            assert w is None, w
            return self.ite(u, -v, v)
        elif op in ('=>', '->', 'implies'):
            assert v is not None, v
            assert w is None, w
            return self.ite(u, v, 1)
        elif op in ('<=>', '<->', 'equiv'):
            assert v is not None, v
            assert w is None, w
            return self.ite(u, v, -v)
        elif op in ('diff', '-'):
            assert v is not None, v
            assert w is None, w
            return self.ite(u, -v, -1)
        elif op in (r'\A', 'forall'):
            assert v is not None, v
            assert w is None, w
            qvars = self.support(u)
            return self.quantify(v, qvars, forall=True)
        elif op in (r'\E', 'exists'):
            assert v is not None, v
            assert w is None, w
            qvars = self.support(u)
            return self.quantify(v, qvars, forall=False)
        elif op == 'ite':
            assert v is not None, v
            assert w is not None, w
            return self.ite(u, v, w)
        else:
            raise Exception(
                'unknown operator "{op}"'.format(op=op))

    def _add_int(self, i):
        assert i in self, i
        return i

    @_try_to_reorder
    def cube(self, dvars):
        if not isinstance(dvars, dict):
            dvars = {k: True for k in dvars}
        # `dvars` keys can be var names or levels
        r = self.true
        for var, val in items(dvars):
            u = self.var(var)
            u = u if val else -u
            r = self.apply('and', u, r)
        return r

    def dump(self, filename, roots=None,
             filetype=None, **kw):
        if filetype is None:
            name = filename.lower()
            if name.endswith('.pdf'):
                filetype = 'pdf'
            elif name.endswith('.png'):
                filetype = 'png'
            elif name.endswith('.svg'):
                filetype = 'svg'
            elif name.endswith('.p'):
                filetype = 'pickle'
            else:
                raise Exception((
                    'cannot infer file type '
                    'from extension of file '
                    'name "{f}"').format(
                        f=filename))
        if filetype in ('pdf', 'png', 'svg'):
            self._dump_figure(roots, filename,
                              filetype, **kw)
        elif filetype == 'pickle':
            self._dump_bdd(roots, filename, **kw)
        else:
            raise Exception(
                'unknown file type "{t}"'.format(
                    t=filetype))

    def _dump_figure(self, roots, filename,
                     filetype, **kw):
        """Write BDDs to `filename` as figure."""
        g = to_pydot(roots, self)
        if filetype == 'pdf':
            g.write_pdf(filename, **kw)
        elif filetype == 'png':
            g.write_png(filename, **kw)
        elif filetype == 'svg':
            g.write_svg(filename, **kw)
        else:
            raise Exception(
                'Unknown file type of "{f}"'.format(
                    f=filename))

    def _dump_bdd(self, roots, filename, **kw):
        """Write BDDs to `filename` as pickle."""
        if roots is None:
            nodes = self._succ
        else:
            nodes = self.descendants(roots)
        succ = ((k, self._succ[k]) for k in nodes)
        d = dict(
            vars=self.vars,
            succ=dict(succ))
        kw.setdefault('protocol', 2)
        with open(filename, 'wb') as f:
            pickle.dump(d, f, **kw)

    def load(self, filename, levels=True):
        name = filename.lower()
        if name.endswith('.p'):
            return self._load_pickle(
                filename, levels=levels)
        else:
            raise ValueError(
                'Unknown file type of "{f}"'.format(
                    f=filename))

    def _load_pickle(self, filename, levels=True):
        with open(filename, 'rb') as f:
            d = pickle.load(f)
        var2level = d['vars']
        succ = d['succ']
        n = len(var2level)
        level_map = dict()
        # level_map[n] = len(self.vars)
        for var, i in items(var2level):
            assert 0 <= i < n, (i, n)
            if var not in self.vars:
                logger.warning(
                    'variable "{var}" added'.format(
                        var=var))
            if levels:
                j = self.add_var(var, i)
            else:
                j = self.add_var(var)
            level_map[i] = j
        umap = dict()
        for u in succ:
            # already added ?
            if u in umap:
                continue
            # add
            self._load(u, succ, umap, level_map)
        return umap

    def _load(self, u, succ, umap, level_map):
        """Recurse to load BDD `u` from `succ`."""
        # terminal ?
        if abs(u) == 1:
            return u
        # memoized ?
        if u in umap:
            r = umap[abs(u)]
            assert r > 0, r
            if u < 0:
                r = -r
            return r
        i, v, w = succ[abs(u)]
        j = level_map[i]
        p = self._load(v, succ, umap, level_map)
        q = self._load(w, succ, umap, level_map)
        r = self.find_or_add(j, p, q)
        assert r > 0, r
        umap[abs(u)] = r
        if u < 0:
            r = -r
        return r

    def _dump_manager(self, filename, **kw):
        """Write `BDD` to `filename` as pickle."""
        d = dict(
            vars=self.vars,
            max_nodes=self.max_nodes,
            roots=self.roots,
            pred=self._pred,
            succ=self._succ,
            ref=self._ref,
            min_free=self._min_free)
        kw.setdefault('protocol', 2)
        with open(filename, 'wb') as f:
            pickle.dump(d, f, **kw)

    @classmethod
    def _load_manager(cls, filename):
        """Load `BDD` from pickle file `filename`."""
        with open(filename, 'rb') as f:
            d = pickle.load(f)
        bdd = cls(d['vars'])
        bdd.max_nodes = d['max_nodes']
        bdd.roots = d['roots']
        bdd._pred = d['pred']
        bdd._succ = d['succ']
        bdd._ref = d['ref']
        bdd._min_free = d['min_free']
        return bdd

    @property
    def false(self):
        return -1

    @property
    def true(self):
        return 1


def _enumerate_minterms(cube, bits):
    """Generator of complete assignments in `cube`.

    @type cube: `dict`
    @param bits: enumerate over those absent from `cube`
    @type bits: `set`
    @rtype: generator of `dict(str: bool)`
    """
    assert cube is not None
    assert bits is not None
    bits = set(bits).difference(cube)
    # fix order
    bits = list(bits)
    n = len(bits)
    for i in xrange(2**n):
        values = bin(i).lstrip('-0b').zfill(n)
        model = {k: bool(int(v)) for k, v in zip(bits, values)}
        model.update(cube)
        assert len(model) >= len(bits), (model, bits)
        assert len(model) >= len(cube), (model, cube)
        yield model


def _assert_isomorphic_orders(old, new, support):
    """Raise `AssertionError` if not isomorphic.

    @param old, new: levels
    @param support: `old` and `new` compared after
        restriction to `support`.
    """
    _assert_valid_ordering(old)
    _assert_valid_ordering(new)
    s = {k: v for k, v in items(old) if k in support}
    t = {k: v for k, v in items(new) if k in support}
    old = sorted(s, key=s.get)
    new = sorted(t, key=t.get)
    assert old == new, (old, new)


def _assert_valid_ordering(levels):
    """Check that `levels` is well-formed.

    - bijection
    - contiguous levels
    """
    # `levels` is a mapping -> each var : single level
    assert isinstance(levels, Mapping), levels
    # levels are contiguous integers ?
    n = len(levels)
    numbers = set(_compat.values(levels))
    numbers_ = set(xrange(n))
    assert numbers == numbers_, (n, numbers)


def rename(u, bdd, dvars):
    """Rename variables of node `u`.

    @param dvars: `dict` from variabe names to variable names
    """
    assert abs(u) in bdd, u
    # nothing to rename ?
    if not dvars:
        return u
    # map variable names to levels
    levels = bdd.vars
    dvars = {
        levels[var]: levels[dvars.get(var, var)]
        for var in bdd.vars}
    cache = dict()
    return _copy_bdd(u, dvars, bdd, bdd, cache)


def _assert_valid_rename(u, bdd, dvars):
    """Raise `AssertionError` if rename of non-adjacent vars.

    @param dvars: `dict` that maps var levels to var levels
    """
    if not dvars:
        return
    # valid levels ?
    bdd.var_at_level(0)
    # pairwise disjoint ?
    _assert_no_overlap(dvars)


def _all_adjacent(dvars, bdd):
    """Return `True` if all levels in `dvars` are adjacent."""
    for v, vp in items(dvars):
        if not _adjacent(v, vp, bdd):
            return False
    return True


def _adjacent(i, j, bdd):
    """Raise `AssertionError` if level `i` not adjacent to `j`."""
    if abs(i - j) == 1:
        return True
    logger.warning((
        'level {i} ("{x}") not adjacent to '
        'level {j} ("{y}")').format(
            i=i,
            j=j,
            x=bdd.var_at_level(i),
            y=bdd.var_at_level(j)))
    return False


def _assert_no_overlap(d):
    """Raise `AssertionError` if keys and values overlap."""
    assert not any((k in d) for k in _compat.values(d))


def image(trans, source, rename, qvars, bdd, forall=False):
    """Return set reachable from `source` under `trans`.

    @param trans: transition relation
    @param source: the transition must start in this set
    @param rename: `dict` that maps primed variables in
        `trans` to unprimed variables in `trans`.
        Applied to the quantified conjunction of `trans` and `source`.
    @param qvars: `set` of variables to quantify
    @param bdd: `BDD`
    @param forall: if `True`,
        then quantify `qvars` universally,
        else existentially.
    """
    # map to levels
    qvars = bdd._map_to_level(qvars)
    rename = {
        bdd.vars.get(k, k): bdd.vars.get(v, v)
        for k, v in items(rename)}
    # init
    cache = dict()
    rename_u = rename
    rename_v = None
    # no overlap and neighbors
    _assert_no_overlap(rename)
    if not _all_adjacent(rename, bdd):
        logger.warning('BDD.image: not all vars adjacent')
    # unpriming maps to qvars or outside support of conjunction
    s = bdd.support(trans, as_levels=True)
    s.update(bdd.support(source, as_levels=True))
    s.difference_update(qvars)
    s.intersection_update(_compat.values(rename))
    assert not s, s
    return _image(trans, source, rename_u, rename_v,
                  qvars, bdd, forall, cache)


def preimage(trans, target, rename, qvars, bdd, forall=False):
    """Return set that can reach `target` under `trans`.

    Also known as the "relational product".
    Assumes that primed and unprimed variables are neighbors.
    Variables are identified by their levels.

    @param trans: transition relation
    @param target: the transition must end in this set
    @param rename: `dict` that maps (unprimed) variables in `target` to
        (primed) variables in `trans`
    @param qvars: `set` of variables to quantify
    @param bdd: `BDD`
    @param forall: if `True`,
        then quantify `qvars` universally,
        else existentially.
    """
    # map to levels
    qvars = bdd._map_to_level(qvars)
    rename = {
        bdd.vars.get(k, k): bdd.vars.get(v, v)
        for k, v in items(rename)}
    # init
    cache = dict()
    rename_u = None
    rename_v = rename
    # check
    _assert_valid_rename(target, bdd, rename)
    return _image(trans, target, rename_u, rename_v,
                  qvars, bdd, forall, cache)


def _image(u, v, umap, vmap, qvars, bdd, forall, cache):
    """Recursive (pre)image computation.

    Renaming requires that in each pair
    the variables are adjacent.

    @param u, v: nodes
    @param umap: renaming of variables in `u`
        that occurs after conjunction of `u` with `v`
        and quantification.
    @param vmap: renaming of variables in `v`
        that occurs before conjunction with `u`.
    """
    # controlling values for conjunction ?
    if u == -1 or v == -1:
        return -1
    if u == 1 and v == 1:
        return 1
    # already computed ?
    t = (u, v)
    w = cache.get(t)
    if w is not None:
        return w
    # recurse (descend)
    iu, _, _ = bdd._succ[abs(u)]
    jv, _, _ = bdd._succ[abs(v)]
    if vmap is None:
        iv = jv
    else:
        iv = vmap.get(jv, jv)
    z = min(iu, iv)
    u0, u1 = bdd._top_cofactor(u, z)
    v0, v1 = bdd._top_cofactor(v, jv + z - iv)
    p = _image(u0, v0, umap, vmap, qvars, bdd, forall, cache)
    q = _image(u1, v1, umap, vmap, qvars, bdd, forall, cache)
    # quantified ?
    if z in qvars:
        if forall:
            r = bdd.ite(p, q, -1)  # conjoin
        else:
            r = bdd.ite(p, 1, q)  # disjoin
    else:
        if umap is None:
            m = z
        else:
            m = umap.get(z, z)
        g = bdd.find_or_add(m, -1, 1)
        r = bdd.ite(g, q, p)
    cache[t] = r
    return r


def reorder(bdd, order=None):
    """Apply Rudell's sifting algorithm to reduce `bdd` size.

    Reordering invokes the garbage collector,
    so be sure to `incref` nodes that should remain.

    @param order: if given, then swap vars to obtain this order.
    @type order: `dict(str: int)` from each var to a level
    @type bdd: `BDD`
    """
    len_before = len(bdd)
    if order is None:
        _apply_sifting(bdd)
    else:
        _sort_to_order(bdd, order)
    len_after = len(bdd)
    logger.info(
        'Reordering changed `BDD` manager size '
        'from {a} to {b} nodes.'.format(
            a=len_before, b=len_after))


def _apply_sifting(bdd):
    """Apply Rudell's sifting algorithm."""
    bdd.collect_garbage()
    n = len(bdd)
    # using `set` injects some randomness
    levels = bdd._levels()
    names = set(bdd.vars)
    for var in names:
        k = _reorder_var(bdd, var, levels)
        m = len(bdd)
        logger.info(
            '{m} nodes for variable "{v}" at level {k}'.format(
                m=m, v=var, k=k))
    assert m <= n, (m, n)
    logger.info('final variable order:\b{v}'.format(v=bdd.vars))


def _reorder_var(bdd, var, levels):
    """Reorder by sifting a variable `var`.

    @type bdd: `BDD`
    @type var: `str`
    """
    assert var in bdd.vars, (var, bdd.vars)
    m = len(bdd)
    n = len(bdd.vars) - 1
    assert n >= 0, n
    start = 0
    end = n
    level = bdd.level_of_var(var)
    # closer to bottom ?
    if (2 * level) >= n:
        start, end = end, start
    _shift(bdd, level, start, levels)
    sizes = _shift(bdd, start, end, levels)
    k = min(sizes, key=sizes.get)
    _shift(bdd, end, k, levels)
    m_ = len(bdd)
    assert sizes[k] == m_, (sizes[k], m_)
    assert m_ <= m, (m_, m)
    return k


def _shift(bdd, start, end, levels):
    """Shift level `start` to become `end`, by swapping.

    @type bdd: `BDD`
    @type start, end: `0 <= int < len(bdd.vars)`
    """
    m = len(bdd.vars)
    assert 0 <= start < m, (start, m)
    assert 0 <= end < m, (end, m)
    sizes = dict()
    d = 1 if start < end else -1
    for i in xrange(start, end, d):
        j = i + d
        oldn, n = bdd.swap(i, j, levels)
        sizes[i] = oldn
        sizes[j] = n
    return sizes


def _sort_to_order(bdd, order):
    """Swap variables to obtain the given `order` of variables.

    @type order: `dict`
    """
    # TODO: use min number of swaps
    assert len(bdd.vars) == len(order)
    m = 0
    levels = bdd._levels()
    n = len(order)
    for k in xrange(n):
        for i in xrange(n - 1):
            for root in bdd.roots:
                assert root in bdd
            x = bdd.var_at_level(i)
            y = bdd.var_at_level(i + 1)
            p = order[x]
            q = order[y]
            if p > q:
                bdd.swap(i, i + 1, levels)
                m += 1
                logger.debug(
                    'swap: {p} with {q}, {i}'.format(p=p, q=q, i=i))
            if logger.getEffectiveLevel() < logging.DEBUG:
                bdd.assert_consistent()
    logger.info('total swaps: {m}'.format(m=m))


def reorder_to_pairs(bdd, pairs):
    """Reorder variables to make adjacent the given pairs.

    @type pairs: `dict` of variables as `str`
    """
    m = 0
    levels = bdd._levels()
    for x, y in items(pairs):
        jx = bdd.level_of_var(x)
        jy = bdd.level_of_var(y)
        k = abs(jx - jy)
        assert k > 0, (jx, jy)
        # already adjacent ?
        if k == 1:
            continue
        # shift x next to y
        if jx > jy:
            jx, jy = jy, jx
        _shift(bdd, start=jx, end=jy - 1, levels=levels)
        m += k
        logger.debug('shift by {k}'.format(k=k))
    logger.info('total swaps: {m}'.format(m=m))


def copy_bdd(u, from_bdd, to_bdd):
    """Copy BDD of node `u` `from_bdd` `to_bdd`.

    @param u: node in `from_bdd`
    @type from_bdd, to_bdd: `BDD`
    """
    if from_bdd is to_bdd:
        logger.warning(
            'copying node to same BDD manager')
        return u
    level_map = {
        from_bdd.level_of_var(var): to_bdd.level_of_var(var)
        for var in from_bdd.vars if var in to_bdd.vars}
    cache = dict()
    r = _copy_bdd(u, level_map, from_bdd, to_bdd, cache)
    return r


def _copy_bdd(u, level_map, old_bdd, bdd, cache):
    """Recurse to copy nodes from `old_bdd` to `bdd`.

    @param u: node in `old_bdd`
    @type level_map: `dict` that maps old to new levels
    @type old_bdd, bdd: `BDD`
    @type cache: `dict`
    """
    # terminal ?
    if abs(u) == 1:
        return u
    # non-terminal
    # memoized ?
    r = cache.get(abs(u))
    if r is not None:
        assert r > 0, r
        # complement ?
        if u < 0:
            r = -r
        return r
    # recurse
    jold, v, w = old_bdd._succ[abs(u)]
    p = _copy_bdd(v, level_map, old_bdd, bdd, cache)
    q = _copy_bdd(w, level_map, old_bdd, bdd, cache)
    assert p * v > 0, (p, v)
    assert q > 0, q
    # map this level
    jnew = level_map[jold]
    g = bdd.find_or_add(jnew, -1, 1)
    r = bdd.ite(g, q, p)
    # memoize
    assert r > 0, r
    cache[abs(u)] = r
    # complement ?
    if u < 0:
        r = -r
    return r


def _flip(r, u):
    """Flip `r` if `u` is negated, else identity."""
    return -r if u < 0 else r


def to_nx(bdd, roots):
    """Convert node references in `roots` to `networkx.MultiDiGraph`.

    The resulting graph has:

      - nodes labeled with:
        - `level`: `int` from 0 to `len(bdd)`
      - edges labeled with:
        - `value`: `False` for low/"else", `True` for high/"then"
        - `complement`: `True` if target node is negated

    @type bdd: `BDD`
    @type roots: iterable of edges, each a signed `int`
    @rtype: `networkx.MultiDiGraph`
    """
    import networkx as nx
    g = nx.MultiDiGraph()
    for root in roots:
        assert abs(root) in bdd, root
        Q = {root}
        while Q:
            u = Q.pop()
            u = abs(u)
            i, v, w = bdd._succ[u]
            assert u > 0, u
            g.add_node(u, level=i)
            # terminal ?
            if v is None or w is None:
                assert w is None, w
                assert v is None, v
                continue
            # non-terminal
            r = (v < 0)
            v = abs(v)
            w = abs(w)
            if v not in g:
                Q.add(v)
            if w not in g:
                Q.add(w)
            assert v > 0, v
            assert w > 0, w
            g.add_edge(u, v, value=False, complement=r)
            g.add_edge(u, w, value=True, complement=False)
    return g


def to_pydot(roots, bdd):
    """Convert `BDD` to pydot graph.

    Nodes are ordered by variable levels in support.
    Edges to low successors are dashed.
    Complemented edges are labeled with "-1".

    Nodes not reachable from `roots`
    are ignored, unless `roots is None`.

    The roots are plotted as external references,
    with complemented edges where applicable.

    @type roots: container of BDD nodes
    @type bdd: `BDD`
    """
    import pydot
    # all nodes ?
    if roots is None:
        nodes = bdd._succ
        roots = list()
    else:
        nodes = bdd.descendants(roots)
    # show only levels in aggregate support
    levels = {bdd._succ[abs(u)][0] for u in nodes}
    assert bdd._succ[1][0] in levels
    g = pydot.Dot('bdd', graph_type='digraph')
    skeleton = list()
    subgraphs = dict()
    # layer for external BDD references
    layers = [-1] + sorted(levels)
    # add nodes for BDD levels
    for i in layers:
        h = pydot.Subgraph('', rank='same')
        g.add_subgraph(h)
        subgraphs[i] = h
        # add phantom node
        u = 'L{i}'.format(i=i)
        skeleton.append(u)
        if i == -1:
            # layer for external BDD references
            label = 'ref'
        else:
            # BDD level
            label = str(i)
        nd = pydot.Node(name=u, label=label, shape='none')
        h.add_node(nd)
    # auxiliary edges for ranking
    for i, u in enumerate(skeleton[:-1]):
        v = skeleton[i + 1]
        e = pydot.Edge(str(u), str(v), style='invis')
        g.add_edge(e)
    # add nodes
    idx2var = {k: v for v, k in items(bdd.vars)}
    # BDD nodes
    def f(x):
        return str(abs(x))
    for u in nodes:
        i, v, w = bdd._succ[abs(u)]
        # terminal ?
        if v is None:
            var = str(bool(abs(u)))
        else:
            var = idx2var[i]
        su = f(u)
        label = '{var}-{u}'.format(var=var, u=su)
        nd = pydot.Node(name=su, label=label)
        # add node to subgraph for level i
        h = subgraphs[i]
        h.add_node(nd)
        # add edges
        if v is None:
            continue
        sv = f(v)
        sw = f(w)
        vlabel = '-1' if v < 0 else ' '
        e = pydot.Edge(su, sv, style='dashed', taillabel=vlabel)
        g.add_edge(e)
        e = pydot.Edge(su, sw, style='solid')
        g.add_edge(e)
    # external references to BDD nodes
    for u in roots:
        i, _, _ = bdd._succ[abs(u)]
        su = 'ref' + str(u)
        label = '@' + str(u)
        nd = pydot.Node(name=su, label=label)
        # add node to subgraph for level -1
        h = subgraphs[-1]
        h.add_node(nd)
        # add edge from external reference to BDD node
        assert u is not None
        sv = str(abs(u))
        vlabel = '-1' if u < 0 else ' '
        e = pydot.Edge(su, sv, style='dashed', taillabel=vlabel)
        g.add_edge(e)
    return g
