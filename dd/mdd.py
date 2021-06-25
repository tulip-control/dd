"""Ordered multi-valued decision diagrams.


References
==========

Arvind Srinivasan, Timothy Kam, Sharad Malik, Robert K. Brayton
    "Algorithms for discrete function manipulation"
    IEEE International Conference on
    Computer-Aided Design (ICCAD), 1990
    pp.92--95

Michael Miller and Rolf Drechsler
    "Implementing a multiple-valued decision diagram package"
    28th International Symposium on
    Multiple-Valued Logic (ISMVL), 1998
    pp.52--57
"""
# Copyright 2015 by California Institute of Technology
# All rights reserved. Licensed under BSD-3.
#
import logging
import sys

from dd import bdd as _bdd
from dd.bdd import to_nx
# inline:
# import networkx
# import pydot


logger = logging.getLogger(__name__)
TABMODULE = 'dd.mdd_parsetab'
PLY_LOG = 'dd.mdd.ply'


class MDD:
    """Shared ordered multi-valued decision diagram.

    Represents a Boolean function of integer variables.
    Nodes are integers.
    The terminal node is 1.
    Complemented edges are represented as negated nodes.
    Values returned by methods are edges, possibly complemented.
    Edge 0 is never complemented.

    Attributes:
      - `vars`
      - `max_nodes`

    If you want a node to survive garbage collection,
    increment its reference counter:

    `mdd.incref(edge)`
    """

    # dvars:
    # `dict` that maps each variable to a `dict`
    # that defines its:
    #  - len
    #  - level

    def __init__(self, dvars=None):
        self._pred = dict()
        self._succ = dict()
        self._ref = dict()
        self._max = 1
        self._ite_table = dict()
        if dvars is None:
            dvars = dict()
        else:
            i = len(dvars)
            self._succ[1] = (i, None)
            self._ref[1] = 0
        self.vars = dict(dvars)
        self._level_to_var = None
        self._parser = None
        self._free = set()
        self.max_nodes = sys.maxsize

    def __len__(self):
        """Return number of BDD nodes."""
        return len(self._succ)

    def __contains__(self, u):
        """Return `True` if `u` is a BDD node."""
        return abs(u) in self._succ

    def __iter__(self):
        return iter(self._succ)

    def _allocate(self):
        """Return free integer, mark it as occupied."""
        if self._free:
            return self._free.pop()
        else:
            self._max += 1
            return self._max

    def _release(self, u):
        """Unmark integer from used ones."""
        if u > self._max:
            raise AssertionError(u)
        if u in self._free:
            raise AssertionError(u)
        if u in self._succ:
            raise AssertionError(u)
        if u in self._pred:
            raise AssertionError(u)
        if u in self._ref:
            raise AssertionError(u)
        self._free.add(u)

    def incref(self, u):
        """Increment reference count of node `abs(u)`."""
        self._ref[abs(u)] += 1

    def decref(self, u):
        """Decrement reference count of node `abs(u)`, with 0 as min."""
        if self._ref[abs(u)] > 0:
            self._ref[abs(u)] -= 1

    def ref(self, u):
        """Return reference count for node `abs(u)`."""
        return self._ref[abs(u)]

    def var_at_level(self, i):
        """Return variable with level `i`."""
        if self._level_to_var is None:
            self._level_to_var = {
                d['level']: var
                for var, d in self.vars.items()}
        return self._level_to_var[i]

    def level_of_var(self, var):
        """Return level of variable `var`."""
        return self.vars[var]['level']

    def ite(self, g, u, v):
        """Return node for `if g then u, else v`.

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
        t = (g, u, v)
        w = self._ite_table.get(t)
        if w is not None:
            return w
        z = min(self._succ[abs(g)][0],
                self._succ[abs(u)][0],
                self._succ[abs(v)][0])
        gc = self._top_cofactor(g, z)
        uc = self._top_cofactor(u, z)
        vc = self._top_cofactor(v, z)
        nodes = tuple(self.ite(a, b, c)
                      for a, b, c in zip(gc, uc, vc))
        w = self.find_or_add(z, nodes)
        # cache
        self._ite_table[t] = w
        return w

    def find_or_add(self, i, *nodes):
        """Return node at level `i` with successors in `nodes`.

        @param i: level in `range(len(vars))`
        @type i: int
        """
        if not (0 <= i < len(self.vars)):
            raise ValueError(i)
        var = self.var_at_level(i)
        if len(nodes) != self.vars[var]['len']:
            raise ValueError(
                (var, len(nodes), self.vars[var]['len']))
        if not nodes:  # in case max == 0
            raise ValueError(nodes)
        for u in nodes:
            if abs(u) not in self:
                raise ValueError(u)
        # canonicity of complemented edges
        if nodes[0] < 0:
            nodes = tuple(-u for u in nodes)
            r = -1
        else:
            r = 1
        # eliminate
        if len(set(nodes)) == 1:
            return r * nodes[0]
        # already exists ?
        t = (i,) + nodes
        u = self._pred.get(t)
        if u is not None:
            return r * u
        u = self._allocate()
        if u in self:
            raise AssertionError((self._succ, u, t))
        # add node
        self._pred[t] = u
        self._succ[u] = t
        self._ref[u] = 0
        # reference counting
        for v in nodes:
            self.incref(v)
        return r * u

    def collect_garbage(self, roots=None):
        """Recursively remove nodes with zero reference count."""
        if roots is None:
            roots = self._ref
        dead = {u for u in roots if not self.ref(u)}
        # keep terminal
        if 1 in dead:
            dead.remove(1)
        while dead:
            u = dead.pop()
            if u == 1:
                raise AssertionError(u)
            # remove
            t = self._succ.pop(u)
            u_ = self._pred.pop(t)
            uref = self._ref.pop(u)
            self._release(u)
            if u != u_:
                raise AssertionError((u, u_))
            if uref != 0:
                raise AssertionError(uref)
            if u not in self._free:
                raise AssertionError((u, self._free))
            # recurse
            # decrement reference counters
            nodes = t[1:]
            for v in nodes:
                self.decref(v)
                # died ?
                if not self._ref[abs(v)] and abs(v) != 1:
                    dead.add(abs(v))
        self._ite_table = dict()

    def to_expr(self, u):
        if u == 1:
            return u
        elif u == -1:
            return 0
        t = self._succ[abs(u)]
        i = t[0]
        nodes = t[1:]
        var = self.var_at_level(i)
        # group per target node
        c = tuple(set(nodes))
        e = {x: self.to_expr(x) for x in c}
        cond = {v: set() for v in c}
        for j, x in enumerate(nodes):
            cond[x].add(j)
        # format
        cond_str = dict()
        for k, v in cond.items():
            if len(v) == 1:
                (j,) = v
                cond_str[k] = '= {j}'.format(j=j)
            else:
                cond_str[k] = 'in {v}'.format(v=v)
        x = c[0]
        s = 'if ({var} {j}): {p}, '.format(
            var=var, j=cond_str[x], p=e[x])
        s += ', '.join(
            '\nelif ({var} {j}): {p}'.format(
                var=var, j=cond_str[x], p=e[x])
            for x in c[1:])
        if u < 0:
            s = '! {s}'.format(s=s)
        s = '({s})'.format(s=s)
        return s

    def apply(self, op, u, v=None, w=None):
        if u not in self:
            raise ValueError(u)
        if not (v is None or v in self):
            raise ValueError(v)
        if not (w is None or w in self):
            raise ValueError(w)
        if op in ('~', 'not', '!'):
            if v is not None:
                raise ValueError(v)
            if w is not None:
                raise ValueError(w)
            return -u
        elif op in ('or', r'\/', '|', '||'):
            if v is None:
                raise ValueError(v)
            if w is not None:
                raise ValueError(w)
            return self.ite(u, 1, v)
        elif op in ('and', '/\\', '&', '&&'):
            if v is None:
                raise ValueError(v)
            if w is not None:
                raise ValueError(w)
            return self.ite(u, v, -1)
        elif op in ('xor', '^'):
            if v is None:
                raise ValueError(v)
            if w is not None:
                raise ValueError(w)
            return self.ite(u, -v, v)
        elif op in ('=>', '->', 'implies'):
            if v is None:
                raise ValueError(v)
            if w is not None:
                raise ValueError(w)
            return self.ite(u, v, 1)
        elif op in ('<=>', '<->', 'equiv'):
            if v is None:
                raise ValueError(v)
            if w is not None:
                raise ValueError(w)
            return self.ite(u, v, -v)
        elif op in ('diff', '-'):
            if v is None:
                raise ValueError(v)
            if w is not None:
                raise ValueError(w)
            return self.ite(u, -v, -1)
        elif op in (r'\A', 'forall'):
            if v is None:
                raise ValueError(v)
            if w is not None:
                raise ValueError(w)
            raise NotImplementedError(
                'quantification is not implemented for MDDs.')
        elif op in (r'\E', 'exists'):
            if v is None:
                raise ValueError(v)
            if w is not None:
                raise ValueError(w)
            raise NotImplementedError(
                'quantification is not implemented for MDDs.')
        elif op == 'ite':
            if v is None:
                raise ValueError(v)
            if w is None:
                raise ValueError(w)
            return self.ite(u, v, w)
        else:
            raise ValueError(
                'unknown operator "{op}"'.format(op=op))

    def dump(self, fname):
        """Write MDD as a diagram to PDF file `fname`.

        @param fname: file name, ending with the substring `.pdf`.
        @type fname: `str`

        The diagram includes all nodes in the MDD.
        The diagram is created using GraphViz.
        """
        if fname.endswith('.pdf'):
            pd = to_pydot(self)
            pd.write_pdf(fname)
        else:
            raise Exception(
                'unknown file extension: {f}'.format(f=fname))


def bdd_to_mdd(bdd, dvars):
    """Return MDD for given BDD.

    Caution: collects garbage.

    `dvars` must map each MDD variable to the
    corresponding bits in BDD.
    Also, it should give the order as "level" keys.
    """
    # i = level in BDD
    # j = level in MDD
    # bit = BDD variable
    # var = MDD variable
    #
    # map from bits to integers
    bit_to_var = dict()
    for var, d in dvars.items():
        bits = d['bitnames']
        b = {bit: var for bit in bits}
        bit_to_var.update(b)
    # find target bit order
    order = list()  # target
    levels = {d['level']: var for var, d in dvars.items()}
    m = len(levels)
    for j in range(m):
        var = levels[j]
        bits = dvars[var]['bitnames']
        order.extend(bits)
    bit_to_sort = {bit: k for k, bit in enumerate(order)}
    # reorder
    bdd.collect_garbage()
    _bdd.reorder(bdd, order=bit_to_sort)
    # BDD -> MDD
    mdd = MDD(dvars)
    # zones of bits per integer var
    zones = dict()
    for var, d in dvars.items():
        bits = d['bitnames']
        lsb = bits[0]
        msb = bits[-1]
        min_level = bit_to_sort[lsb]
        max_level = bit_to_sort[msb]
        zones[var] = (min_level, max_level)
    # reverse edges
    pred = {u: set() for u in bdd}
    for u, (_, v, w) in bdd._succ.items():
        if u <= 0:
            raise AssertionError(u)
        # terminal ?
        if u == 1:
            continue
        # non-terminal
        pred[abs(v)].add(u)
        pred[abs(w)].add(u)
    # find BDD nodes mentioned from above
    rm = set()
    for u, p in pred.items():
        rc = bdd.ref(u)
        k = len(p)  # number of predecessors
        # has external refs ?
        if rc > k:
            continue
        # has refs from outside zone ?
        i, _, _ = bdd._succ[u]
        bit = bdd.var_at_level(i)
        var = bit_to_var[bit]
        min_level, _ = zones[var]
        pred_levels = {bdd._succ[v][0] for v in p}
        min_pred_level = min(pred_levels)
        if min_pred_level < min_level:
            continue
        # referenced only from inside zone
        rm.add(u)
    pred = {u: p for u, p in pred.items() if u not in rm}
    # build layer by layer
    # TODO: use bins, instad of iterating through all nodes
    bdd.assert_consistent()
    # _debug_dump(pred, bdd)
    umap = dict()
    umap[1] = 1
    for u, i, v, w in bdd.levels(skip_terminals=True):
        # ignore function ?
        if u not in pred:
            continue
        # keep `u`
        bit = bdd.var_at_level(i)
        var = bit_to_var[bit]
        bits = dvars[var]['bitnames']
        bit_succ = list()
        for d in _enumerate_integer(bits):
            x = bdd.cofactor(u, d)
            bit_succ.append(x)
        # map edges
        int_succ = [umap[abs(z)] if z > 0 else -umap[abs(z)]
                    for z in bit_succ]
        # add new MDD node at level j
        j = dvars[var]['level']
        r = mdd.find_or_add(j, *int_succ)
        # cache
        # signed r, because low never inverted,
        # opposite to canonicity chosen for BDDs
        umap[u] = r
    return mdd, umap


def _enumerate_integer(bits):
    n = len(bits)
    for i in range(2**n):
        values = list(reversed(bin(i).lstrip('-0b').zfill(n)))
        d = {bit: int(v) for bit, v in zip(bits, values)}
        for bit in bits[len(values):]:
            d[bit] = 0
        yield d


def _debug_dump(pred, bdd):
    """Dump nodes of `bdd`, coloring nodes in `pred`."""
    import networkx as nx
    g = to_nx(bdd, roots=bdd._succ)
    color = 'red'
    for u in pred:
        if u < 1:
            raise ValueError(u)
        g.add_node(u, color=color)
    for u in g:
        if u < 1:
            raise AssertionError(u)
        if u == 1:
            continue
        level, _, _ = bdd._succ[u]
        var = bdd.var_at_level(level)
        label = '{var}-{u}'.format(var=var, u=u)
        g.add_node(u, label=label)
    pd = nx.drawing.nx_pydot.to_pydot(g)
    pd.write_pdf('bdd_colored.pdf')
    bdd.dump('bdd.pdf')


def to_pydot(mdd):
    import pydot
    g = pydot.Dot('mdd', graph_type='digraph')
    skeleton = list()
    subgraphs = dict()
    n = len(mdd.vars) + 1
    for i in range(n):
        h = pydot.Subgraph('', rank='same')
        g.add_subgraph(h)
        subgraphs[i] = h
        # add phantom node
        u = '-{i}'.format(i=i)
        skeleton.append(u)
        nd = pydot.Node(name=u, label=str(i), shape='none')
        h.add_node(nd)
    # auxiliary edges for ranking
    for i, u in enumerate(skeleton[:-1]):
        v = skeleton[i + 1]
        e = pydot.Edge(str(u), str(v), style='invis')
        g.add_edge(e)
    # add nodes
    for u, t in mdd._succ.items():
        if u <= 0:
            raise AssertionError(u)
        i = t[0]
        nodes = t[1:]
        # terminal ?
        if nodes[0] is None:
            var = '1'
        else:
            var = mdd.var_at_level(i)
        # add node
        label = '{var}-{u}'.format(var=var, u=u)
        nd = pydot.Node(name=str(u), label=label)
        h = subgraphs[i]  # level i
        h.add_node(nd)
        # add edges
        if nodes[0] is None:
            continue
        # has successors
        for j, v in enumerate(nodes):
            label = str(j)
            # tail_label = '-1' if v < 0 else ' '
            if v < 0:
                style = 'dashed'
            else:
                style = 'solid'
            su = str(u)
            sv = str(abs(v))
            e = pydot.Edge(su, sv, label=label,
                           style=style)
            g.add_edge(e)
    return g
