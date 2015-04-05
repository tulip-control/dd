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
from itertools import tee, izip
import logging
import pickle
import sys
import astutils
# inline:
# import networkx
# import pydot


logger = logging.getLogger(__name__)
TABMODULE = 'dd.bdd_parsetab'
PLY_LOG = 'dd.bdd.ply'


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
        if ordering is None:
            ordering = dict()
        else:
            i = len(ordering)
            self._succ[1] = (i, None, None)
            self._ref[1] = 0
        self.ordering = dict(ordering)
        self._ind2var = None
        self.roots = set()
        self._parser = None
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

    def level_to_variable(self, i):
        """Return variable with level `i`."""
        if self._ind2var is None:
            self._ind2var = {
                k: var
                for var, k in self.ordering.iteritems()}
        return self._ind2var[i]

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

    def support(self, u):
        """Return variables that node `u` depends on.

        @rtype: `set`
        """
        var = set()
        self._support(u, var)
        return {self.level_to_variable(i) for i in var}

    def _support(self, u, var):
        """Recurse to collect variables in support."""
        # exhausted all vars ?
        if len(var) == len(self.ordering):
            return
        # terminal ?
        if u == -1 or u == 1:
            return
        i, v, w = self._succ[abs(u)]
        var.add(i)
        self._support(v, var)
        self._support(w, var)

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

    def compose(self, f, j, g, cache=None):
        """Return f(x_j=g).

        @param u, v: nodes
        @param j: variable level
        @param cache: stores intermediate results
        """
        # terminal or exhausted valuation ?
        if abs(f) == 1:
            return f
        # cached ?
        if cache is None:
            cache = dict()
        elif f in cache:
            return cache[f]
        i, v, w = self._succ[abs(f)]
        if j < i:
            return f
        elif i == j:
            r = self.ite(g, w, v)
        else:
            # i < j
            z = min(i, self._succ[abs(g)][0])
            f0, f1 = self._top_cofactor(f, z)
            g0, g1 = self._top_cofactor(g, z)
            p = self.compose(f0, j, g0, cache)
            q = self.compose(f1, j, g1, cache)
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
        else:
            # exhausted valuation
            return u
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
        vx = self.level_to_variable(x)
        self.ordering[vx] = y
        vy = self.level_to_variable(y)
        self.ordering[vy] = x
        # reset
        self._ind2var = None
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
        d = dict()
        d[u] = self._sat_len(u, d)
        i, _, _ = self._succ[abs(u)]
        return d[u] * 2**i

    def _sat_len(self, u, d):
        """Recurse to compute the number of models."""
        # terminal ?
        if u == -1:
            return 0
        elif u == 1:
            return 1
        # non-terminal
        i, v, w = self._succ[abs(u)]
        if v not in d:
            d[v] = self._sat_len(v, d)
        if w not in d:
            d[w] = self._sat_len(w, d)
        iv, _, _ = self._succ[abs(v)]
        iw, _, _ = self._succ[w]
        # complement ?
        du = (d[v] * 2**(iv - i - 1) +
              d[w] * 2**(iw - i - 1))
        # complement ?
        if u < 0:
            return 2**(len(self.ordering) - iv) - d[v]
        else:
            return du

    def sat_iter(self, u):
        """Return generator over models.

        A model is a satisfying assignment to variables.

        If a variable is missing from the `dict` of a model,
        then it is a "don't care", i.e., the model can be
        completed by assigning any value to that variable.

        @rtype: generator of `dict`
        """
        # empty ?
        if not self._succ:
            return
        # non-empty
        assert abs(u) in self._succ, u
        self.level_to_variable(0)
        return self._sat_iter(u, dict(), True)

    def _sat_iter(self, u, model, value):
        """Recurse to enumerate models."""
        if u < 0:
            value = not value
        # terminal ?
        if abs(u) == 1:
            if value:
                model = {
                    self._ind2var[i]: v
                    for i, v in model.iteritems()}
                yield model
            return
        # non-terminal
        i, v, w = self._succ[abs(u)]
        d0 = dict(model)
        d0[i] = 0
        d1 = dict(model)
        d1[i] = 1
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

        If the attribute `_parser` is `None`,
        then it is attempted to import `tulip.spec`.
        To avoid this, set `_parser` to a custom parser
        with a method `parse` that returns a syntax tree
        that conforms to `add_ast`.

        @type expr: `str`
        """
        if self._parser is None:
            self._parser = Parser()
        return self.add_ast(self._parser.parse(e))

    def add_ast(self, t):
        """Add abstract syntax tree `t` to `self`.

        The variables must be keys in `self.ordering`.

        Any AST nodes are acceptable provided they have
        attributes:
          - `"operator"` and `"operands"` for operator nodes
          - `"value"` equal to:
            - `"True"` or `"False"` for Boolean constants
            - a key (var name) in `self.ordering` for variables

        @type t: `Terminal` or `Operator` of `tulip.spec.ast`
        """
        # assert 1 in `self`, with index `len(self.ordering)`
        # operator ?
        if t.type == 'operator':
            operands = map(self.add_ast, t.operands)
            return self.apply(t.operator, *operands)
        elif t.type == 'bool':
            index = len(self.ordering)
            self._succ[1] = (index, None, None)
            u = -1 if t.value.lower() == 'false' else 1
            return u
        elif t.type == 'var':
            i = len(self.ordering)
            self._succ[1] = (i, None, None)
            assert t.value in self.ordering, (
                'undefined variable "{v}", '
                'known variables are:\n {d}').format(
                    v=t.value, d=self.ordering)
            j = self.ordering[t.value]
            return self.find_or_add(j, -1, 1)
        else:
            raise Exception(
                'unknown node type "{t}"'.format(t=t.type))

    def to_expr(self, u):
        """Return a Boolean expression for node `u`."""
        ind2var = {k: v for v, k in self.ordering.iteritems()}
        return self._to_expr(u, ind2var)

    def _to_expr(self, u, ind2var):
        if abs(u) == 1:
            return u
        i, v, w = self._succ[abs(u)]
        var = ind2var[i]
        p = self._to_expr(v, ind2var)
        q = self._to_expr(w, ind2var)
        # pure var ?
        if p == -1 and q == 1:
            s = var
        else:
            s = '({var} -> {q} : {p})'.format(var=var, p=p, q=q)
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

    def dump(self, filename, filetype=None):
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
            self._dump_pdf(filename)
        elif filetype == 'pickle':
            self._dump_pickle(filename)

    def _dump_pdf(self, filename):
        """Write `BDD` to `filename` as PDF."""
        g = to_pydot(self)
        g.write_pdf(filename)

    def _dump_pickle(self, filename):
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
            pickle.dump(d, f)

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
                 for k, v in dvars.iteritems()}
    # split
    var = set(dvars)
    varp = set(dvars.itervalues())  # primed vars
    # pairwise disjoint ?
    assert len(var) == len(varp), dvars
    assert not var.intersection(varp), dvars
    S = set()
    Q = set([u])
    # u independent of varp ?
    while Q:
        x = Q.pop()
        i, v, w = bdd._succ[abs(x)]
        if v is None or w is None:
            assert v is None, v
            assert w is None, w
            continue
        if v not in S:
            Q.add(v)
            S.add(v)
        if w not in S:
            Q.add(w)
            S.add(w)
        assert i not in varp, (
            'target var "{v}" at level {i} is essential'.format(
                v=bdd.level_to_variable(i), i=i))
    # neighbors ?
    for v, vp in dvars.iteritems():
        assert abs(v - vp) == 1, (
            '"{v}" not neighbor of "{vp}"'.format(
                v=v, vp=vp))
    return _rename(u, bdd, dvars)


def _rename(u, bdd, dvars):
    """Recursive renaming, assuming `dvars` is valid."""
    if abs(u) == 1:
        return u
    i, v, w = bdd._succ[abs(u)]
    p = _rename(v, bdd, dvars)
    q = _rename(w, bdd, dvars)
    # to be renamed ?
    z = dvars.get(i, i)
    r = bdd.find_or_add(z, p, q)
    if u < 0:
        r = -r
    return r


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
    cache = dict()
    rename_u = rename
    rename_v = None
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
    cache = dict()
    rename_u = None
    rename_v = rename
    return _image(trans, target, rename_u, rename_v,
                  qvars, bdd, forall, cache)


def _image(u, v, umap, vmap, qvars, bdd, forall, cache):
    """Recursive (pre)image computation.

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


def reorder(bdd):
    """Apply Rudell's sifting algorithm to reduce `bdd` size.

    Reordering invokes the garbage collector,
    so be sure to `incref` nodes that should remain.

    @type bdd: `BDD`
    """
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
            if v not in g:
                Q.add(v)
            if w not in g:
                Q.add(w)
            g.add_edge(u, abs(v), value=False, complement=(v < 0))
            g.add_edge(u, abs(w), value=True, complement=False)
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
    """

    def __init__(self, node, bdd):
        assert abs(node) in bdd, node
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
        return cls(u, bdd)

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
        return self.bdd.level_to_variable(i)

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


class Lexer(astutils.Lexer):
    """Lexer for Boolean formulae."""

    reserved = {
        'ite': 'ITE',
        'False': 'FALSE',
        'True': 'TRUE'}
    delimiters = ['LPAREN', 'RPAREN', 'COMMA']
    operators = ['NOT', 'AND', 'OR', 'XOR', 'IMP', 'BIMP',
                 'EQUALS', 'NEQUALS']
    misc = ['NAME', 'NUMBER']

    def t_NAME(self, t):
        r"[A-Za-z_][A-za-z0-9_.']*"
        t.type = self.reserved.get(t.value, 'NAME')
        return t

    def t_AND(self, t):
        r'\&\&|\&'
        t.value = '&'
        return t

    def t_OR(self, t):
        r'\|\||\|'
        t.value = '|'
        return t

    t_NOT = r'\!'
    t_XOR = r'\^'
    t_EQUALS = r'\='
    t_NEQUALS = r'\!\='
    t_LPAREN = r'\('
    t_RPAREN = r'\)'
    t_NUMBER = r'\d+'
    t_IMP = '->'
    t_BIMP = '\<->'
    t_COMMA = r','
    t_ignore = " \t"

    def t_comment(self, t):
        r'\#.*'
        return

    def t_newline(self, t):
        r'\n+'
        t.lexer.lineno += t.value.count("\n")


class Parser(astutils.Parser):
    """Parser for Boolean formulae."""

    tabmodule = TABMODULE
    start = 'expr'
    # low to high
    precedence = (
        ('left', 'BIMP'),
        ('left', 'IMP'),
        ('left', 'XOR'),
        ('left', 'OR'),
        ('left', 'AND'),
        ('left', 'EQUALS', 'NEQUALS'),
        ('right', 'NOT'))
    Lexer = Lexer

    def p_bool(self, p):
        """expr : TRUE
                | FALSE
        """
        p[0] = self.nodes.Terminal(p[1], 'bool')

    def p_number(self, p):
        """expr : NUMBER"""
        p[0] = self.nodes.Terminal(p[1], 'num')

    def p_var(self, p):
        """expr : NAME"""
        p[0] = self.nodes.Terminal(p[1], 'var')

    def p_unary(self, p):
        """expr : NOT expr"""
        p[0] = self.nodes.Operator(p[1], p[2])

    def p_binary(self, p):
        """expr : expr AND expr
                | expr OR expr
                | expr XOR expr
                | expr IMP expr
                | expr BIMP expr
                | expr EQUALS expr
                | expr NEQUALS expr
        """
        p[0] = self.nodes.Operator(p[2], p[1], p[3])

    def p_ternary_conditional(self, p):
        """expr : ITE LPAREN expr COMMA expr COMMA expr RPAREN"""
        p[0] = self.nodes.Operator(p[1], p[3], p[5], p[7])

    def p_paren(self, p):
        """expr : LPAREN expr RPAREN"""
        p[0] = p[2]


def _rewrite_tables(outputdir='./'):
    astutils.rewrite_tables(Parser, TABMODULE, outputdir)


if __name__ == '__main__':
    _rewrite_tables()
