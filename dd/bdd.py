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
from collections import Mapping
from itertools import tee
try:  # python3 compat
    from itertools import izip
except ImportError:
    izip = zip
import logging
import pickle
import sys
try:
    sys.maxint
except AttributeError:
    sys.maxint = sys.maxsize
from dd import _parser
# inline:
# import networkx
# import pydot

if not 'iteritems' in dict.__dict__: # python3 compat
    class _dict(dict):
        def iteritems(self):
            return self.items()
    dict = _dict

try: # python3 compat
    xrange(1)
except NameError:
    xrange = range


logger = logging.getLogger(__name__)


class BDD(object):
    """Shared ordered binary decision diagram.

    The terminal node is 1.
    Complemented edges are represented as negative integers.
    Values returned by methods are edges, possibly complemented.

    Attributes:
      - `ordering`: `dict` mapping `variables` to `int` levels
      - `roots`: (optional) edges used by `to_nx`.
      - `max_nodes`: raise `Exception` if this limit is reached.
        The default value is `sys.max_int`. Increase it if needed.

    To ensure that the target node of a returned edge
    is not garbage collected during reordering,
    increment its reference counter:

    `bdd.incref(edge)`

    To ensure that `ite` maintains reducedness add new
    nodes using `find_or_add` to keep the table updated,
    or call `update_predecessors` prior to calling `ite`.
    """

    def __init__(self, ordering=None):
        self._pred = dict()  # (i, low, high) -> u
        self._succ = dict()  # u -> (i, low, high)
        self._ref = dict()  # reference counters
        self._min_free = 2  # all smaller positive integers used
        self._ite_table = dict()  # (cond, high, low)
        # TODO: deprecate `self.ordering`
        self.ordering = dict()
        self.vars = self.ordering
        self._level_to_var = dict()
        ordering = dict(ordering or {})
        _assert_valid_ordering(ordering)
        for var, level in ordering.iteritems():
            self.add_var(var, level)
        self.roots = set()
        self.max_nodes = sys.maxint

    def __copy__(self):
        bdd = BDD(self.ordering)
        bdd._pred = dict(self._pred)
        bdd._succ = dict(self._succ)
        bdd._ref = dict(self._ref)
        bdd._min_free = self._min_free
        bdd.roots = set(self.roots)
        bdd.max_nodes = self.max_nodes
        return bdd

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
            'var ordering: {self.ordering}\n'
            'roots: {self.roots}\n').format(self=self)

    def _init_terminal(self, i):
        self._succ[1] = (i, None, None)
        self._ref[1] = 0

    def incref(self, u):
        """Increment reference count of node `u`."""
        self._ref[abs(u)] += 1

    def decref(self, u):
        """Decrement reference count of node `u`, with 0 as min."""
        if self._ref[abs(u)] > 0:
            self._ref[abs(u)] -= 1

    def ref(self, u):
        """Return reference count of edge `u`."""
        return self._ref[abs(u)]

    def add_var(self, var, level=None):
        """Add a variable named `var` at `level`.

        If `level` is absent, then add at bottom.
        Raise `Exception` if:
            - `var` exists at different level, or
            - `level` is occupied.

        Currently, `add_var` must be called
        *only* before adding any nodes.
        In the future, this will change.

        @type level: `int`
        """
        # var already exists ?
        if var in self.ordering:
            k = self.ordering[var]
            if level is not None:
                assert level == k, (var, k, level)
            return k
        # level occupied ?
        try:
            other = self.var_at_level(level)
        except AssertionError:
            other = None
        assert other is None, (
            'level {level} occupied'.format(level=level))
        # create var
        if level is None:
            level = len(self.ordering)
        self.ordering[var] = level
        self._level_to_var[level] = var
        self._init_terminal(len(self.ordering))
        return level

    def var(self, var):
        """Return node for variable named `var`."""
        assert var in self.ordering, (
            'undefined variable "{v}", '
            'known variables are:\n {d}').format(
                v=var, d=self.ordering)
        j = self.ordering[var]
        u = self.find_or_add(j, -1, 1)
        return u

    def var_at_level(self, level):
        """Return variable with `level`."""
        if level not in self._level_to_var:
            raise AssertionError(
                'level {j} does not exist'.format(j=level))
        return self._level_to_var[level]

    def level_of_var(self, var):
        """Return level of `var`, or `None`."""
        return self.ordering.get(var)

    def _map_to_level(self, d):
        """Map keys of `d` to variable levels.

        If `d` is an iterable but not a mapping,
        then an iterable is returned.
        The mapping is `self.ordering`.
        """
        if not d:
            return d
        # are keys variable names ?
        u = next(iter(d))
        if u not in self.ordering:
            return d
        if isinstance(d, Mapping):
            r = {
                self.ordering[var]: bool(val)
                for var, val in d.iteritems()}
        else:
            r = {self.ordering[k] for k in d}
        return r

    def _top_var(self, *nodes):
        return min(map(lambda x: self._succ[abs(x)][0], nodes))

    def descendants(self, u):
        """Return BDD nodes reachable from node `u`.

        Node `u` is included.
        Nodes are represented as positive integers.
        """
        assert u in self, u
        nodes = set()
        self._descendants(u, nodes)
        assert nodes
        return nodes

    def _descendants(self, u, nodes):
        """Recurse to count number of BDD nodes."""
        # visited ?
        r = abs(u)
        if r in nodes:
            return
        nodes.add(r)
        # terminal ?
        if r == 1:
            return
        # recurse
        _, v, w = self._succ[r]
        self._descendants(v, nodes)
        self._descendants(w, nodes)

    def evaluate(self, u, values):
        """Return value of node `u` for evaluation `values`.

        @param values: (partial) mapping from `variables` to values
            keys can be variable names as `str` or levels as `int`.
            Mapping should be complete with respect to `u`.
        @type values: `dict`
        """
        assert abs(u) in self, u
        values = self._map_to_level(values)
        return self._evaluate(u, values)

    def _evaluate(self, u, values):
        """Recurse to compute value."""
        if abs(u) == 1:
            return u
        i, v, w = self._succ[abs(u)]
        if values[i]:
            r = self._evaluate(w, values)
        else:
            r = self._evaluate(v, values)
        if u < 0:
            return -r
        else:
            return r

    def is_essential(self, u, var):
        """Return `True` if `var` is essential for node `u`.

        @param var: level in `ordering`
        @type var: `int`
        """
        i = self.ordering.get(var)
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
        """Return variables that node `u` depends on.

        @param as_levels: if `True`, then return variables
            as integers, insted of strings
        @rtype: `set`
        """
        levels = set()
        nodes = set()
        self._support(u, levels, nodes)
        if as_levels:
            return levels
        return {self.var_at_level(i) for i in levels}

    def _support(self, u, levels, nodes):
        """Recurse to collect variables in support."""
        # exhausted all vars ?
        if len(levels) == len(self.ordering):
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
            n = len(self.ordering) - 1
        else:
            n = len(self.ordering)
        for i in xrange(n, -1, -1):
            for u, (j, v, w) in self._succ.iteritems():
                if i != j:
                    continue
                yield u, i, v, w

    def _levels(self):
        """Return `dict` from levels to `set`s of nodes."""
        n = len(self.ordering)
        levels = {i: set() for var, i in self.ordering.iteritems()}
        levels[n] = set()
        for u, (i, v, w) in self._succ.iteritems():
            levels[i].add(u)
        levels.pop(n)
        return levels

    def reduction(self):
        """Return copy reduced with respect to `self.ordering`.

        Not to be used for large BDDs.
        Instead, construct them directly reduced.
        """
        # terminals
        bdd = BDD(self.ordering)
        umap = {-1: -1, 1: 1}
        # non-terminals
        for u, i, v, w in self.levels(skip_terminals=True):
            p, q = umap[v], umap[w]
            r = bdd.find_or_add(i, p, q)
            umap[u] = r
            if u in self.roots:
                bdd.roots.add(r)
        return bdd

    def compose(self, f, var, g):
        """Return f(x_var=g).

        @param f, g: nodes
        @param var: variable name
        @param cache: stores intermediate results
        """
        j = self.level_of_var(var)
        cache = dict()
        u = self._compose(f, j, g, cache)
        return u

    def _compose(self, f, j, g, cache):
        # terminal or exhausted valuation ?
        if abs(f) == 1:
            return f
        # cached ?
        if (f, g) in cache:
            return cache[(f, g)]
        # independent of j ?
        i, v, w = self._succ[abs(f)]
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

    def ite(self, g, u, v):
        """Return node for if-then-else of `g`, `u` and `v`.

        @param u: high
        @param v: low
        @type g, u, v: `int`
        @rtype: `int`
        """
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
        p = self.ite(g0, u0, v0)
        q = self.ite(g1, u1, v1)
        w = self.find_or_add(z, p, q)
        # cache
        self._ite_table[r] = w
        return w

    def _top_cofactor(self, u, i):
        """Return restriction for assignment to single variable.

        @param u: node
        @param i: variable level
        @param value: assignment to variable `i`
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

    def cofactor(self, u, values):
        """Return restriction of `u` to valuation `values`.

        @param u: node
        @param values: `dict` that maps var levels to values
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

    def find_or_add(self, i, v, w):
        """Return a node at level `i` with successors `v, w`.

        If one exists, it is quickly found in the cached table.

        @param i: level in `range(n_vars - 1)`
        @param v: low edge
        @param w: high edge
        """
        assert 0 <= i < len(self.ordering), i
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

    def _next_free_int(self, start, debug=False):
        """Return the smallest unused integer larger than `start`."""
        for i in xrange(start, self.max_nodes):
            if i not in self._succ:
                if debug:
                    for j in xrange(1, start + 1):
                        assert j in self, j
                return i
        raise Exception('full: reached `self.max_nodes` nodes.')

    def collect_garbage(self, roots=None):
        """Recursively remove nodes with zero reference count.

        Removal starts from the nodes in `roots` with zero
        reference count. If no `roots` are given, then
        all nodes are scanned for zero reference counts.

        @type roots: `set`, Caution: it is modified
        """
        logger.debug('++ collecting BDD garbage')
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
        logger.debug(
            '-- done: colected {n} - {m} = {k} nodes.'.format(
                n=n, m=m, k=k))

    def update_predecessors(self):
        """Update table that maps (level, low, high) to nodes."""
        for u, t in self._succ.iteritems():
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
        x = self.ordering.get(x, x)
        y = self.ordering.get(y, y)
        assert 0 <= x < len(self.ordering), x
        assert 0 <= y < len(self.ordering), y
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
        for u, (v, w) in levels[y].iteritems():
            i, _, _ = self._succ[u]
            assert i == y, (i, y)
            r = (x, v, w)
            self._succ[u] = r
            assert r not in self._pred, r
            self._pred[r] = u
        # move level x down
        # first x nodes independent of y
        done = set()
        for u, (v, w) in levels[x].iteritems():
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
        for u, (v, w) in levels[x].iteritems():
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
        # swap x and y in ordering
        vx = self.var_at_level(x)
        self.ordering[vx] = y
        vy = self.var_at_level(y)
        self.ordering[vy] = x
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
        """Return low and high, or `u` itself, if terminal."""
        i, v, w = self._succ[abs(u)]
        if abs(u) == 1:
            return (i, u, u)
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

    def sat_len(self, u):
        """Return number of models of node `u`."""
        assert abs(u) in self, u
        r = self._sat_len(u, d=dict())
        i, _, _ = self._succ[abs(u)]
        return r * 2**i

    def _sat_len(self, u, d):
        """Recurse to compute the number of models."""
        i, _, _ = self._succ[abs(u)]
        # memoized ?
        if abs(u) in d:
            n = d[abs(u)]
            # complement ?
            if u < 0:
                n = 2**(len(self.ordering) - i) - n
            return n
        # terminal ?
        if u == 1:
            return 1
        if u == -1:
            return 0
        # non-terminal
        i, v, w = self._succ[abs(u)]
        nu = self._sat_len(v, d)
        nw = self._sat_len(w, d)
        iv, _, _ = self._succ[abs(v)]
        iw, _, _ = self._succ[w]
        # sum
        n = (nu * 2**(iv - i - 1) +
             nw * 2**(iw - i - 1))
        d[abs(u)] = n
        # complement ?
        if u < 0:
            n = 2**(len(self.ordering) - i) - n
        return n

    def sat_iter(self, u, full=False, care_bits=None):
        """Return generator over assignments.

        An assignment is `dict` that
        maps each variable to a `bool`.

        @param full: if `True`,
            then return complete assignments (minterms),
            otherwise (possibly) partial assignments (cubes).
        @param care_bits: if `full`, then enumerate
            only over these additional bits.

        @rtype: generator of `dict(str: bool)`
        """
        # empty ?
        if not self._succ:
            return
        # non-empty
        assert abs(u) in self._succ, u
        cube = dict()
        value = True
        if care_bits is None:
            care_bits = set(self.ordering)
        for cube in self._sat_iter(u, cube, value):
            if not full:
                yield cube
                continue
            # complete assignments
            for m in _enumerate_minterms(cube, care_bits):
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
                    for i, v in cube.iteritems()}
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
        for u, (i, v, w) in self._succ.iteritems():
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
            # 1-1 mapping
            assert (i, v, w) in self._pred, (i, v, w)
            assert self._pred[(i, v, w)] == u, u
            # reference count
            assert u in self._ref, u
            assert self._ref[u] >= 0, self._ref[u]
        return True

    def add_expr(self, e):
        """Return node for expression `e`, after adding it.

        If you would like to use your own parser,
        you can use utilities from `dd._parser`.

        @type expr: `str`
        """
        i = len(self.ordering)
        self._succ[1] = (i, None, None)
        self._ref[1] = 0
        return _parser.add_expr(e, self)

    def add_ast(self, t):
        raise Exception(
            '`dd.bdd.BDD.add_ast` moved to `dd._parser.add_ast`.')

    def to_expr(self, u):
        """Return a Boolean expression for node `u`."""
        assert u in self, u
        ind2var = {k: v for v, k in self.ordering.iteritems()}
        return self._to_expr(u, ind2var)

    def _to_expr(self, u, ind2var):
        if u == 1:
            return 'True'
        if u == -1:
            return 'False'
        i, v, w = self._succ[abs(u)]
        var = ind2var[i]
        p = self._to_expr(v, ind2var)
        q = self._to_expr(w, ind2var)
        # pure var ?
        if p == 'False' and q == 'True':
            s = var
        else:
            s = 'ite({var}, {q}, {p})'.format(var=var, p=p, q=q)
        # complemented ?
        if u < 0:
            s = '(! {s})'.format(s=s)
        return s

    def apply(self, op, u, v=None):
        """Apply Boolean connective `op` between nodes `u` and `v`.

        @type op: `str` in:
          - `'not', 'or', 'and', 'xor', 'implies', 'bimplies'`
          - `'!', '|', '||', '&', '&&', '^', '->', '<->'`
        @type u, v: nodes
        """
        assert abs(u) in self, u
        assert v is None or abs(v) in self, v
        if op in ('not', '!'):
            return -u
        elif op in ('or', '|', '||'):
            return self.ite(u, 1, v)
        elif op in ('and', '&', '&&'):
            return self.ite(u, v, -1)
        elif op in ('xor', '^'):
            return self.ite(u, -v, v)
        elif op in ('implies', '->'):
            return self.ite(u, v, 1)
        elif op in ('bimplies', '<->'):
            return self.ite(u, v, -v)
        elif op in ('diff', '-'):
            return self.ite(u, -v, -1)
        else:
            raise Exception(
                'unknown operator "{op}"'.format(op=op))

    def cube(self, dvars):
        """Return node for conjunction of literals in `dvars`.

        @param dvars: assignment of values to some variables
        @type dvars: `dict`
        """
        r = 1
        for var, val in dict(dvars).iteritems():
            i = self.ordering.get(var, var)
            u = self.find_or_add(i, -1, 1)
            if not val:
                u = -u
            r = self.apply('and', u, r)
        return r

    def dump(self, filename, filetype=None, **kw):
        """Write `BDD` to `filename` as pickle or PDF.

        The file type is inferred from the
        extension ".p" or ".pdf" (case insensitive),
        unless a `filetype` is explicitly given.

        @type filename: `str`
        @type filetype: `"pdf"` or `"pickle"`
        """
        if filetype is None:
            name = filename.lower()
            if name.endswith('.pdf'):
                filetype = 'pdf'
            elif name.endswith('.p'):
                filetype = 'pickle'
            else:
                raise Exception('file type not supported')
        if filetype == 'pdf':
            self._dump_pdf(filename, **kw)
        elif filetype == 'pickle':
            self._dump_pickle(filename, **kw)
        else:
            raise Exception(
                'unknown file type "{t}"'.format(t=filetype))

    def _dump_pdf(self, filename, **kw):
        """Write `BDD` to `filename` as PDF."""
        g = to_pydot(self)
        g.write_pdf(filename, **kw)

    def _dump_pickle(self, filename, **kw):
        """Write `BDD` to `filename` as pickle."""
        d = {
            'ordering': self.ordering,
            'max_nodes': self.max_nodes,
            'roots': self.roots,
            'pred': self._pred,
            'succ': self._succ,
            'ref': self._ref,
            'min_free': self._min_free}
        with open(filename, 'w') as f:
            pickle.dump(d, f, **kw)

    @classmethod
    def load(cls, filename):
        """Load `BDD` from pickle file `filename`."""
        with open(filename, 'r') as f:
            d = pickle.load(f)
        bdd = cls(d['ordering'])
        bdd.max_nodes = d['max_nodes']
        bdd.roots = d['roots']
        bdd._pred = d['pred']
        bdd._succ = d['succ']
        bdd._ref = d['ref']
        bdd._min_free = d['min_free']
        return bdd

    # !!! DO NOT MOVE up, because arg defaults affected
    @property
    def false(self):
        return -1

    @property
    def true(self):
        return 1


def _enumerate_minterms(cube, bits):
    """Generator of complete assignments in `cube`.

    @type cube: `dict`
    @param bits: enumerate over these care bits
    @rtype: generator of `dict(str: bool)`
    """
    assert cube is not None
    bits = set(bits).difference(cube)
    # fix order
    bits = list(bits)
    n = len(bits)
    for i in xrange(2**n):
        values = bin(i).lstrip('-0b').zfill(n)
        model = {k: bool(int(v)) for k, v in zip(bits, values)}
        model.update(cube)
        assert len(model) >= len(bits), (model, bits)
        yield model


def _assert_isomorphic_orders(old, new, support):
    """Raise `AssertionError` if not isomorphic.

    @param old, new: orderings
    @param support: `old` and `new` compared after
        restriction to `support`.
    """
    _assert_valid_ordering(old)
    _assert_valid_ordering(new)
    s = {k: v for k, v in old.iteritems() if k in support}
    t = {k: v for k, v in new.iteritems() if k in support}
    old = sorted(s, key=s.get)
    new = sorted(t, key=t.get)
    assert old == new, (old, new)


def _assert_valid_ordering(ordering):
    """Check that `ordering` is well-formed.

    - bijection
    - contiguous levels
    """
    # levels are contiguous integers ?
    n = len(ordering)
    levels = set(ordering.values())
    levels_ = set(xrange(n))
    assert levels == levels_, (n, levels)
    # contiguous levels -> each level : single var
    # ordering is a mapping -> each var : single level
    assert isinstance(ordering, Mapping), ordering


def rename(u, bdd, dvars):
    """Efficient rename to non-essential neighbors.

    @param dvars: `dict` from variabe levels to variable levels
        or from variable names to variable names
    """
    assert abs(u) in bdd, u
    # nothing to rename ?
    if not dvars:
        return u
    # map variable names to levels, if needed
    ordering = bdd.ordering
    k = next(iter(dvars))
    if k in ordering:
        dvars = {ordering[k]: ordering[v]
                 for k, v in dict(dvars).iteritems()}
    _assert_valid_rename(u, bdd, dvars)
    umap = dict()
    return _rename(u, bdd, dvars, umap)


def _rename(u, bdd, dvars, umap):
    """Recursive renaming, assuming `dvars` is valid."""
    # terminal ?
    if abs(u) == 1:
        return u
    # memoized ?
    r = umap.get(abs(u))
    if r is not None:
        # complement ?
        if u < 0:
            r = -r
        return r
    i, v, w = bdd._succ[abs(u)]
    p = _rename(v, bdd, dvars, umap)
    q = _rename(w, bdd, dvars, umap)
    # to be renamed ?
    z = dvars.get(i, i)
    r = bdd.find_or_add(z, p, q)
    # memoize
    assert r > 0, r
    umap[abs(u)] = r
    # complement ?
    if u < 0:
        r = -r
    return r


def _assert_valid_rename(u, bdd, dvars):
    """Raise `AssertionError` if rename of non-adjacent vars."""
    if not dvars:
        return
    # valid levels ?
    bdd.var_at_level(0)
    assert set(dvars).issubset(bdd._level_to_var), dvars
    assert set(dvars.itervalues()).issubset(bdd._level_to_var), dvars
    # pairwise disjoint ?
    _assert_no_overlap(dvars)
    # u independent of primed vars ?
    s = bdd.support(u, as_levels=True)
    for i in dvars.itervalues():
        assert i not in s, (
            'renaming target var "{v}" at '
            'level {i} is essential, rename: {r}, support: {s}').format(
                v=bdd.var_at_level(i), i=i,
                r=dvars, s=s)
    # neighbors ?
    for v, vp in dvars.iteritems():
        _assert_adjacent(v, vp, bdd)


def _assert_adjacent(i, j, bdd):
    """Raise `AssertionError` if level `i` not adjacent to `j`."""
    assert abs(i - j) == 1, (
        'level {i} ("{x}") not adjacent to '
        'level {j} ("{y}")').format(
            i=i,
            j=j,
            x=bdd.var_at_level(i),
            y=bdd.var_at_level(j))


def _assert_no_overlap(d):
    """Raise `AssertionError` if keys and values overlap."""
    assert not set(d).intersection(d.itervalues()), d


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
        bdd.ordering.get(k, k): bdd.ordering.get(v, v)
        for k, v in dict(rename).iteritems()}
    # init
    cache = dict()
    rename_u = rename
    rename_v = None
    # no overlap and neighbors
    _assert_no_overlap(rename)
    for v, vp in dict(rename).iteritems():
        _assert_adjacent(v, vp, bdd)
    # unpriming maps to qvars or outside support of conjunction
    s = bdd.support(trans, as_levels=True)
    s.update(bdd.support(source, as_levels=True))
    s.difference_update(qvars)
    s.intersection_update(rename.itervalues())
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
        bdd.ordering.get(k, k): bdd.ordering.get(v, v)
        for k, v in dict(rename).iteritems()}
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
        r = bdd.find_or_add(m, p, q)
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
    if order is None:
        _apply_sifting(bdd)
    else:
        _sort_to_order(bdd, order)


def _apply_sifting(bdd):
    """Apply Rudell's sifting algorithm."""
    bdd.collect_garbage()
    n = len(bdd)
    # using `set` injects some randomness
    levels = bdd._levels()
    names = set(bdd.ordering)
    for var in names:
        k = _reorder_var(bdd, var, levels)
        m = len(bdd)
        logger.info(
            '{m} nodes for variable "{v}" at level {k}'.format(
                m=m, v=var, k=k))
    assert m <= n, (m, n)
    logger.info('final variable ordering:\b{v}'.format(v=bdd.ordering))


def _reorder_var(bdd, var, levels):
    """Reorder by sifting a variable `var`.

    @type bdd: `BDD`
    @type var: `str`
    """
    assert var in bdd.ordering, (var, bdd.ordering)
    m = len(bdd)
    n = len(bdd.ordering) - 1
    assert n >= 0, n
    start = 0
    end = n
    level = bdd.ordering[var]
    # closer to top ?
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
    @type start, end: `0 <= int < len(bdd.ordering)`
    """
    m = len(bdd.ordering)
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
    assert len(bdd.ordering) == len(order)
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
    for x, y in dict(pairs).iteritems():
        jx = bdd.ordering[x]
        jy = bdd.ordering[y]
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


def copy_vars(source, target):
    """Copy variables, preserving levels.

    @type source, target: `BDD`
    """
    for var in source.vars:
        level = source.level_of_var(var)
        target.add_var(var, level=level)


def copy_bdd(u, from_bdd, to_bdd):
    """Copy function of node `u` `from_bdd` `to_bdd`.

    @param u: node in `from_bdd`
    @type from_bdd, to_bdd: `BDD`
    """
    # TODO: more efficient bottom-up implementation
    # first find all descendants of given roots
    # then map them, starting from the bottom layer
    _assert_valid_ordering(from_bdd.ordering)
    _assert_valid_ordering(to_bdd.ordering)
    support = from_bdd.support(u)
    level_map = _level_map(from_bdd, to_bdd, support)
    umap = dict()
    umap[1] = 1
    r = _copy_bdd(u, umap, level_map, from_bdd, to_bdd)
    return r


def _level_map(from_bdd, to_bdd, support):
    """Return map from old to new levels.

    @type from_bdd, to_bdd: `BDD`
    @param support: restrict the map to these variables
    @type support: var names as `str`
    """
    old = from_bdd.ordering
    new = to_bdd.ordering
    _assert_isomorphic_orders(old, new, support)
    level_map = {old[x]: new[x] for x in support}
    return level_map


def _copy_bdd(u, umap, level_map, old_bdd, bdd):
    """Recurse to copy nodes from `old_bdd` to `bdd`.

    @param u: node in `old_bdd`
    @type umap: `dict`
    @type level_map: `dict` as returned by `_level_map`
    @type old_bdd, bdd: `BDD`
    """
    # terminal ?
    if abs(u) == 1:
        return u
    # non-terminal
    # memoized ?
    if abs(u) in umap:
        r = umap[abs(u)]
        assert r > 0
        # complement ?
        if u < 0:
            r = -r
        return r
    # recurse
    jold, v, w = old_bdd._succ[abs(u)]
    jnew = level_map[jold]
    p = _copy_bdd(v, umap, level_map, old_bdd, bdd)
    q = _copy_bdd(w, umap, level_map, old_bdd, bdd)
    assert p * v > 0, (p, v)
    assert q > 0, q
    # add node
    r = bdd.find_or_add(jnew, p, q)
    assert r > 0
    # memoize
    umap[abs(u)] = abs(r)
    # negate ?
    if u < 0:
        r = -r
    return r


def to_nx(bdd, roots):
    """Convert functions in `roots` to `networkx.MultiDiGraph`.

    The resulting graph has:

      - nodes labeled with:
        - `level`: `int` from 0 to `len(bdd)`
      - edges labeled with:
        - `value`: `False` for low/"else", `True` for high/"then"
        - `complement`: `True` if target node is negated

    @type bdd: `BDD`
    @type roots: iterable of edges, each a signed `int`
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


def to_pydot(bdd):
    """Convert `BDD` to pydot graph.

    Nodes are ordered by variable levels.
    Edges to low successors are dashed.
    Complemented edges are labeled with "-1".

    @type bdd: `BDD`
    """
    import pydot
    g = pydot.Dot('bdd', graph_type='digraph')
    skeleton = list()
    subgraphs = dict()
    for i in xrange(len(bdd.ordering) + 1):
        h = pydot.Subgraph('', rank='same')
        g.add_subgraph(h)
        subgraphs[i] = h
        # add phantom node
        u = '-{i}'.format(i=i)
        skeleton.append(u)
        nd = pydot.Node(name=u, label=str(i), shape='none')
        h.add_node(nd)
    # auxiliary edges for ranking
    a, b = tee(skeleton)
    next(b, None)
    for u, v in izip(a, b):
        e = pydot.Edge(str(u), str(v), style='invis')
        g.add_edge(e)
    # add nodes
    idx2var = {k: v for v, k in bdd.ordering.iteritems()}

    def f(x): return str(abs(x))
    for u, (i, v, w) in bdd._succ.iteritems():
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
    return g
