"""Ordered binary decision diagrams based on `networkx`.


References
==========

Randal E. Bryant
    "Graph-based algorithms for Boolean function manipulation"
    IEEE Transactions on Computers
    Vol. C-35, No.8, August, 1986, pp.677--690

Karl S. Brace, Richard L. Rudell, Randal E. Bryant
    "Efficient implementation of a BDD package"
    27th ACM/IEEE Design Automation Conference, 1990
    pp.40--45

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
import logging
logger = logging.getLogger(__name__)
from collections import Mapping
from itertools import tee, izip
import networkx as nx
# inline:
# import pydot
# import tulip.spec.lexyacc


class BDD(nx.MultiDiGraph):
    """Shared ordered binary decision diagram.

    There must be at least one root.
    Terminal nodes are the integers 0, 1.

    Attributes:
      - `ordering`: `dict` mapping `variables` to `int` indices
      - `roots`: nodes with no predecessors

    Labeling:
      - each node with `index` of type `int`
      - each edge with `value` of type `bool`

    If `ordering` changes, then reordering is needed.

    To ensure `ite` maintains reducedness add new
    nodes using `find_or_add` to keep the table updated,
    or call `update_pairs_table` prior to calling `ite`.
    """

    def __init__(self, ordering=None, **kw):
        super(BDD, self).__init__(**kw)
        if ordering is None:
            ordering = dict()
        else:
            self.add_nodes_from([0, 1], index=len(ordering))
        self.ordering = ordering
        self.roots = set()
        self._pairs_table = dict()
        self._ite_table = dict()
        self._parser = None

    def __str__(self):
        return (
            'Binary decision diagram:\n'
            '------------------------\n'
            'var ordering: {self.ordering}\n'
            'roots: {self.roots}\n').format(self=self)

    def _map_to_index(self, d):
        """Map keys of `d` to variable indices.

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
            keys can be variable names as `str` or indices as `int`
        @type values: `dict`
        """
        values = self._map_to_index(values)
        # follow valuation from u to terminal
        while u not in {0, 1}:
            (_, v, d), (_, w, _) = self.edges_iter(u, data=True)
            if d['value'] == values[self.node[u]['index']]:
                u = v
            else:
                u = w
        return u

    def is_essential(self, u, var):
        """Return `True` if `var` essential for node `u`."""
        i = self.ordering.get(var)
        if i is None:
            return False
        iu = self.node[u]['index']
        # var above node u ?
        if i < iu:
            return False
        # u depends on node labeled with var ?
        for v in nx.algorithms.dfs_preorder_nodes(self, u):
            if self.node[v]['index'] == i:
                return True
        return False

    def support(self, u):
        """Return variables that node `u` depends on."""
        var = set()
        n = len(self.ordering)
        for v in nx.algorithms.dfs_preorder_nodes(self, u):
            var.add(self.node[v]['index'])
            if len(var) == n:
                break
        return map(self.ordering, var)

    def levels(self):
        """Put in bins by index."""
        levels = dict()
        for u in self:
            i = self.node[u]['index']
            levels.setdefault(i, set()).add(u)
        return levels

    def reduction(self):
        """Return copy reduced with respect to `self.ordering`."""
        levels = self.levels()
        # sort from terminals to root
        r = iter(sorted(levels.iteritems(), reverse=True))
        # terminals
        i, s = next(r)
        umap = {u: u for u in s}
        assert s == {0, 1}
        assert i == max(levels)
        # non-terminals
        redundant = set()
        toint = {0: 0, 1: 1}
        m = 0
        for i, s in r:
            m = m + len(toint)
            toint = dict()
            for u in s:
                (_, v, dv), (_, w, _) = self.edges_iter(
                    u, data=True)
                p, q = umap[v], umap[w]
                # redundant ?
                if p == q:
                    umap[u] = p
                    redundant.add(p)
                    continue
                # not redundant
                # swap succ ?
                if dv['value']:
                    pq = (q, p)
                else:
                    pq = (p, q)
                k = toint.setdefault(pq, m + len(toint))
                umap[u] = k
        h = nx.relabel_nodes(self, umap)
        # rm self-loops introduced
        for u in redundant:
            h.remove_edge(u, u)
        # init other attr
        h.ordering = dict(self.ordering)
        h.roots = {u for u in h if not h.pred[u]}
        return h

    def compose(self, f, j, g, cache=None):
        """Return f(x_j=g).

        @param u, v: nodes
        @param j: variable index
        @param cache: stores intermediate results
        """
        # terminal or exhausted valuation ?
        if f in {0, 1}:
            return f
        # cached ?
        if cache is None:
            cache = dict()
        elif f in cache:
            return cache[f]
        i = self.node[f]['index']
        if j < i:
            return f
        elif i == j:
            (_, v, dv), (_, w, _) = self.edges_iter(f, data=True)
            if dv['value']:
                v, w = w, v
            r = self.ite(g, w, v)
        else:
            # i < j
            z = min(i, self.node[g]['index'])
            f0, f1 = self._top_cofactor(f, z)
            g0, g1 = self._top_cofactor(g, z)
            p = self.compose(f0, j, g0, cache)
            q = self.compose(f1, j, g1, cache)
            r = self.find_or_add(z, p, q)
        cache[(f, g)] = r
        return r

    def ite(self, g, u, v):
        """Return node for if-then-else of `g`, `x` and `y`.

        @type g, x, y: nodes
        @rtype: [BDD]
        """
        # is g terminal ?
        if g == 1:
            return u
        elif g == 0:
            return v
        # g is non-terminal
        # already computed ?
        r = (g, u, v)
        w = self._ite_table.get(r)
        if w is not None:
            return w
        z = min(self.node[g]['index'],
                self.node[u]['index'],
                self.node[v]['index'])
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
        @param i: variable index
        @param value: assignment to variable `i`
        """
        # terminal node ?
        if u in {0, 1}:
            return (u, u)
        # non-terminal node
        iu = self.node[u]['index']
        # u independent of var ?
        if i < iu:
            return (u, u)
        elif iu < i:
            raise Exception('call `cofactor` instead')
        # iu == i
        # u labeled with var
        (_, v, d), (_, w, _) = self.edges_iter(u, data=True)
        if d['value']:
            return (w, v)
        else:
            return (v, w)

    def cofactor(self, u, values):
        """Return restriction of `u` to valuation `values`.

        @param u: node
        @param values: `dict` that maps var indices to values
        """
        values = self._map_to_index(values)
        cache = dict()
        ordvar = sorted(values)
        j = 0
        return self._cofactor(u, j, ordvar, values, cache)

    def _cofactor(self, u, j, ordvar, values, cache):
        """Recurse to compute cofactor."""
        # terminal ?
        if u in {0, 1}:
            return u
        if u in cache:
            return cache[u]
        i = self.node[u]['index']
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
        (_, v, dv), (_, w, _) = self.edges_iter(u, data=True)
        if i in values:
            val = values[i]
            if bool(dv['value']) != bool(val):
                v = w
            r = self._cofactor(v, j, ordvar, values, cache)
        else:
            p = self._cofactor(v, j, ordvar, values, cache)
            q = self._cofactor(w, j, ordvar, values, cache)
            if dv['value']:
                r = self.find_or_add(i, q, p)
            else:
                r = self.find_or_add(i, p, q)
        cache[u] = r
        return r

    def quantify(self, u, qvars, forall=False):
        """Return existential of universal abstraction.

        Caution: `dvars` is modified.

        @param u: node
        @param qvars: `set` of quantified variables
        @param forall: if `True`,
            then quantify `dvars` universally,
            else quantify existentially.
        """
        qvars = self._map_to_index(qvars)
        cache = dict()
        ordvar = sorted(qvars)
        j = 0
        return self._quantify(u, j, ordvar, qvars, forall, cache)

    def _quantify(self, u, j, ordvar, qvars, forall, cache):
        """Recurse to quantify variables."""
        # terminal ?
        if u in {0, 1}:
            return u
        if u in cache:
            return cache[u]
        i = self.node[u]['index']
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
        (_, v, dv), (_, w, _) = self.edges_iter(u, data=True)
        if i in qvars:
            if forall:
                r = self.ite(v, w, 0)  # conjoin
            else:
                r = self.ite(v, 1, w)  # disjoin
        else:
            p = self._quantify(v, j, ordvar, qvars, forall, cache)
            q = self._quantify(w, j, ordvar, qvars, forall, cache)
            if dv['value']:
                r = self.find_or_add(i, q, p)
            else:
                r = self.find_or_add(i, p, q)
        cache[u] = r
        return r

    def find_or_add(self, i, v, w):
        """Return a node at level `i` with successors `v, w`.

        If one exists, it is quickly found in the cached table.

        @param v: low
        @param w: high
        """
        if v == w:
            return v
        t = (i, v, w)
        u = self._pairs_table.get(t)
        if u is None:
            u = len(self)
            assert u not in self
            assert i < len(self.ordering)
            assert v in self
            assert w in self
            self._pairs_table[t] = u
            self.add_node(u, index=i)
            self.add_edge(u, v, value=False)
            self.add_edge(u, w, value=True)
        return u

    def update_pairs_table(self):
        """Update table that maps (level, low, high) to nodes."""
        for u, du in self.nodes_iter(data=True):
            if u in {0, 1}:
                continue
            (_, v, dv), (_, w, _) = self.successors_iter(u)
            if dv['value']:
                v, w = w, v
            t = (du['index'], v, w)
            self._pairs_table[t] = u

    def sat_len(self, u=None):
        """Return number of models of node `u`.

        Labels nodes with `"sat_len"`, the number of
        satisfying valuations for the corresponding factor.

        The default node `u` is `self.root`, unless
        BDD has multiple roots.
        """
        root = u
        if root is None:
            if len(self.roots) != 1:
                raise Exception(
                    'No single root defined: give `u`')
            else:
                (root, ) = self.roots
        levels = self.levels()
        # from terminals up to root
        r = iter(sorted(levels.iteritems(), reverse=True))
        # terminals
        i, s = next(r)
        d = self.node
        idx = lambda u: d[u]['index']
        a = lambda u: d[u]['sat_len']
        for u in s:
            d[u]['sat_len'] = u
        # non-terminals
        for i, s in r:
            for u in s:
                p, q = self.succ[u]
                d[u]['sat_len'] = (
                    a(p) * 2**(idx(p) - idx(u) - 1) +
                    a(q) * 2**(idx(q) - idx(u)) - 1)
        return a(root) * 2**idx(root)

    def sat_iter(self, root=None):
        """Return iterator over models.

        Use `next(BDD.sat_iter())` to get a single
        satisfying valuation.

        If the BDD has multiple roots,
        then a `root` must be given.

        If a variable is missing from the `dict` of a model,
        then it is a "don't care", i.e., the model can be
        completed by assigning any value to that variable.
        """
        ind2var = {k: v for v, k in self.ordering.iteritems()}
        # empty or unsat ?
        if len(self) == 0:
            return
        if len(self) == 1 and False in self:
            return
        # satisfiable
        if root is None:
            if len(self.roots) != 1:
                raise Exception(
                    'No single root defined: give `root`')
            else:
                (root, ) = self.roots
        g = nx.reverse(self)
        paths = nx.all_simple_paths(g, 1, root)
        for p in paths:
            model = dict()
            r = iter(p)
            u = next(r)
            for v in r:
                var = ind2var[g.node[v]['index']]
                # assert no redundant nodes
                assert len(self[v][u]) == 1
                val = self[v][u][0]['value']
                model[var] = val
                u = v
            yield model

    def is_consistent(self):
        """Return `True` if `self` is a valid BDD."""
        assert self.roots == {u for u in self if not self.node[u]}
        assert self.roots  # must be rooted
        for u, d in self.nodes_iter(data=True):
            k = 'index'
            assert k in d
            assert isinstance(d[k], int)
            # terminal ?
            if not self.succ[u]:
                continue
            # var order should increase
            values = set()
            for v, q in self.successors_iter(u, data=True):
                assert d['index'] < q['index']
                values.add(bool(q['value']))
            assert values == {False, True}
        for u in self.roots:
            assert not self.in_degree(u)
        for u, out in self.out_degree_iter():
            if u in {0, 1}:
                assert not out
            else:
                assert out == 2

    def add_expr(self, e):
        """Return node for expression `e` after adding it.

        @type expr: `str`
        """
        try:
            from tulip.spec import lexyacc
        except ImportError:
            raise Exception('failed to import `tulip.spec`')
        if self._parser is None:
            self._parser = lexyacc.Parser()
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
        # assert 0, 1 in `self`, with index `len(self.ordering)`
        # operator ?
        try:
            operands = map(self.add_ast, t.operands)
            return self.apply(t.operator, *operands)
        except AttributeError:
            # var or bool (terminal AST node)
            # Boolean constant ?
            if t.value in {'True', 'False'}:
                u = int(t.value == 'True')
                self.add_node(u, index=len(self.ordering))
                return u
            # variable `t.value` must be in `self.ordering`
            i = self.ordering[t.value]
            self.add_nodes_from([0, 1], index=len(self.ordering))
            return self.find_or_add(i, 0, 1)

    def to_expr(self, u):
        """Return a Boolean expression for node `u`."""
        ind2var = {k: v for v, k in self.ordering.iteritems()}
        return self._to_expr(u, ind2var)

    def _to_expr(self, u, ind2var):
        if u in {0, 1}:
            return u
        i = self.node[u]['index']
        var = ind2var[i]
        (_, v, dv), (_, w, _) = self.edges_iter(u, data=True)
        if dv['value']:
            v, w = w, v
        p = self._to_expr(v, ind2var)
        q = self._to_expr(w, ind2var)
        # pure var ?
        if p == 0 and q == 1:
            return var
        elif p == 1 and q == 0:
            return '!{var}'.format(var=var)
        else:
            return '({var} -> {q} : {p})'.format(var=var, p=p, q=q)

    def apply(self, op, u, v=None):
        """Apply Boolean connective `op` between nodes `u` and `v`.

        @type op: `str` in:
          - `'not', 'or', 'and', 'xor', 'implies', 'bimplies'`
          - `'!', '|', '||', '&', '&&', '^', '->', '<->'`
        @type u, v: nodes
        """
        if op in {'not', '!'}:
            return self.ite(u, 0, 1)
        elif op in {'or', '|', '||'}:
            return self.ite(u, 1, v)
        elif op in {'and', '&', '&&'}:
            return self.ite(u, v, 0)
        elif op in {'xor', '^'}:
            return self.ite(u, self.ite(v, 0, 1), v)
        elif op in {'implies', '->'}:
            return self.ite(u, v, 1)
        elif op in {'bimplies', '<->'}:
            return self.ite(u, v, self.ite(v, 0, 1))

    def write(self, filename):
        """Write the BDD graph to `filename` as PDF."""
        g = to_pydot(self)
        if filename.endswith('.pdf'):
            g.write_pdf(filename)
        else:
            raise Exception('file type not supported')


def rename(u, bdd, dvars):
    """Efficient rename to non-essential neighbors.

    @param dvars: `dict` from variabe indices to indices
    """
    var = set(dvars)
    varp = set(dvars.itervalues())
    # pairwise disjoint ?
    assert len(var) == len(varp)
    assert not var.intersection(varp)
    S = set()
    Q = set([u])
    # u independent of varp ?
    while Q:
        x = Q.pop()
        r = set(bdd.successors(x)).difference(S)
        Q.update(r)
        S.update(r)
        assert bdd.node[x]['index'] not in varp
    # neighbors ?
    for v, vp in dvars.iteritems():
        assert abs(bdd.ordering[v], bdd.ordering[vp]) == 1
    return _rename(u, bdd, dvars)


def _rename(u, bdd, dvars):
    """Recursive renaming, assuming `dvars` is valid."""
    if u in {0, 1}:
        return u
    (_, v, dv), (_, w, _) = bdd.edges_iter(u, data=True)
    if dv['value']:
        v, w = w, v
    p = _rename(v, bdd, dvars)
    q = _rename(w, bdd, dvars)
    z = bdd.node[u]['index']
    # to be renamed ?
    z = dvars.get(z, z)
    return bdd.find_or_add(z, p, q)


def image(trans, source, rename, qvars, bdd, forall=False):
    """Return set reachable from `source` under `trans`.

    @param trans: transition relation
    @param source: the transition must start in this set
    @param rename: `dict` that maps primed variables in
        `u` to unprimed variables in `u`.
        Applied to the quantified conjunction of `u` and `v`.
    @param qvars: `set` of quantified variables
    @param bdd: [BDD]
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
    """Return set that can reach target `v` under `u`.

    Also known as the "relational product".
    Assumes that primed and unprimed variables are neighbors.
    Variables are identified by their indices.

    @param trans: transition relation
    @param target: the transition must end in this set
    @param rename: `dict` that maps variables in `v` to
        variables in `u`
    @param qvars: `set` of quantified variables
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
    if u == 0 or v == 0:
        return 0
    if u == 1 and v == 1:
        return 1
    # already computed ?
    t = (u, v)
    w = cache.get(t)
    if w is not None:
        return w
    # recurse (descend)
    iu = bdd.node[u]['index']
    jv = bdd.node[v]['index']
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
            r = bdd.ite(p, q, 0)  # conjoin
        else:
            r = bdd.ite(p, 1, q)  # disjoin
    else:
        if umap is not None:
            m = umap.get(z, z)
        else:
            m = z
        r = bdd.find_or_add(m, p, q)
    cache[t] = r
    return r


def to_pydot(bdd):
    """Convert BDD to pydot graph.

    Nodes are ordered by variables.
    Edges to low successors are dashed.
    """
    try:
        import pydot
    except ImportError:
        raise Exception('could not import pydot')
    idx2var = {k: v for v, k in bdd.ordering.iteritems()}
    g = pydot.Dot('bdd', graph_type='digraph')
    levels = bdd.levels()
    skeleton = list()
    for i, s in sorted(levels.iteritems()):
        h = pydot.Subgraph('', rank='same')
        g.add_subgraph(h)
        # add phantom node
        u = '-{i}'.format(i=i)
        skeleton.append(u)
        nd = pydot.Node(name=u, label=str(i), shape='none')
        h.add_node(nd)
        # add nodes of this level
        for u in s:
            if u in {0, 1}:
                label = str(bool(u))
            else:
                var = idx2var[bdd.node[u]['index']]
                label = '{var}-{u}'.format(var=var, u=u)
            nd = pydot.Node(name=u, label=label)
            h.add_node(nd)
            # place node "False" left
            if u == 0:
                h.set_rankdir('LR')
                h.add_edge(pydot.Edge(0, 1, style='invis'))
    # BDD edges
    for u, v, d in bdd.edges_iter(data=True):
        if d['value']:
            style = 'solid'
        else:
            style = 'dashed'
        e = pydot.Edge(u, v, style=style)
        g.add_edge(e)
    # auxiliary edges for ranking
    a, b = tee(skeleton)
    next(b, None)
    for u, v in izip(a, b):
        g.add_edge(pydot.Edge(u, v, style='invis'))
    return g
