"""Cython interface to CUDD.


Reference
=========
    Fabio Somenzi
    "CUDD: CU Decision Diagram Package"
    University of Colorado at Boulder
    v2.5.1, 2015
    http://vlsi.colorado.edu/~fabio/
"""
import logging
import pickle
import pprint
import sys
import time
from dd import _parser
from dd import _compat
from dd import bdd as _bdd
from libcpp cimport bool
from libc.stdio cimport FILE, fdopen, fopen, fclose
from libc cimport stdint
from cpython.mem cimport PyMem_Malloc, PyMem_Free
import psutil


cdef extern from 'cuddInt.h':
    # subtable (for a level)
    cdef struct DdSubtable:
        unsigned int slots
        unsigned int keys
    # manager
    cdef struct DdManager:
        DdSubtable *subtables
        unsigned int keys
        unsigned int dead
        double cachecollisions
        double cacheinserts
        double cachedeletions
cdef extern from 'cudd.h':
    # node
    ctypedef unsigned int DdHalfWord
    cdef struct DdNode:
        DdHalfWord index
        DdHalfWord ref
    ctypedef DdNode DdNode

    ctypedef DdManager DdManager
    cdef DdManager *Cudd_Init(
        unsigned int numVars,
        unsigned int numVarsZ,
        unsigned int numSlots,
        unsigned int cacheSize,
        unsigned long maxMemory)
    cdef struct DdGen
    ctypedef enum Cudd_ReorderingType:
        pass
    # node elements
    cdef DdNode *Cudd_bddNewVar(DdManager *dd)
    cdef DdNode *Cudd_bddNewVarAtLevel(DdManager *dd, int level)
    cdef DdNode *Cudd_bddIthVar(DdManager *dd, int i)
    cdef DdNode *Cudd_ReadLogicZero(DdManager *dd)
    cdef DdNode *Cudd_ReadOne(DdManager *dd)
    cdef DdNode *Cudd_Regular(DdNode *u)
    cdef bool Cudd_IsConstant(DdNode *u)
    cdef unsigned int Cudd_NodeReadIndex(DdNode *u)
    cdef DdNode *Cudd_T(DdNode *u)
    cdef DdNode *Cudd_E(DdNode *u)
    cdef bool Cudd_IsComplement(DdNode *u)
    cdef int Cudd_DagSize(DdNode *node)
    cdef int Cudd_SharingSize(DdNode **nodeArray, int n)
    # basic Boolean operators
    cdef DdNode *Cudd_Not(DdNode *dd)
    cdef DdNode *Cudd_bddIte(DdManager *dd, DdNode *f,
                             DdNode *g, DdNode *h)
    cdef DdNode *Cudd_bddAnd(DdManager *dd,
                             DdNode *dd, DdNode *dd)
    cdef DdNode *Cudd_bddOr(DdManager *dd,
                            DdNode *dd, DdNode *dd)
    cdef DdNode *Cudd_bddXor(DdManager *dd,
                             DdNode *f, DdNode *g)
    cdef DdNode *Cudd_Support(DdManager *dd, DdNode *f)
    cdef DdNode *Cudd_bddComputeCube(
        DdManager *dd, DdNode **vars, int *phase, int n)
    cdef DdNode *Cudd_CubeArrayToBdd(DdManager *dd, int *array)
    cdef int Cudd_BddToCubeArray(DdManager *dd, DdNode *cube,
                                 int *array)
    cdef int Cudd_PrintMinterm(DdManager *dd, DdNode *f)
    cdef DdNode *Cudd_Cofactor(DdManager *dd, DdNode *f, DdNode *g)
    cdef DdNode *Cudd_bddCompose(DdManager *dd,
                                 DdNode *f, DdNode *g, int v)
    cdef DdNode *Cudd_bddVectorCompose(DdManager *dd,
                                       DdNode *f, DdNode **vector)
    cdef DdNode *Cudd_bddRestrict(DdManager *dd, DdNode *f, DdNode *c)
    # cubes
    cdef DdGen *Cudd_FirstCube(DdManager *dd, DdNode *f,
                               int **cube, double *value)
    cdef int Cudd_NextCube(DdGen *gen, int **cube, double *value)
    cdef int Cudd_IsGenEmpty(DdGen *gen)
    cdef int Cudd_GenFree(DdGen *gen)
    # refs
    cdef void Cudd_Ref(DdNode *n)
    cdef void Cudd_RecursiveDeref(DdManager *table,
                                  DdNode *n)
    cdef void Cudd_Deref(DdNode *n)
    # checks
    cdef int Cudd_CheckZeroRef(DdManager *manager)
    cdef int Cudd_DebugCheck(DdManager *table)
    cdef void Cudd_Quit(DdManager *unique)
    cdef DdNode *Cudd_bddTransfer(
        DdManager *ddSource, DdManager *ddDestination, DdNode *f)
    # info
    cdef int Cudd_PrintInfo(DdManager *dd, FILE *fp)
    cdef int Cudd_ReadSize(DdManager *dd)
    cdef long Cudd_ReadNodeCount(DdManager *dd)
    cdef long Cudd_ReadPeakNodeCount(DdManager *dd)
    cdef int Cudd_ReadPeakLiveNodeCount(DdManager *dd)
    cdef unsigned long Cudd_ReadMemoryInUse(DdManager *dd)
    cdef unsigned int Cudd_ReadSlots(DdManager *dd)
    cdef double Cudd_ReadUsedSlots(DdManager *dd)
    cdef double Cudd_ExpectedUsedSlots(DdManager *dd)
    cdef unsigned int Cudd_ReadCacheSlots(DdManager *dd)
    cdef double Cudd_ReadCacheUsedSlots(DdManager *dd)
    cdef double Cudd_ReadCacheLookUps(DdManager *dd)
    cdef double Cudd_ReadCacheHits(DdManager *dd)
    # reordering
    cdef int Cudd_ReduceHeap(DdManager *table,
                             Cudd_ReorderingType heuristic,
                             int minsize)
    cdef int Cudd_ShuffleHeap(DdManager *table, int *permutation)
    cdef void Cudd_AutodynEnable(DdManager *unique,
                                 Cudd_ReorderingType method)
    cdef void Cudd_AutodynDisable(DdManager *unique)
    cdef int Cudd_ReorderingStatus(DdManager * unique,
                                   Cudd_ReorderingType * method)
    cdef unsigned int Cudd_ReadReorderings(DdManager *dd)
    cdef long Cudd_ReadReorderingTime(DdManager *dd)
    cdef int Cudd_ReadPerm(DdManager *dd, int i)
    cdef int Cudd_ReadInvPerm(DdManager *dd, int i)
    cdef void Cudd_SetSiftMaxSwap(DdManager *dd, int sms)
    cdef int Cudd_ReadSiftMaxSwap(DdManager *dd)
    cdef void Cudd_SetSiftMaxVar(DdManager *dd, int smv)
    cdef int Cudd_ReadSiftMaxVar(DdManager *dd)
    # manager config
    cdef unsigned long Cudd_ReadMaxMemory(DdManager *dd)
    cdef void Cudd_SetMaxMemory(DdManager *dd,
                                unsigned long maxMemory)
    cdef unsigned int Cudd_ReadMaxCacheHard(DdManager *dd)
    cdef unsigned int Cudd_ReadMaxCache(DdManager *dd)
    cdef void Cudd_SetMaxCacheHard(DdManager *dd, unsigned int mc)
    cdef double Cudd_ReadMaxGrowth(DdManager *dd)
    cdef void Cudd_SetMaxGrowth(DdManager *dd, double mg)
    cdef unsigned int Cudd_ReadMinHit(DdManager *dd)
    cdef void Cudd_SetMinHit(DdManager *dd, unsigned int hr)
    cdef void Cudd_EnableGarbageCollection(DdManager *dd)
    cdef void Cudd_DisableGarbageCollection(DdManager *dd)
    cdef int Cudd_GarbageCollectionEnabled(DdManager * dd)
    cdef unsigned int Cudd_ReadLooseUpTo(DdManager *dd)
    cdef void Cudd_SetLooseUpTo(DdManager *dd, unsigned int lut)
    # quantification
    cdef DdNode *Cudd_bddExistAbstract(
        DdManager *manager, DdNode *f, DdNode *cube)
    cdef DdNode *Cudd_bddUnivAbstract(
        DdManager *manager, DdNode *f, DdNode *cube)
    cdef DdNode *Cudd_bddAndAbstract(
        DdManager *manager, DdNode *f, DdNode *g, DdNode *cube)
    cdef DdNode *Cudd_bddSwapVariables(
        DdManager *dd,
        DdNode *f, DdNode **x, DdNode **y, int n)
cdef CUDD_UNIQUE_SLOTS = 2**8
cdef CUDD_CACHE_SLOTS = 2**18
cdef CUDD_REORDER_GROUP_SIFT = 14
cdef MAX_CACHE = <unsigned int> - 1


# TODO: replace DDDMP
cdef extern from 'dddmp.h':
    ctypedef enum Dddmp_VarInfoType:
        pass
    ctypedef enum Dddmp_VarMatchType:
        pass
    cdef int Dddmp_cuddBddStore(
        DdManager *ddMgr,
        char *ddname,
        DdNode *f,
        char **varnames,
        int *auxids,
        int mode,
        Dddmp_VarInfoType varinfo,
        char *fname,
        FILE *fp)
    cdef DdNode *Dddmp_cuddBddLoad(
        DdManager *ddMgr,
        Dddmp_VarMatchType varMatchMode,
        char **varmatchnames,
        int *varmatchauxids,
        int *varcomposeids,
        int mode,
        char *fname,
        FILE *fp)
cdef DDDMP_MODE_TEXT = 65  # <int>'A'
cdef DDDMP_VARIDS = 0
cdef DDDMP_VARNAMES = 3
cdef DDDMP_VAR_MATCHNAMES = 3
cdef DDDMP_SUCCESS = 1


GB = 2**30
DEFAULT_MEMORY = 1 * GB
logger = logging.getLogger(__name__)


cdef class BDD(object):
    """Wrapper of CUDD manager.

    Interface similar to `dd.bdd.BDD`.
    Variable names are strings.
    Attributes:

      - `vars`: `set` of bit names as `str`ings
    """

    cdef DdManager *manager
    cpdef public object vars
    cpdef public object _index_of_var
    cpdef public object _var_with_index
    cpdef public object _false
    cpdef public object _true

    def __cinit__(self,
                  memory_estimate=None,
                  initial_cache_size=None):
        """Initialize BDD manager.

        @param memory: maximum allowed memory, in bytes.
        """
        total_memory = psutil.virtual_memory().total
        default_memory = DEFAULT_MEMORY
        if memory_estimate is None:
            memory_estimate = default_memory
        if memory_estimate >= total_memory:
            print(
                'Error in `dd.cudd`: '
                'total physical memory is {t} bytes, '
                'but requested {r} bytes').format(
                    t=total_memory,
                    r=memory_estimate)
        assert memory_estimate < total_memory, (
            memory_estimate, total_memory)
        if initial_cache_size is None:
            initial_cache_size = CUDD_CACHE_SLOTS
        initial_subtable_size = CUDD_UNIQUE_SLOTS
        initial_n_vars_bdd = 0
        initial_n_vars_zdd = 0
        mgr = Cudd_Init(
            initial_n_vars_bdd,
            initial_n_vars_zdd,
            initial_subtable_size,
            initial_cache_size,
            memory_estimate)
        assert mgr != NULL, 'failed to init CUDD DdManager'
        self.manager = mgr

    def __init__(self,
                 memory_estimate=None,
                 initial_cache_size=None):
        self.configure(reordering=True, max_cache_hard=MAX_CACHE)
        self.vars = set()
        self._index_of_var = dict()  # map: str -> unique fixed int
        self._var_with_index = dict()
        self._false = self._bool(False)
        self._true = self._bool(True)

    def __dealloc__(self):
        del self._false
        del self._true
        n = len(self)
        assert n == 0, (
            'Still {n} nodes '
            'referenced upon shutdown.').format(n=n)
        Cudd_Quit(self.manager)

    def __richcmp__(BDD self, BDD other, op):
        """Return `True` if `other` has same manager."""
        if other is None:
            eq = False
        else:
            eq = (self.manager == other.manager)
        if op == 2:
            return eq
        elif op == 3:
            return not eq
        else:
            raise Exception('Only __eq__ and __ne__ defined')

    def __len__(self):
        """Return number of nodes with non-zero references."""
        return Cudd_CheckZeroRef(self.manager)

    def __contains__(self, Function u):
        assert u.manager == self.manager, 'undefined containment'
        try:
            Cudd_NodeReadIndex(u.node)
            return True
        except:
            return False

    def __str__(self):
        d = self.statistics()
        s = (
            'Binary decision diagram (CUDD wrapper) with:\n'
            '\t {n} live nodes now\n'
            '\t {peak} live nodes at peak\n'
            '\t {n_vars} BDD variables\n'
            '\t {mem:10.1f} MB in use\n'
            '\t {reorder_time:10.1f} sec spent reordering\n'
            '\t {n_reorderings} reorderings\n').format(
                n=d['n_nodes'],
                peak=d['peak_live_nodes'],
                n_vars=d['n_vars'],
                reorder_time=d['reordering_time'],
                n_reorderings=d['n_reorderings'],
                mem=d['mem'])
        return s

    def statistics(BDD self, exact_node_count=False):
        """Return `dict` with CUDD node counts and times.

        If `exact_node_count` is `True`, then the
        list of dead nodes is cleared.

        Keys with meaning:

          - `n_vars`: number of variables
          - `n_nodes`: number of live nodes
          - `peak_nodes`: max number of all nodes
          - `peak_live_nodes`: max number of live nodes

          - `reordering_time`: sec spent reordering
          - `n_reorderings`: number of reorderings

          - `mem`: MB in use
          - `unique_size`: total number of buckets in unique table
          - `unique_used_fraction`: buckets that contain >= 1 node
          - `expected_unique_used_fraction`: if properly working

          - `cache_size`: number of slots in cache
          - `cache_used_fraction`: slots with data
          - `cache_lookups`: total number of lookups
          - `cache_hits`: total number of cache hits
          - `cache_insertions`
          - `cache_collisions`
          - `cache_deletions`
        """
        cdef DdManager *mgr
        mgr = self.manager
        n_vars = Cudd_ReadSize(mgr)
        # nodes
        if exact_node_count:
            n_nodes = Cudd_ReadNodeCount(mgr)
        else:
            n_nodes = mgr.keys - mgr.dead
        peak_nodes = Cudd_ReadPeakNodeCount(mgr)
        peak_live_nodes = Cudd_ReadPeakLiveNodeCount(mgr)
        # reordering
        t = Cudd_ReadReorderingTime(mgr)
        reordering_time = t / 1000.0
        n_reorderings = Cudd_ReadReorderings(mgr)
        # memory
        m = Cudd_ReadMemoryInUse(mgr)
        mem = float(m) / 10**6
        # unique table
        unique_size = Cudd_ReadSlots(mgr)
        unique_used_fraction = Cudd_ReadUsedSlots(mgr)
        expected_unique_fraction = Cudd_ExpectedUsedSlots(mgr)
        # cache
        cache_size = Cudd_ReadCacheSlots(mgr)
        cache_used_fraction = Cudd_ReadCacheUsedSlots(mgr)
        cache_lookups = Cudd_ReadCacheLookUps(mgr)
        cache_hits = Cudd_ReadCacheHits(mgr)
        cache_insertions = mgr.cacheinserts
        cache_collisions = mgr.cachecollisions
        cache_deletions = mgr.cachedeletions
        d = dict(
            n_vars=n_vars,
            n_nodes=n_nodes,
            peak_nodes=peak_nodes,
            peak_live_nodes=peak_live_nodes,
            reordering_time=reordering_time,
            n_reorderings=n_reorderings,
            mem=mem,
            unique_size=unique_size,
            unique_used_fraction=unique_used_fraction,
            expected_unique_used_fraction=expected_unique_fraction,
            cache_size=cache_size,
            cache_used_fraction=cache_used_fraction,
            cache_lookups=cache_lookups,
            cache_hits=cache_hits,
            cache_insertions=cache_insertions,
            cache_collisions=cache_collisions,
            cache_deletions=cache_deletions)
        return d

    def configure(BDD self, **kw):
        """Read and apply parameter values.

        First read (returned), then apply `kw`.
        Available keyword arguments:

          - `'reordering'`: if `True` then enable, else disable
          - `'garbage_collection'`: if `True` then enable,
              else disable
          - `'max_memory'`: in bytes
          - `'loose_up_to'`: unique table fast growth upper bound
          - `'max_cache_hard'`: cache entries upper bound
          - `'min_hit'`: hit ratio for resizing cache
          - `'max_growth'`: intermediate growth during sifting
          - `'max_swaps'`: no more level swaps in one sifting
          - `'max_vars'`: no more variables moved in one sifting

        For more details, see `cuddAPI.c`.
        Example usage:

        ```
        import dd.cudd

        bdd = dd.cudd.BDD()
        # store old settings, and apply new settings
        cfg = bdd.configure(
            max_memory=12 * 1024**3,
            loose_up_to=5 * 10**6,
            max_cache_hard=MAX_CACHE,
            min_hit=20,
            max_growth=1.5)
        # something fancy
        # ...
        # restore old settings
        bdd.configure(**cfg)
        ```
        """
        cdef int method
        cdef DdManager *mgr
        mgr = self.manager
        # read
        reordering = Cudd_ReorderingStatus(
            mgr, <Cudd_ReorderingType *>&method)
        garbage_collection = Cudd_GarbageCollectionEnabled(mgr)
        max_memory = Cudd_ReadMaxMemory(mgr)
        loose_up_to = Cudd_ReadLooseUpTo(mgr)
        max_cache_soft = Cudd_ReadMaxCache(mgr)
        max_cache_hard = Cudd_ReadMaxCacheHard(mgr)
        min_hit = Cudd_ReadMinHit(mgr)
        max_growth = Cudd_ReadMaxGrowth(mgr)
        max_swaps = Cudd_ReadSiftMaxSwap(mgr)
        max_vars = Cudd_ReadSiftMaxVar(mgr)
        d = dict(
            reordering=True if reordering == 1 else False,
            garbage_collection=True
                if garbage_collection == 1
                else False,
            max_memory=max_memory,
            loose_up_to=loose_up_to,
            max_cache_soft=max_cache_soft,
            max_cache_hard=max_cache_hard,
            min_hit=min_hit,
            max_growth=max_growth,
            max_swaps=max_swaps,
            max_vars=max_vars)
        # set
        for k, v in kw.items():
            if k == 'reordering':
                if v:
                    Cudd_AutodynEnable(mgr, CUDD_REORDER_GROUP_SIFT)
                else:
                    Cudd_AutodynDisable(mgr)
            elif k == 'garbage_collection':
                if v:
                    Cudd_EnableGarbageCollection(mgr)
                else:
                    Cudd_DisableGarbageCollection(mgr)
            elif k == 'max_memory':
                Cudd_SetMaxMemory(mgr, v)
            elif k == 'loose_up_to':
                Cudd_SetLooseUpTo(mgr, v)
            elif k == 'max_cache_hard':
                Cudd_SetMaxCacheHard(mgr, v)
            elif k == 'min_hit':
                Cudd_SetMinHit(mgr, v)
            elif k == 'max_growth':
                Cudd_SetMaxGrowth(mgr, v)
            elif k == 'max_swaps':
                Cudd_SetSiftMaxSwap(mgr, v)
            elif k == 'max_vars':
                Cudd_SetSiftMaxVar(mgr, v)
            elif k == 'max_cache_soft':
                logger.warning('"max_cache_soft" not settable.')
            else:
                raise Exception(
                    'Unknown parameter "{k}"'.format(k=k))
        return d

    cpdef succ(self, Function u):
        """Return `(level, low, high)` for `u`."""
        assert u.manager == self.manager
        i = u.level
        v = u.low
        w = u.high
        return i, v, w

    cdef incref(self, DdNode *u):
        Cudd_Ref(u)

    cdef decref(self, DdNode *u, recursive=True):
        if recursive:
            Cudd_RecursiveDeref(self.manager, u)
        else:
            Cudd_Deref(u)

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
        # var already exists ?
        j = self._index_of_var.get(var)
        if j is not None:
            assert j == index or index is None, (j, index)
            return j
        # new var
        if index is None:
            j = len(self._index_of_var)
        else:
            j = index
        u = Cudd_bddIthVar(self.manager, j)
        assert u != NULL, 'failed to add var "{v}"'.format(v=var)
        self._add_var(var, j)
        return j

    cpdef insert_var(self, var, level):
        """Create a new variable named `var`, at `level`."""
        cdef DdNode *r
        r = Cudd_bddNewVarAtLevel(self.manager, level)
        assert r != NULL, 'failed to create var "{v}"'.format(v=var)
        j = r.index
        self._add_var(var, j)
        return j

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
        j = self._index_of_var[var]
        r = Cudd_bddIthVar(self.manager, j)
        f = Function()
        f.init(self.manager, r)
        return f

    def var_at_level(self, level):
        """Return name of variable at `level`."""
        j = Cudd_ReadInvPerm(self.manager, level)
        assert j != -1, 'index {j} out of bounds'.format(j=j)
        # no var there yet ?
        if j == -1:
            return None
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
        level = Cudd_ReadPerm(self.manager, j)
        assert level != -1, 'index {j} out of bounds'.format(j=j)
        return level

    cpdef support(self, Function f):
        """Return the variables that node `f` depends on."""
        assert self.manager == f.manager, f
        cdef DdNode *r
        r = Cudd_Support(self.manager, f.node)
        f = Function()
        f.init(self.manager, r)
        supp = self._cube_to_dict(f)
        # constant ?
        if not supp:
            return set()
        # must be positive unate
        assert set(_compat.values(supp)) == {True}, supp
        return set(supp)

    def copy(self, u, other):
        """Transfer BDD with root `u` to `other`.

        @type other: `BDD`
        @rtype: node
        """
        return copy_bdd(u, self, other)

    cpdef Function ite(self, Function g, Function u, Function v):
        assert g.manager == self.manager
        assert u.manager == self.manager
        assert v.manager == self.manager
        cdef DdNode *r
        r = Cudd_bddIte(self.manager, g.node, u.node, v.node)
        f = Function()
        f.init(self.manager, r)
        return f

    cpdef Function compose(self, Function f, var_sub):
        """Return the composition f|_(var = g).

        @param var_sub: `dict` from variable names to nodes.
        """
        n = len(var_sub)
        if n == 0:
            logger.warning('call without any effect')
            return f
        if n > 1:
            return self._vector_compose(f, var_sub)
        assert n == 1, n
        for var, g in _compat.items(var_sub):
            return self._compose(f, var, g)

    cdef Function _compose(self, Function f, var, Function g):
        """Return single composition."""
        assert f.manager == self.manager
        assert g.manager == self.manager
        cdef DdNode *r
        index = self._index_of_var[var]
        r = Cudd_bddCompose(self.manager, f.node, g.node, index)
        assert r != NULL, 'compose failed'
        f = Function()
        f.init(self.manager, r)
        return f

    cdef Function _vector_compose(self, Function f, var_sub):
        """Return vector composition."""
        assert f.manager == self.manager
        cdef DdNode *r
        cdef DdNode **x
        cdef Function g
        n = len(self.vars)
        assert n > 0, n
        x = <DdNode **> PyMem_Malloc(n *sizeof(DdNode *))
        for var in self.vars:
            j = self._index_of_var[var]
            if var in var_sub:
                # substitute
                g = var_sub[var]
                assert g.manager == self.manager
                x[j] = g.node
            else:
                # leave var same
                x[j] = Cudd_bddIthVar(self.manager, j)
        try:
            r = Cudd_bddVectorCompose(self.manager, f.node, x)
        finally:
            PyMem_Free(x)
        f = Function()
        f.init(self.manager, r)
        return f

    cpdef Function cofactor(self, Function f, values):
        """Return the cofactor f|_g."""
        assert self.manager == f.manager
        cdef DdNode *r
        cdef Function cube
        cube = self.cube(values)
        r = Cudd_Cofactor(self.manager, f.node, cube.node)
        assert r != NULL, 'cofactor failed'
        h = Function()
        h.init(self.manager, r)
        return h

    cpdef Function rename(self, u, dvars):
        """Return node `u` after renaming variables in `dvars`."""
        return rename(u, self, dvars)

    def sat_iter(self, Function u,
                 full=False, care_bits=None):
        """Return generator over assignments."""
        assert u.manager == self.manager
        cdef DdGen *gen
        cdef int *cube
        cdef double value
        if care_bits is None:
            care_bits = set(self.vars)
        self.configure(reordering=False)
        gen = Cudd_FirstCube(self.manager, u.node, &cube, &value)
        assert gen != NULL, 'first cube failed'
        try:
            r = 1
            while Cudd_IsGenEmpty(gen) == 0:
                assert r == 1, ('gen not empty but no next cube', r)
                d = _cube_array_to_dict(cube, self._index_of_var)
                if not full:
                    yield d
                else:
                    for m in _bdd._enumerate_minterms(d, care_bits):
                        yield m
                r = Cudd_NextCube(gen, &cube, &value)
        finally:
            Cudd_GenFree(gen)
        self.configure(reordering=True)

    cpdef Function apply(
            self,
            op,
            Function u,
            Function v=None,
            Function w=None):
        """Return as `Function` the result of applying `op`."""
        # TODO: add ite, also to slugsin syntax
        assert self.manager == u.manager
        cdef DdNode *r
        cdef DdManager *mgr
        mgr = u.manager
        # unary
        r = NULL
        if op in ('!', 'not'):
            assert v is None
            r = Cudd_Not(u.node)
        else:
            assert v is not None
            assert v.manager == u.manager
        # binary
        if op in ('and', '&', '&&'):
            r = Cudd_bddAnd(mgr, u.node, v.node)
        elif op in ('or', '|', '||'):
            r = Cudd_bddOr(mgr, u.node, v.node)
        elif op in ('xor', '^'):
            r = Cudd_bddXor(mgr, u.node, v.node)
        elif op in ('implies', '->'):
            r = Cudd_bddIte(mgr, u.node, v.node, Cudd_ReadOne(mgr))
        elif op in ('bimplies', '<->'):
            r = Cudd_bddIte(mgr, u.node, v.node, Cudd_Not(v.node))
        elif op in ('diff', '-'):
            r = Cudd_bddIte(mgr, u.node, Cudd_Not(v.node),
                            Cudd_ReadLogicZero(mgr))
        elif op in ('forall', '\A'):
            r = Cudd_bddUnivAbstract(mgr, v.node, u.node)
        elif op in ('exists', '\E'):
            r = Cudd_bddExistAbstract(mgr, v.node, u.node)
        # ternary
        if op == 'ite':
            assert w is not None
            assert w.manager == v.manager
            r = Cudd_bddIte(mgr, u.node, v.node, w.node)
        else:
            assert w is None
        if r == NULL:
            raise Exception(
                'unknown operator: "{op}"'.format(op=op))
        f = Function()
        f.init(mgr, r)
        return f

    cpdef _add_int(self, i):
        """Return node from integer `i`."""
        cdef DdNode *u
        assert i not in (0, 1), i
        # invert `Function.__int__`
        if 2 <= i:
            i -= 2
        u = <DdNode *><stdint.uintptr_t>i
        r = Function()
        r.init(self.manager, u)
        return r

    cpdef Function cube(self, dvars):
        """Return node for cube over `dvars`.

        @param dvars: `dict` that maps each variable to a `bool`
        """
        n = len(self._index_of_var)
        # make cube
        cdef DdNode *cube
        cdef int *x
        x = <int *> PyMem_Malloc(n * sizeof(int))
        _dict_to_cube_array(dvars, x, self._index_of_var)
        try:
            cube = Cudd_CubeArrayToBdd(self.manager, x)
        finally:
            PyMem_Free(x)
        f = Function()
        f.init(self.manager, cube)
        return f

    cdef Function _cube_from_bdds(self, dvars):
        """Return node for cube over `dvars`.

        Only positive unate cubes implemented for now.
        """
        n = len(dvars)
        # make cube
        cdef DdNode *cube
        cdef DdNode **x
        x = <DdNode **> PyMem_Malloc(n * sizeof(DdNode *))
        for i, var in enumerate(dvars):
            f = self.var(var)
            x[i] = f.node
        try:
            cube = Cudd_bddComputeCube(self.manager, x, NULL, n)
        finally:
            PyMem_Free(x)
        f = Function()
        f.init(self.manager, cube)
        return f

    cpdef _cube_to_dict(self, Function f):
        """Recurse to collect indices of support variables."""
        assert f.manager == self.manager
        n = len(self.vars)
        cdef int *x
        x = <int *> PyMem_Malloc(n * sizeof(DdNode *))
        try:
            Cudd_BddToCubeArray(self.manager, f.node, x)
            d = _cube_array_to_dict(x, self._index_of_var)
        finally:
            PyMem_Free(x)
        return d

    cpdef Function quantify(self, Function u,
                            qvars, forall=False):
        """Abstract variables `qvars` from node `u`."""
        assert u.manager == self.manager
        cdef DdManager *mgr = u.manager
        c = set(qvars)
        cube = self.cube(c)
        # quantify
        if forall:
            r = Cudd_bddUnivAbstract(mgr, u.node, cube.node)
        else:
            r = Cudd_bddExistAbstract(mgr, u.node, cube.node)
        # wrap
        f = Function()
        f.init(mgr, r)
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
        assert Cudd_DebugCheck(self.manager) == 0
        n = len(self.vars)
        m = len(self._var_with_index)
        k = len(self._index_of_var)
        assert n == m, (n, m)
        assert m == k, (m, k)

    def add_expr(self, e):
        """Return node for `str` expression `e`."""
        return _parser.add_expr(e, self)

    cpdef str to_expr(self, Function u):
        """Return a Boolean expression for node `u`."""
        assert u.manager == self.manager
        return self._to_expr(u.node)

    cdef str _to_expr(self, DdNode *u):
        if u == Cudd_ReadLogicZero(self.manager):
            return 'False'
        if u == Cudd_ReadOne(self.manager):
            return 'True'
        r = Cudd_Regular(u)
        i = r.index
        v = Cudd_E(u)
        w = Cudd_T(u)
        var = self.var_at_level(i)
        p = self._to_expr(v)
        q = self._to_expr(w)
        # pure var ?
        if p == 'False' and q == 'True':
            s = var
        else:
            s = 'ite({var}, {q}, {p})'.format(var=var, p=p, q=q)
        # complemented ?
        if Cudd_IsComplement(u):
            s = '(! {s})'.format(s=s)
        return s

    cpdef dump(self, Function u, fname):
        """Dump BDD as DDDMP file `fname`."""
        assert u.manager == self.manager
        n = len(self._index_of_var)
        cdef FILE *f
        cdef char **names
        cdef bytes py_bytes
        names = <char **> PyMem_Malloc(n * sizeof(char *))
        str_mem = list()
        for index, var in self._var_with_index.iteritems():
            py_bytes = var.encode()
            str_mem.append(py_bytes)  # prevent garbage collection
            names[index] = py_bytes
        try:
            f = fopen(fname.encode(), 'w')
            i = Dddmp_cuddBddStore(
                self.manager,
                NULL,
                u.node,
                names,
                NULL,
                DDDMP_MODE_TEXT,
                DDDMP_VARNAMES,
                NULL,
                f)
        finally:
            fclose(f)
            PyMem_Free(names)
        assert i == DDDMP_SUCCESS, 'failed to write to DDDMP file'

    cpdef load(self, fname):
        """Return `Function` loaded from file `fname`."""
        n = len(self._index_of_var)
        cdef DdNode *r
        cdef FILE *f
        cdef char **names
        cdef bytes py_bytes
        names = <char **> PyMem_Malloc(n * sizeof(char *))
        str_mem = list()
        for index, var in self._var_with_index.iteritems():
            py_bytes = var.encode()
            str_mem.append(py_bytes)
            names[index] = py_bytes
        try:
            f = fopen(fname.encode(), 'r')
            r = Dddmp_cuddBddLoad(
                self.manager,
                DDDMP_VAR_MATCHNAMES,
                names,
                NULL,
                NULL,
                DDDMP_MODE_TEXT,
                NULL,
                f)
        except:
            raise Exception(
                'A malformed DDDMP file can cause '
                'segmentation faults to `cudd/dddmp`.')
        finally:
            fclose(f)
            PyMem_Free(names)
        assert r != NULL, 'failed to load DDDMP file.'
        h = Function()
        h.init(self.manager, r)
        # `Dddmp_cuddBddArrayLoad` references `r`
        Cudd_RecursiveDeref(self.manager, r)
        return h

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
        cdef DdNode *r
        if v:
            r = Cudd_ReadOne(self.manager)
        else:
            r = Cudd_ReadLogicZero(self.manager)
        f = Function()
        f.init(self.manager, r)
        return f


cpdef Function restrict(Function u, Function care_set):
    """Restrict `u` to `care_set` (1990 Coudert ICCAD)."""
    assert u.manager == care_set.manager
    cdef DdNode *r
    r = Cudd_bddRestrict(u.manager, u.node, care_set.node)
    f = Function()
    f.init(u.manager, r)
    return f


cpdef Function and_exists(Function u, Function v, qvars, BDD bdd):
    """Return `? qvars. u & v`."""
    assert u.manager == bdd.manager
    assert u.manager == v.manager
    mgr = u.manager
    cube = bdd.cube(qvars)
    r = Cudd_bddAndAbstract(u.manager, u.node, v.node, cube.node)
    f = Function()
    f.init(mgr, r)
    return f


cpdef Function or_forall(Function u, Function v, qvars, BDD bdd):
    """Return `! qvars. u | v`."""
    assert u.manager == bdd.manager
    assert u.manager == v.manager
    mgr = u.manager
    cube = bdd.cube(qvars)
    cdef DdNode *r
    r = Cudd_bddAndAbstract(
        u.manager, Cudd_Not(u.node), Cudd_Not(v.node), cube.node)
    r = Cudd_Not(r)
    f = Function()
    f.init(mgr, r)
    return f


cpdef Function rename(Function u, BDD bdd, dvars):
    """Return node `u` after renaming variables in `dvars`."""
    assert u.manager == bdd.manager
    # assert old and new vars are disjoint sets
    target_vars = dvars.values()
    common = set(dvars).intersection(target_vars)
    assert not common, common
    # assert new vars not in support
    support = bdd.support(u)
    common = support.intersection(target_vars)
    assert not common, common
    # rename
    n = len(dvars)
    cdef DdNode **x = <DdNode **> PyMem_Malloc(n * sizeof(DdNode *))
    cdef DdNode **y = <DdNode **> PyMem_Malloc(n * sizeof(DdNode *))
    cdef DdNode *r
    cdef DdManager *mgr = u.manager
    cdef Function f
    for i, xvar in enumerate(dvars):
        yvar = dvars[xvar]
        f = bdd.var(xvar)
        x[i] = f.node
        f = bdd.var(yvar)
        y[i] = f.node
    try:
        r = Cudd_bddSwapVariables(
            mgr, u.node, x, y, n)
        assert r != NULL
    finally:
        PyMem_Free(x)
        PyMem_Free(y)
    f = Function()
    f.init(mgr, r)
    return f


cpdef reorder(BDD bdd, dvars=None):
    """Reorder `bdd` to order in `dvars`.

    If `dvars` is `None`, then invoke group sifting.
    """
    # invoke sifting ?
    if dvars is None:
        Cudd_ReduceHeap(bdd.manager, CUDD_REORDER_GROUP_SIFT, 1)
        return
    # partial reorderings not supported for now
    assert len(dvars) == len(bdd.vars), (
        'Missing variables from new variable order')
    cdef int *p
    n = len(dvars)
    p = <int *> PyMem_Malloc(n * sizeof(int *))
    level_to_var = {v: k for k, v in dvars.iteritems()}
    for level in xrange(n):
        var = level_to_var[level]
        index = bdd._index_of_var[var]
        p[level] = index
    try:
        r = Cudd_ShuffleHeap(bdd.manager, p)
    finally:
        PyMem_Free(p)
    assert r == 1, 'failed to reorder'


def copy_vars(BDD source, BDD target):
    """Copy variables, preserving CUDD indices.

    @type source, target: `BDD`
    """
    for var, index in source._index_of_var.iteritems():
        target.add_var(var, index=index)


cpdef copy_bdd(Function u, BDD source, BDD target):
    """Transfer the node `u` to `bdd`.

    Turns off reordering in `source`
    when checking for missing vars in `target`.

    @type u: `Function` with `u in source`
    @type source, target: `BDD`
    """
    logger.debug('++ transfer bdd')
    assert u.manager == source.manager
    assert u.manager != target.manager
    # target missing vars ?
    cfg = source.configure(reordering=False)
    supp = source.support(u)
    source.configure(reordering=cfg['reordering'])
    missing = {var for var in supp if var not in target.vars}
    assert not missing, (
        'target BDD is missing the variables:\n'
        '{missing}\n'
        'known variables in target are:\n'
        '{target.vars}\n').format(
            missing=missing,
            target=target)
    # same indices ?
    for var in supp:
        i = source._index_of_var[var]
        j = target._index_of_var[var]
        assert i == j, (var, i, j)
    r = Cudd_bddTransfer(source.manager, target.manager, u.node)
    f = Function()
    f.init(target.manager, r)
    logger.debug('-- done transferring bdd')
    return f


cpdef count_nodes(functions):
    """Return total nodes used by `functions`.

    Sharing is taken into account.

    @type functions: `list` of `Function`
    @rtype: int
    """
    cdef DdNode **x
    cdef Function f
    n = len(functions)
    x = <DdNode **> PyMem_Malloc(n *sizeof(DdNode *))
    for i, f in enumerate(functions):
        x[i] = f.node
    try:
        k = Cudd_SharingSize(x, n)
    finally:
        PyMem_Free(x)
    return k


cpdef count_nodes_per_level(BDD bdd):
    """Return `dict` that maps each var to a node count."""
    d = dict()
    for var in bdd.vars:
        level = bdd.level_of_var(var)
        n = bdd.manager.subtables[level].keys
        d[var] = n
    return d


def dump(u, file_name, BDD bdd):
    """Pickle variable order and dump dddmp file."""
    assert u in bdd, u
    pickle_fname = '{s}.pickle'.format(s=file_name)
    dddmp_fname = '{s}.dddmp'.format(s=file_name)
    order = {var: bdd.level_of_var(var)
             for var in bdd.vars}
    d = dict(variable_order=order)
    with open(pickle_fname, 'wb') as f:
        pickle.dump(d, f, protocol=2)
    bdd.dump(u, dddmp_fname)


def load(file_name, BDD bdd, reordering=False):
    """Unpickle variable order and load dddmp file.

    Loads the variable order,
    reorders `bdd` to match that order,
    turns off reordering,
    then loads the BDD,
    restores reordering.
    Assumes that:

      - `file_name` has no extension
      - pickle file name: `file_name.pickle`
      - dddmp file name: `file_name.dddmp`

    @param reordering: if `True`,
        then enable reordering during DDDMP load.
    """
    t0 = time.time()
    pickle_fname = '{s}.pickle'.format(s=file_name)
    dddmp_fname = '{s}.dddmp'.format(s=file_name)
    with open(pickle_fname, 'rb') as f:
        d = pickle.load(f)
    order = d['variable_order']
    for var in order:
        bdd.add_var(var)
    reorder(bdd, order)
    cfg = bdd.configure(reordering=False)
    u = bdd.load(dddmp_fname)
    bdd.configure(reordering=cfg['reordering'])
    t1 = time.time()
    dt = t1 - t0
    logger.info('BDD load time from file: {dt}'.format(dt=dt))
    return u


cdef _dict_to_cube_array(d, int *x, dict index_of_var):
    """Assign array of literals `x` from assignment `d`.

    @param x: array of literals
        0: negated, 1: positive, 2: don't care
        see `Cudd_FirstCube`
    @param index_of_var: `dict` from variables to `bool`
        or `set` of variable names.
    """
    for var, j in index_of_var.iteritems():
        if var not in d:
            x[j] = 2
            continue
        # var in `d`
        if isinstance(d, dict):
            b = d[var]
        else:
            b = True
        if b is False:
            x[j] = 0
        elif b is True:
            x[j] = 1
        else:
            raise ValueError(
                'unknown value: {b}'.format(b=b))


cdef dict _cube_array_to_dict(int *x, dict index_of_var):
    """Return assignment from array of literals `x`.

    @param x: see `_dict_to_cube_array`
    """
    d = dict()
    for var, j in index_of_var.iteritems():
        b = x[j]
        if b == 2:
            continue
        elif b == 1:
            d[var] = True
        elif b == 0:
            d[var] = False
        else:
            raise Exception(
                'unknown polarity: {b}, '
                'for variable "{var}"'.format(
                    b=b, var=var))
    return d


cdef class Function(object):
    """Wrapper of `DdNode` from CUDD.

    Attributes:

      - `index`
      - `ref`
      - `low`
      - `high`
      - `negated`

    In Python, use as:
    ```
    bdd = BDD()
    u = bdd.true
    v = bdd.false
    w = u | ~ v

    In Cython, use as:

    ```
    bdd = BDD()
    cdef DdNode *u
    u = Cudd_ReadOne(bdd.manager)
    f = Function()
    f.init(bdd.manager, u)
    ```
    """

    cdef object __weakref__
    cpdef DdManager *manager
    cpdef DdNode *node

    cdef init(self, DdManager *mgr, DdNode *u):
        assert u != NULL, '`DdNode *u` is `NULL` pointer.'
        self.manager = mgr
        self.node = u
        Cudd_Ref(u)

    @property
    def index(self):
        """Index of `self.node`."""
        cdef DdNode *u
        u = Cudd_Regular(self.node)
        index = Cudd_NodeReadIndex(self.node)
        return index

    @property
    def level(self):
        """Level where this node currently is."""
        i = self.index
        return Cudd_ReadPerm(self.manager, i)

    @property
    def ref(self):
        """Sum of reference counts of node and its negation."""
        cdef DdNode *u
        u = Cudd_Regular(self.node)
        return u.ref

    @property
    def low(self):
        """Return "else" node as `Function`."""
        cdef DdNode *u
        if Cudd_IsConstant(self.node):
            return None
        u = Cudd_E(self.node)
        f = Function()
        f.init(self.manager, u)
        return f

    @property
    def high(self):
        """Return "then" node as `Function`."""
        cdef DdNode *u
        if Cudd_IsConstant(self.node):
            return None
        u = Cudd_T(self.node)
        f = Function()
        f.init(self.manager, u)
        return f

    @property
    def negated(self):
        """Return `True` if `self` is a complemented edge."""
        return Cudd_IsComplement(self.node)

    def __dealloc__(self):
        Cudd_RecursiveDeref(self.manager, self.node)

    def __int__(self):
        assert sizeof(stdint.uintptr_t) == sizeof(DdNode *)
        i = <stdint.uintptr_t>self.node
        # 0, 1 are true and false in logic syntax
        if 0 <= i:
            i += 2
        return i

    def __repr__(self):
        cdef DdNode *u
        u = Cudd_Regular(self.node)
        return (
            'Function(DdNode with: '
            'var_index={idx}, '
            'ref_count={ref}, '
            '__int__={i})').format(
                idx=u.index,
                ref=u.ref,
                i=int(self))

    def __str__(self):
        return str(int(self))

    def __len__(self):
        return Cudd_DagSize(self.node)

    def __richcmp__(Function self, Function other, op):
        if other is None:
            eq = False
        else:
            # guard against mixing managers
            assert self.manager == other.manager
            eq = (self.node == other.node)
        if op == 2:
            return eq
        elif op == 3:
            return not eq
        else:
            raise Exception('Only `__eq__` and `__ne__` defined.')

    def __invert__(self):
        cdef DdNode *r
        r = Cudd_Not(self.node)
        f = Function()
        f.init(self.manager, r)
        return f

    def __and__(Function self, Function other):
        assert self.manager == other.manager
        r = Cudd_bddAnd(self.manager, self.node, other.node)
        f = Function()
        f.init(self.manager, r)
        return f

    def __or__(Function self, Function other):
        assert self.manager == other.manager
        r = Cudd_bddOr(self.manager, self.node, other.node)
        f = Function()
        f.init(self.manager, r)
        return f


"""Tests and test wrappers for C functions."""


cpdef _test_incref():
    bdd = BDD()
    cdef Function f
    f = bdd.true
    i = f.ref
    bdd.incref(f.node)
    j = f.ref
    assert j == i + 1, (j, i)
    bdd.decref(f.node)  # avoid errors in `BDD.__dealloc__`
    del f


cpdef _test_decref():
    bdd = BDD()
    cdef Function f
    f = bdd.true
    i = f.ref
    assert i == 3, i
    bdd.incref(f.node)
    i = f.ref
    assert i == 4, i
    bdd.decref(f.node)
    j = f.ref
    assert j == i - 1, (j, i)
    del f


cpdef _test_dict_to_cube_array():
    cdef int *x
    n = 3
    x = <int *> PyMem_Malloc(n * sizeof(int))
    index_of_var = dict(x=0, y=1, z=2)
    d = dict(y=True, z=False)
    _dict_to_cube_array(d, x, index_of_var)
    r = [j for j in x[:n]]
    r_ = [2, 1, 0]
    assert r == r_, (r, r_)
    PyMem_Free(x)


cpdef _test_cube_array_to_dict():
    cdef int *x
    n = 3
    x = <int *> PyMem_Malloc(n * sizeof(int))
    x[0] = 2
    x[1] = 1
    x[2] = 0
    index_of_var = dict(x=0, y=1, z=2)
    d = _cube_array_to_dict(x, index_of_var)
    d_ = dict(y=True, z=False)
    assert d == d_, (d, d_)
    PyMem_Free(x)
