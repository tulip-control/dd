# cython: profile=True
"""Cython interface to BuDDy.


Reference
=========
    Jorn Lind-Nielsen
    "BuDDy: Binary Decision Diagram package"
    IT-University of Copenhagen (ITU)
    v2.4, 2002
    http://buddy.sourceforge.net
"""
import logging
import pprint
import sys
from libcpp cimport bool
from libc.stdio cimport fdopen, fopen
from cpython.mem cimport PyMem_Malloc, PyMem_Free
cimport buddy_ as buddy
APPLY_MAP = {
    'and': 0, 'xor': 1, 'or': 2, 'nand': 3, 'nor': 4,
    'imp': 5, 'biimp': 6, 'diff': 7, 'less': 8, 'invimp': 9}
BDD_REORDER_NONE = 0
BDD_REORDER_WIN2 = 1
BDD_REORDER_WIN2ITE = 2  # "ite" = iteratively
BDD_REORDER_SIFT = 3
BDD_REORDER_SIFTITE = 4
BDD_REORDER_WIN3 = 5
BDD_REORDER_WIN3ITE = 6
BDD_REORDER_RANDOM = 7
BDD_REORDER_FREE = 0
BDD_REORDER_FIXED = 1


logger = logging.getLogger(__name__)


cdef class BDD(object):
    """Wrapper of BuDDy.

    Interface similar to `dd.bdd.BDD`.
    There is only a single global shared BDD,
    so use only one instance.
    """

    cpdef public object var_to_index

    def __cinit__(self):
        self.var_to_index = dict()
        if buddy.bdd_isrunning():
            return
        n_nodes = 10**2
        cache = 10**4
        n_vars = 150
        buddy.bdd_init(n_nodes, cache)
        buddy.bdd_setvarnum(n_vars)
        buddy.bdd_setcacheratio(64)
        buddy.bdd_autoreorder(BDD_REORDER_SIFT)
        buddy.bdd_reorder_verbose(1)

    def __dealloc__(self):
        buddy.bdd_done()

    def __str__(self):
        n = buddy.bdd_getnodenum()
        n_alloc = buddy.bdd_getallocnum()
        n_vars = buddy.bdd_varnum()
        s = (
            'Binary decision diagram (BuDDy wrapper) with:\n'
            '\t {n} live nodes now\n'
            '\t {n_alloc} total nodes allocated\n'
            '\t {n_vars} BDD variables\n').format(
                n=n, n_alloc=n_alloc, n_vars=n_vars)
        return s

    def __len__(self):
        return buddy.bdd_getnodenum()

    cdef incref(self, int u):
        buddy.bdd_addref(u)

    cdef decref(self, int u):
        buddy.bdd_delref(u)

    property false:

        def __get__(self):
            return self._bool(False)

    property true:

        def __get__(self):
            return self._bool(True)

    cdef _bool(self, b):
        if b:
            r = buddy.bdd_true()
        else:
            r = buddy.bdd_false()
        return Function(r)

    cpdef int add_var(self, str var):
        """Return index for variable `var`."""
        j = self.var_to_index.get(var)
        if j is not None:
            return j
        j = len(self.var_to_index)
        self.var_to_index[var] = j
        # new block for reordering
        buddy.bdd_intaddvarblock(j, j, 0)
        return j

    cpdef Function var(self, str var):
        """Return BDD for variable `var`."""
        assert var in self.var_to_index, (
            var, self.var_to_index)
        j = self.var_to_index[var]
        r = buddy.bdd_ithvar(j)
        assert r != self.false.node, 'failed'
        buddy.bdd_intaddvarblock(j, j, 0)
        return Function(r)

    cpdef int level(self, str var):
        """Return level of variable `var`."""
        j = self.add_var(var)
        level = buddy.bdd_var2level(j)
        return level

    cpdef int at_level(self, int level):
        level = buddy.bdd_level2var(level)
        index_to_var = {
            v: k for k, v in self.var_to_index.iteritems()}
        j = index_to_var[level]
        return j

    cpdef apply(self, op, u, v=None):
        """Return as `Function` the result of applying `op`."""
        # unary
        if op in ('!', 'not'):
            assert v is None
            r = buddy.bdd_not(u.node)
        else:
            assert v is not None
        # binary
        if op in ('&', 'and'):
            r = buddy.bdd_and(u.node, v.node)
        elif op in ('|', 'or'):
            r = buddy.bdd_or(u.node, v.node)
        elif op in ('^', 'xor'):
            r = buddy.bdd_xor(u.node, v.node)
        return Function(r)

    cpdef quantify(self, u, qvars, forall=False):
        cube = self.cube(qvars)
        if forall:
            r = buddy.bdd_forall(u, cube)
        else:
            r = buddy.bdd_exist(u, cube)
        return Function(r)

    cpdef cube(self, dvars):
        """Return a positive unate cube for `dvars`."""
        n = len(dvars)
        cdef int *x
        x = <int *> PyMem_Malloc(n * sizeof(int))
        for i, var in enumerate(dvars):
            j = self.add_var(var)
            x[i] = j
        try:
            r = buddy.bdd_makeset(x, n)
        finally:
            PyMem_Free(x)
        return Function(r)

    cpdef assert_consistent(self):
        # TODO: implement this
        pass


cpdef and_abstract(u, v, qvars, bdd):
    """Return `? qvars. u & v`."""
    cube = bdd.cube(qvars)
    op = APPLY_MAP['and']
    r = buddy.bdd_appex(u.node, v.node, op, cube.node)
    return Function(r)


cpdef or_abstract(u, v, qvars, bdd):
    """Return `! qvars. u | v`."""
    cube = bdd.cube(qvars)
    op = APPLY_MAP['or']
    r = buddy.bdd_appall(u.node, v.node, op, cube.node)
    return Function(r)


def rename(u, bdd, dvars):
    n = len(dvars)
    cdef int *oldvars
    cdef int *newvars
    oldvars = <int *> PyMem_Malloc(n * sizeof(int))
    newvars = <int *> PyMem_Malloc(n * sizeof(int))
    for i, (a, b) in enumerate(dvars.iteritems()):
        ja = bdd.add_var(a)
        jb = bdd.add_var(b)
        oldvars[i] = ja
        newvars[i] = jb
    cdef buddy.bddPair *pair = buddy.bdd_newpair()
    try:
        buddy.bdd_setpairs(pair, oldvars, newvars, n)
        r = buddy.bdd_replace(u.node, pair)
    finally:
        buddy.bdd_freepair(pair)
        PyMem_Free(oldvars)
        PyMem_Free(newvars)
    return Function(r)


cdef class Function(object):
    """Wrapper for nodes of `BDD`.

    Takes care of reference counting,
    using the `weakref`s.

    Use as:

    ```
    bdd = BDD()
    u = bdd_true()
    f = Function(u)
    h = g | ~ f
    ```
    """

    cdef object __weakref__
    cpdef public int node

    def __cinit__(self, node):
        self.node = node
        buddy.bdd_addref(node)

    def __dealloc__(self):
        buddy.bdd_delref(self.node)

    def __str__(self):
        n = len(self)
        return 'Function({u}, {n})'.format(
            u=self.node, n=n)

    def __len__(self):
        return buddy.bdd_nodecount(self.node)

    def __richcmp__(self, other, op):
        if other is None:
            eq = False
        else:
            eq = (self.node == other.node)
        if op == 2:
            return eq
        elif op == 3:
            return not eq
        else:
            raise Exception('Only `==` and `!=` defined.')

    def __invert__(self):
        r = buddy.bdd_not(self.node)
        return Function(r)

    def __and__(self, other):
        r = buddy.bdd_and(self.node, other.node)
        return Function(r)

    def __or__(self, other):
        r = buddy.bdd_or(self.node, other.node)
        return Function(r)
