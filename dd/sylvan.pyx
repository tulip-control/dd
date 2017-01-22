"""Cython interface to Sylvan.


Reference
=========
    Tom van Dijk, Alfons Laarman, Jaco van de Pol
    "Multi-Core BDD Operations for
     Symbolic Reachability"
    PDMC 2012
    doi:10.1016/j.entcs.2013.07.009
    https://github.com/utwente-fmt/sylvan
"""
# Copyright 2016 by California Institute of Technology
# All rights reserved. Licensed under BSD-3.
#
import logging
import pickle
# import pprint
# import sys
import signal
import time

from libcpp cimport bool
# from libc.stdio cimport FILE, fdopen, fopen, fclose
# from cpython.mem cimport PyMem_Malloc, PyMem_Free
import psutil

from dd import _parser
# from dd import bdd as _bdd
from dd cimport c_sylvan as sy


GB = 2**30
logger = logging.getLogger(__name__)


# TODO: check for invalid nodes returned by sylvan calls


cdef class BDD(object):
    """Wrapper of Sylvan manager.

    Interface similar to `dd.bdd.BDD`.
    Variable names are strings.
    Attributes:

      - `vars`: `set` of bit names as strings
    """

    cpdef public object vars
    cpdef public object _index_of_var
    cpdef public object _var_with_index
    cpdef public object _false
    cpdef public object _true

    def __cinit__(self):
        """Initialize BDD manager.

        Due to the architecture of `sylvan`,
        there is a single unique table,
        so you can create only one `BDD` instance at
        any given time.

        If the current `BDD` instance is `del`eted,
        then a new `BDD` instance can be created.
        But two `BDD` instances cannot coexist in
        the same process.
        """
        sy.lace_init(0, 1000000)
        sy.lace_startup(0, NULL, NULL)
        sy.LACE_ME
        sy.sylvan_init_package(1LL<<25, 1LL<<26, 1LL<<24, 1LL<<25)
        sy.sylvan_init_bdd(1)

    def __init__(self,
                 memory_estimate=None,
                 initial_cache_size=None):
        # self.configure(reordering=True, max_cache_hard=MAX_CACHE)
        self.vars = set()
        self._index_of_var = dict()  # map: str -> unique fixed int
        self._var_with_index = dict()
        self._false = self._bool(False)
        self._true = self._bool(True)

    def __dealloc__(self):
        # n = len(self)
        # assert n == 0, (
        #     'Still {n} nodes '
        #     'referenced upon shutdown.').format(n=n)
        sy.LACE_ME
        sy.sylvan_quit()
        sy.lace_exit()

    def __richcmp__(BDD self, BDD other, op):
        """Return `True` if `other` has same manager."""
        if other is None:
            eq = False
        # `sylvan` supports one manager only
        if op == 2:
            return eq
        elif op == 3:
            return not eq
        else:
            raise Exception('Only __eq__ and __ne__ defined')

    def __len__(self):
        """Return number of nodes with non-zero references."""
        sy.LACE_ME
        return sy.sylvan_count_refs()

    def __contains__(self, Function u):
        try:
            self.apply('not', u)
            return True
        except:
            return False

    def __str__(self):
        s = 'Binary decision diagram (Sylvan wrapper)'
        return s

    def configure(self, **kw):
        """Has no effect, present for compatibility only."""
        # TODO: use `sy.gc_enabled == 1` when not `static`
        garbage_collection = None
        d = dict(
            reordering=False,
            garbage_collection=garbage_collection,
            max_memory=None,
            loose_up_to=None,
            max_cache_soft=None,
            max_cache_hard=None,
            min_hit=None,
            max_growth=None,
            max_swaps=None,
            max_vars=None)
        return d

    cdef incref(self, sy.BDD u):
        sy.sylvan_ref(u)

    cdef decref(self, sy.BDD u):
        sy.sylvan_deref(u)

    cpdef add_var(self, var, index=None):
        """Return index of variable named `var`.

        If a variable named `var` exists,
        the assert that it has `index`.
        Otherwise, create a variable named `var`
        with `index` (if given).

        If no reordering has yet occurred,
        then the returned index equals the level,
        provided `add_var` has been used so far.
        """
        sy.LACE_ME
        # var already exists ?
        j = self._index_of_var.get(var)
        if j is not None:
            assert j == index or index is None, (j, index)
            return j
        # new var
        if index is None:
            index = len(self._index_of_var)
        j = index
        u = sy.sylvan_ithvar(j)
        assert u != sy.sylvan_invalid, (
            'failed to add var "{v}"'.format(v=var))
        self._add_var(var, j)
        return j

    cpdef insert_var(self, var, level):
        """Create a new variable named `var`, at `level`."""
        raise Exception(
            'in `sylvan`, variable indices equal levels.\n'
            'Call method `BDD.add_var` instead.')

    cdef _add_var(self, str var, int index):
        """Add to `self` a *new* variable named `var`."""
        assert var not in self.vars
        assert var not in self._index_of_var
        assert index not in self._var_with_index
        self.vars.add(var)
        self._index_of_var[var] = index
        self._var_with_index[index] = var
        assert (len(self._index_of_var) ==
            len(self._var_with_index))

    cpdef Function var(self, var):
        """Return node for variable named `var`."""
        assert var in self._index_of_var, (
            'undefined variable "{v}", '
            'known variables are:\n {d}').format(
                v=var, d=self._index_of_var)
        sy.LACE_ME
        j = self._index_of_var[var]
        r = sy.sylvan_ithvar(j)
        f = Function()
        f.init(r)
        return f

    def var_at_level(self, level):
        """Return name of variable at `level`."""
        j = level  # indices equal levels in `sylvan`
        assert j in self._var_with_index, (j, self._var_with_index)
        var = self._var_with_index[j]
        return var

    def level_of_var(self, var):
        """Return level of variable named `var`."""
        assert var in self._index_of_var, (
            'undefined variable "{v}", '
            'known variables are:\n {d}').format(
                v=var, d=self._index_of_var)
        j = self._index_of_var[var]
        level = j
        return level

    cpdef set support(self, Function f):
        """Return the variables that node `f` depends on."""
        sy.LACE_ME
        cdef sy.BDD cube
        cube = sy.sylvan_support(f.node)
        ids = set()
        while cube != sy.sylvan_true:
            # get var
            j = sy.sylvan_var(cube)
            ids.add(j)
            # descend
            u = sy.sylvan_low(cube)
            v = sy.sylvan_high(cube)
            assert u == sy.sylvan_false
            cube = v
        support = {self._var_with_index[j] for j in ids}
        return support

    cpdef Function compose(self, Function u, var_sub):
        sy.LACE_ME
        cdef sy.BDDMAP map
        cdef sy.BDDVAR j
        cdef sy.BDD r
        cdef Function g
        map = sy.sylvan_map_empty()
        for var, g in var_sub.iteritems():
            j = self._index_of_var[var]
            map = sy.sylvan_map_add(map, j, g.node)
        r = sy.sylvan_compose(u.node, map)
        f = Function()
        f.init(r)
        return f

    cpdef Function cofactor(self, Function u, values):
        """Return the cofactor f|_g."""
        var_sub = {
            var: self.true if value else self.false
            for var, value in values.iteritems()}
        return self.compose(u, var_sub)

    cpdef Function rename(self, u, dvars):
        """Return node `u` after renaming variables in `dvars`."""
        var_sub = {
            var: self.var(sub) for var, sub in dvars.iteritems()}
        r = self.compose(u, var_sub)
        return r

    def sat_iter(self, Function u,
                 full=False, care_bits=None):
        """Return generator over assignments."""
        raise NotImplementedError

    cpdef Function ite(self, Function g, Function u, Function v):
        sy.LACE_ME
        cdef sy.BDD r
        r = sy.sylvan_ite(g.node, u.node, v.node)
        f = Function()
        f.init(r)
        return f

    cpdef Function apply(self, op, Function u, Function v=None):
        """Return as `Function` the result of applying `op`."""
        cdef sy.BDD r
        sy.LACE_ME
        # unary
        if op in ('~', 'not', '!'):
            assert v is None
            r = sy.sylvan_not(u.node)
        else:
            assert v is not None
        # binary
        if op in ('and', '/\\', '&', '&&'):
            r = sy.sylvan_and(u.node, v.node)
        elif op in ('or', r'\/', '|', '||'):
            r = sy.sylvan_or(u.node, v.node)
        elif op in ('xor', '^'):
            r = sy.sylvan_xor(u.node, v.node)
        elif op in ('=>', '->', 'implies'):
            r = sy.sylvan_imp(u.node, v.node)
        elif op in ('<=>', '<->', 'equiv'):
            r = sy.sylvan_biimp(u.node, v.node)
        elif op in ('diff', '-'):
            r = sy.sylvan_diff(u.node, v.node)
        elif op in ('\A', 'forall'):
            r = sy.sylvan_forall(u.node, v.node)
        elif op in ('\E', 'exists'):
            r = sy.sylvan_exists(u.node, v.node)
        if r == sy.sylvan_invalid:
            raise Exception(
                'unknown operator: "{op}"'.format(op=op))
        f = Function()
        f.init(r)
        return f

    cpdef Function cube(self, dvars):
        """Return node for cube over `dvars`.

        @param dvars: `dict` that maps each variable to a `bool`.
            If `set` given, then all values assumed `True`.
        """
        # TODO: call sylvan cube function
        u = self.true
        if isinstance(dvars, set):
            for var in dvars:
                u &= self.var(var)
            return u
        for var, sign in dvars.iteritems():
            v = self.var(var)
            if sign is False:
                v = ~v
            u &= v
        return u

    cpdef Function quantify(self, Function u,
                            qvars, forall=False):
        """Abstract variables `qvars` from node `u`."""
        sy.LACE_ME
        c = set(qvars)
        cube = self.cube(c)
        # quantify
        if forall:
            r = sy.sylvan_forall(u.node, cube.node)
        else:
            r = sy.sylvan_exists(u.node, cube.node)
        # wrap
        f = Function()
        f.init(r)
        return f

    cpdef Function forall(self, qvars, Function u):
        """Quantify `qvars` in `u` universally.

        Wraps method `quantify` to be more readable.
        """
        return self.quantify(u, qvars, forall=True)

    cpdef Function exist(self, qvars, Function u):
        """Quantify `qvars` in `u` existentially.

        Wraps method `quantify` to be more readable.
        """
        return self.quantify(u, qvars, forall=False)

    cpdef assert_consistent(self):
        """Raise `AssertionError` if not consistent."""
        # assert Cudd_DebugCheck(self.manager) == 0
        n = len(self.vars)
        m = len(self._var_with_index)
        k = len(self._index_of_var)
        assert n == m, (n, m)
        assert m == k, (m, k)

    def add_expr(self, e):
        """Return node for `str` expression `e`."""
        return _parser.add_expr(e, self)

    def to_expr(self, u):
        raise NotImplementedError

    cpdef dump(self, Function u, fname):
        """Dump BDD as DDDMP file `fname`."""
        raise NotImplementedError

    cpdef load(self, fname):
        """Return `Function` loaded from file `fname`."""
        raise NotImplementedError

    @property
    def false(self):
        """`Function` for Boolean value false."""
        return self._false

    @property
    def true(self):
        """`Function` for Boolean value true."""
        return self._true

    cdef Function _bool(self, v):
        """Return terminal node for Boolean `v`."""
        cdef sy.BDD r
        if v:
            r = sy.sylvan_true
        else:
            r = sy.sylvan_false
        f = Function()
        f.init(r)
        return f


cpdef Function restrict(Function u, Function care_set):
    sy.LACE_ME
    cdef sy.BDD r
    r = sy.sylvan_restrict(u.node, care_set.node)
    f = Function()
    f.init(r)
    return f


cpdef Function and_exists(Function u, Function v, qvars, BDD bdd):
    """Return `\E qvars:  u /\ v`."""
    sy.LACE_ME
    cube = bdd.cube(qvars)
    r = sy.sylvan_and_exists(u.node, v.node, cube.node)
    f = Function()
    f.init(r)
    return f


cpdef Function or_forall(Function u, Function v, qvars, BDD bdd):
    """Return `\A qvars:  u \/ v`."""
    sy.LACE_ME
    cube = bdd.cube(qvars)
    r = sy.sylvan_and_exists(
        sy.sylvan_not(u.node),
        sy.sylvan_not(v.node),
        cube.node)
    r = sy.sylvan_not(r)
    f = Function()
    f.init(r)
    return f


cpdef reorder(BDD bdd, dvars=None):
    """Reorder `bdd` to order in `dvars`.

    If `dvars` is `None`, then invoke group sifting.
    """
    raise NotImplementedError


def copy_vars(BDD source, BDD target):
    """Copy variables, preserving Sylvan indices.

    @type source, target: `BDD`
    """
    for var, index in source._index_of_var.iteritems():
        target.add_var(var, index=index)


cdef class Function(object):
    """Wrapper of `BDD` from Sylvan.

    Attributes:

      - `index`
      - `ref`
      - `low`
      - `high`

    In Python, use as:
    ```
    bdd = BDD()
    u = bdd.true
    v = bdd.false
    w = u | ~ v

    In Cython, use as:

    ```
    bdd = BDD()
    cdef sy.BDD u
    u = sylvan_true
    f = Function()
    f.init(u)
    ```
    """

    cdef object __weakref__
    cpdef sy.BDD node

    cdef init(self, sy.BDD u):
        assert u != sy.sylvan_invalid, (
            '`sy.BDD u` is `NULL` pointer.')
        self.node = u
        sy.sylvan_ref(u)

    @property
    def index(self):
        """Index of `self.node`."""
        return sy.sylvan_var(self.node)

    @property
    def ref(self):
        """Sum of reference counts of node and its negation."""
        # u = Cudd_Regular(self.node)
        # return u.ref
        raise NotImplementedError

    @property
    def low(self):
        """Return "else" node as `Function`."""
        u = sy.sylvan_low(self.node)
        f = Function()
        f.init(u)
        return f

    @property
    def high(self):
        """Return "then" node as `Function`."""
        u = sy.sylvan_high(self.node)
        f = Function()
        f.init(u)
        return f

    @property
    def negated(self):
        """Return `True` if `self` is a complemented edge."""
        # see `BDD_HASMARK` in `sylvan_bdd`
        return ((self.node & sy.sylvan_complement) == 1)

    def __dealloc__(self):
        sy.sylvan_deref(self.node)

    def __str__(self):
        return (
            'Function(DdNode with: '
            'node={node}, '
            'var_index={idx}, '
            'ref_count={ref})').format(
                node=self.node,
                idx=self.index,
                ref=None)

    def __len__(self):
        return sy.sylvan_nodecount(self.node)

    def __richcmp__(Function self, Function other, op):
        if other is None:
            eq = False
        else:
            # guard against mixing managers
            # assert self.manager == other.manager
            eq = (self.node == other.node)
        if op == 2:
            return eq
        elif op == 3:
            return not eq
        else:
            raise Exception('Only `__eq__` and `__ne__` defined.')

    def __invert__(Function self):
        r = sy.sylvan_not(self.node)
        f = Function()
        f.init(r)
        return f

    def __and__(Function self, Function other):
        sy.LACE_ME
        r = sy.sylvan_and(self.node, other.node)
        f = Function()
        f.init(r)
        return f

    def __or__(Function self, Function other):
        sy.LACE_ME
        r = sy.sylvan_or(self.node, other.node)
        f = Function()
        f.init(r)
        return f
