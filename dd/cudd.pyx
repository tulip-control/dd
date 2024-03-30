"""Cython interface to CUDD.

Variable `__version__` equals CUDD's version string.


Reference
=========
    Fabio Somenzi
    "CUDD: CU Decision Diagram Package"
    University of Colorado at Boulder
    v2.5.1, 2015
    <http://vlsi.colorado.edu/~fabio/>
"""
# Copyright 2015 by California Institute of Technology
# All rights reserved. Licensed under BSD-3.
#
import collections.abc as _abc
import logging
import pickle
import pprint
import sys
import textwrap as _tw
import time
import typing as _ty
import warnings

from cpython cimport bool as python_bool
from cpython.mem cimport PyMem_Malloc, PyMem_Free
cimport libc.stdint as stdint
from libc.stdio cimport FILE, fdopen, fopen, fclose
from libcpp cimport bool

import dd._abc as _dd_abc
from dd import _copy
from dd import _parser
from dd import _utils
from dd import autoref
from dd import bdd as _bdd


_Yes: _ty.TypeAlias = python_bool
_Nat: _ty.TypeAlias = _dd_abc.Nat
_Cardinality: _ty.TypeAlias = _dd_abc.Cardinality
_NumberOfBytes: _ty.TypeAlias = _dd_abc.NumberOfBytes
_VariableName: _ty.TypeAlias = _dd_abc.VariableName
_Level: _ty.TypeAlias = _dd_abc.Level
_VariableLevels: _ty.TypeAlias = _dd_abc.VariableLevels
_Assignment: _ty.TypeAlias = _dd_abc.Assignment
_Renaming: _ty.TypeAlias = _dd_abc.Renaming
_Formula: _ty.TypeAlias = _dd_abc.Formula
_BDDFileType: _ty.TypeAlias = (
    _dd_abc.BDDFileType |
    _ty.Literal['dddmp'])


cdef extern from 'mtr.h':
    struct MtrNode_:
        pass
    ctypedef MtrNode_ MtrNode
cdef MTR_DEFAULT = 0
cdef MTR_FIXED = 4
cdef extern from 'cuddInt.h':
    char* CUDD_VERSION
    int CUDD_CONST_INDEX
    # subtable (for a level)
    struct DdSubtable:
        unsigned int slots
        unsigned int keys
    # manager
    struct DdManager:
        DdSubtable *subtables
        unsigned int keys
        unsigned int dead
        double cachecollisions
        double cacheinserts
        double cachedeletions
    DdNode *cuddUniqueInter(
        DdManager *unique,
        int index,
        DdNode *T, DdNode *E)
cdef extern from 'cudd.h':
    # node
    ctypedef unsigned int DdHalfWord
    struct DdNode:
        DdHalfWord index
        DdHalfWord ref
    ctypedef DdNode DdNode

    ctypedef DdManager DdManager
    DdManager *Cudd_Init(
        unsigned int numVars,
        unsigned int numVarsZ,
        unsigned int numSlots,
        unsigned int cacheSize,
        size_t maxMemory)
    struct DdGen
    ctypedef enum Cudd_ReorderingType:
        pass
    # node elements
    DdNode *Cudd_bddNewVar(
        DdManager *dd)
    DdNode *Cudd_bddNewVarAtLevel(
        DdManager *dd, int level)
    DdNode *Cudd_bddIthVar(
        DdManager *dd, int index)
    DdNode *Cudd_ReadLogicZero(
        DdManager *dd)
    DdNode *Cudd_ReadOne(
        DdManager *dd)
    DdNode *Cudd_Regular(
        DdNode *u)
    bool Cudd_IsConstant(
        DdNode *u)
    unsigned int Cudd_NodeReadIndex(
        DdNode *u)
    DdNode *Cudd_T(
        DdNode *u)
    DdNode *Cudd_E(
        DdNode *u)
    bool Cudd_IsComplement(
        DdNode *u)
    int Cudd_DagSize(
        DdNode *node)
    int Cudd_SharingSize(
        DdNode **nodeArray, int n)
    # basic Boolean operators
    DdNode *Cudd_Not(
        DdNode *dd)
    DdNode *Cudd_bddIte(
        DdManager *dd, DdNode *f,
        DdNode *g, DdNode *h)
    DdNode *Cudd_bddAnd(
        DdManager *dd,
        DdNode *f, DdNode *g)
    DdNode *Cudd_bddOr(
        DdManager *dd,
        DdNode *f, DdNode *g)
    DdNode *Cudd_bddXor(
        DdManager *dd,
        DdNode *f, DdNode *g)
    DdNode *Cudd_bddXnor(
        DdManager *dd,
        DdNode *f, DdNode *g)
    int Cudd_bddLeq(
        DdManager *dd,
        DdNode *f,
        DdNode *g)
    DdNode *Cudd_Support(
        DdManager *dd, DdNode *f)
    DdNode *Cudd_bddComputeCube(
        DdManager *dd,
        DdNode **vars, int *phase, int n)
    DdNode *Cudd_CubeArrayToBdd(
        DdManager *dd, int *array)
    int Cudd_BddToCubeArray(
        DdManager *dd,
        DdNode *cube, int *array)
    int Cudd_PrintMinterm(
        DdManager *dd, DdNode *f)
    DdNode *Cudd_Cofactor(
        DdManager *dd, DdNode *f, DdNode *g)
    DdNode *Cudd_bddCompose(
        DdManager *dd,
        DdNode *f, DdNode *g, int v)
    DdNode *Cudd_bddVectorCompose(
        DdManager *dd,
        DdNode *f, DdNode **vector)
    DdNode *Cudd_bddRestrict(
        DdManager *dd, DdNode *f, DdNode *c)
    # cubes
    DdGen *Cudd_FirstCube(
        DdManager *dd, DdNode *f,
        int **cube, double *value)
    int Cudd_NextCube(
        DdGen *gen, int **cube, double *value)
    int Cudd_IsGenEmpty(
        DdGen *gen)
    int Cudd_GenFree(
        DdGen *gen)
    double Cudd_CountMinterm(
        DdManager *dd, DdNode *f, int nvars)
    # refs
    void Cudd_Ref(
        DdNode *n)
    void Cudd_RecursiveDeref(
        DdManager *table, DdNode *n)
    void Cudd_Deref(
        DdNode *n)
    # checks
    int Cudd_CheckZeroRef(
        DdManager *manager)
    int Cudd_DebugCheck(
        DdManager *table)
    void Cudd_Quit(
        DdManager *unique)
    DdNode *Cudd_bddTransfer(
        DdManager *ddSource,
        DdManager *ddDestination,
        DdNode *f)
    # info
    int Cudd_PrintInfo(
        DdManager *dd, FILE *fp)
    int Cudd_ReadSize(
        DdManager *dd)
    long Cudd_ReadNodeCount(
        DdManager *dd)
    long Cudd_ReadPeakNodeCount(
        DdManager *dd)
    int Cudd_ReadPeakLiveNodeCount(
        DdManager *dd)
    size_t Cudd_ReadMemoryInUse(
        DdManager *dd)
    unsigned int Cudd_ReadSlots(
        DdManager *dd)
    double Cudd_ReadUsedSlots(
        DdManager *dd)
    double Cudd_ExpectedUsedSlots(
        DdManager *dd)
    unsigned int Cudd_ReadCacheSlots(
        DdManager *dd)
    double Cudd_ReadCacheUsedSlots(
        DdManager *dd)
    double Cudd_ReadCacheLookUps(
        DdManager *dd)
    double Cudd_ReadCacheHits(
        DdManager *dd)
    # reordering
    int Cudd_ReduceHeap(
        DdManager *table,
        Cudd_ReorderingType heuristic,
        int minsize)
    int Cudd_ShuffleHeap(
        DdManager *table, int *permutation)
    void Cudd_AutodynEnable(
        DdManager *unique,
        Cudd_ReorderingType method)
    void Cudd_AutodynDisable(
        DdManager *unique)
    int Cudd_ReorderingStatus(
        DdManager *unique,
        Cudd_ReorderingType *method)
    unsigned int Cudd_ReadReorderings(
        DdManager *dd)
    long Cudd_ReadReorderingTime(
        DdManager *dd)
    int Cudd_ReadPerm(
        DdManager *dd, int index)
    int Cudd_ReadInvPerm(
        DdManager *dd, int level)
    void Cudd_SetSiftMaxSwap(
        DdManager *dd, int sms)
    int Cudd_ReadSiftMaxSwap(
        DdManager *dd)
    void Cudd_SetSiftMaxVar(
        DdManager *dd, int smv)
    int Cudd_ReadSiftMaxVar(
        DdManager *dd)
    # variable grouping
    extern MtrNode *Cudd_MakeTreeNode(
        DdManager *dd, unsigned int low,
        unsigned int size, unsigned int type)
    extern MtrNode *Cudd_ReadTree(
        DdManager *dd)
    extern void Cudd_SetTree(
        DdManager *dd, MtrNode *tree)
    extern void Cudd_FreeTree(
        DdManager *dd)
    # manager config
    size_t Cudd_ReadMaxMemory(
        DdManager *dd)
    size_t Cudd_SetMaxMemory(
        DdManager *dd,
        size_t maxMemory)
    unsigned int Cudd_ReadMaxCacheHard(
        DdManager *dd)
    unsigned int Cudd_ReadMaxCache(
        DdManager *dd)
    void Cudd_SetMaxCacheHard(
        DdManager *dd, unsigned int mc)
    double Cudd_ReadMaxGrowth(
        DdManager *dd)
    void Cudd_SetMaxGrowth(
        DdManager *dd, double mg)
    unsigned int Cudd_ReadMinHit(
        DdManager *dd)
    void Cudd_SetMinHit(
        DdManager *dd, unsigned int hr)
    void Cudd_EnableGarbageCollection(
        DdManager *dd)
    void Cudd_DisableGarbageCollection(
        DdManager *dd)
    int Cudd_GarbageCollectionEnabled(
        DdManager * dd)
    unsigned int Cudd_ReadLooseUpTo(
        DdManager *dd)
    void Cudd_SetLooseUpTo(
        DdManager *dd, unsigned int lut)
    # quantification
    DdNode *Cudd_bddExistAbstract(
        DdManager *manager,
        DdNode *f,
        DdNode *cube)
    DdNode *Cudd_bddUnivAbstract(
        DdManager *manager,
        DdNode *f,
        DdNode *cube)
    DdNode *Cudd_bddAndAbstract(
        DdManager *manager,
        DdNode *f, DdNode *g,
        DdNode *cube)
    DdNode *Cudd_bddSwapVariables(
        DdManager *dd,
        DdNode *f, DdNode **x, DdNode **y,
        int n)
cdef extern from '_cudd_addendum.c':
    DdNode *Cudd_bddTransferRename(
        DdManager *ddSource,
        DdManager *ddDestination,
        DdNode *f, int *renaming)
ctypedef DdNode *DdRef
cdef CUDD_UNIQUE_SLOTS = 2**8
cdef CUDD_CACHE_SLOTS = 2**18
cdef CUDD_REORDER_GROUP_SIFT = 14
cdef CUDD_OUT_OF_MEM = -1
cdef MAX_CACHE = <unsigned int> - 1  # entries
__version__ = CUDD_VERSION.decode('utf-8')


# TODO: replace DDDMP
cdef extern from 'dddmp.h':
    ctypedef enum Dddmp_VarInfoType:
        pass
    ctypedef enum Dddmp_VarMatchType:
        pass
    int Dddmp_cuddBddStore(
        DdManager *ddMgr,
        char *ddname,
        DdNode *f,
        char **varnames,
        int *auxids,
        int mode,
        Dddmp_VarInfoType varinfo,
        char *fname,
        FILE *fp)
    DdNode *Dddmp_cuddBddLoad(
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


# 2**30 = 1 GiB (gibibyte, read ISO/IEC 80000)
DEFAULT_MEMORY = 1 * 2**30
logger = logging.getLogger(__name__)


cdef class BDD:
    """Wrapper of CUDD manager.

    Interface similar to `dd.bdd.BDD`.
    Variable names are strings.
    Attributes:

      - `vars`: `set` of bit names as `str`ings
    """

    cdef DdManager *manager
    cdef public object vars
    cdef public object _index_of_var
    cdef public object _var_with_index

    def __cinit__(
            self,
            memory_estimate:
                _NumberOfBytes |
                None=None,
            initial_cache_size:
                _Cardinality |
                None=None,
            *arg,
            **kw
            ) -> None:
        """Initialize BDD manager.

        @param memory_estimate:
            maximum allowed memory, in bytes.
        """
        self.manager = NULL  # prepare for
            # `__dealloc__`,
            # in case an exception is raised below.
            # Including `*arg, **kw` in the
            # signature of the method `__cinit__`
            # aims to prevent an exception from
            # being raised upon instantiation
            # of the class `BDD` before the
            # body of the method `__cinit__`
            # is entered.
            # In that case, `self.manager`
            # could in principle have an
            # arbitrary value when `__dealloc__`
            # is executed.
        total_memory = _utils.total_memory()
        default_memory = DEFAULT_MEMORY
        if memory_estimate is None:
            memory_estimate = default_memory
        if total_memory is None:
            pass
        elif memory_estimate >= total_memory:
            msg = (
                'Error in `dd.cudd`: '
                'total physical memory '
                f'is {total_memory} bytes, '
                f'but requested {memory_estimate} bytes. '
                'Please pass an amount of memory to '
                'the `BDD` constructor to avoid this error. '
                'For example, by instantiating '
                'the `BDD` manager as '
                f'`BDD({round(total_memory / 2)})`.')
            # The motivation of both printing and
            # raising an exception was that Cython
            # failed with a segmentation fault,
            # without showing the exception message.
            print(msg)
            raise ValueError(msg)
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
        if mgr is NULL:
            raise RuntimeError(
                'failed to initialize CUDD DdManager')
        self.manager = mgr

    def __init__(
            self,
            memory_estimate:
                _NumberOfBytes |
                None=None,
            initial_cache_size:
                _Cardinality |
                None=None
            ) -> None:
        logger.info(f'Using CUDD v{__version__}')
        self.configure(
            reordering=True,
            max_cache_hard=MAX_CACHE)
        self.vars = set()
        # map: str -> unique fixed int
        self._index_of_var = dict()
        self._var_with_index = dict()

    def __dealloc__(
            self
            ) -> None:
        if self.manager is NULL:
            raise RuntimeError(
                '`self.manager` is `NULL`, '
                'which suggests that '
                'an exception was raised '
                'inside the method '
                '`dd.cudd.BDD.__cinit__`.')
        n = Cudd_CheckZeroRef(self.manager)
        if n != 0:
            raise AssertionError(
                f'Still {n} nodes '
                'referenced upon shutdown.')
        # Exceptions raised inside `__dealloc__` will be
        # ignored. So if the `AssertionError` above is
        # raised, then Python will continue execution
        # without calling `Cudd_Quit`.
        #
        # Even though this can cause a memory leak,
        # incorrect reference counts imply that there
        # already is some issue, and that calling
        # `Cudd_Quit` might be unsafe.
        Cudd_Quit(self.manager)

    def __eq__(
            self:
                BDD,
            other:
                _ty.Optional[BDD]
            ) -> _Yes:
        """Return `True` if `other` has same manager."""
        if other is None:
            return False
        return self.manager == other.manager

    def __ne__(
            self:
                BDD,
            other:
                _ty.Optional[BDD]
            ) -> _Yes:
        if other is None:
            return True
        return self.manager != other.manager

    def __len__(
            self
            ) -> _Cardinality:
        """Number of nodes with nonzero references."""
        return Cudd_CheckZeroRef(self.manager)

    def __contains__(
            self,
            u:
                Function
            ) -> _Yes:
        if u.manager != self.manager:
            raise ValueError(
                'undefined containment, because '
                '`u.manager != self.manager`')
        try:
            Cudd_NodeReadIndex(u.node)
            return True
        except:
            return False

    def __str__(
            self
            ) -> str:
        d = self.statistics()
        s = (
            'Binary decision diagram '
                '(CUDD wrapper) with:\n'
            '\t {n} live nodes now\n'
            '\t {peak} live nodes at peak\n'
            '\t {n_vars} BDD variables\n'
            '\t {mem:10.1f} bytes in use\n'
            '\t {reorder_time:10.1f} sec '
                'spent reordering\n'
            '\t {n_reorderings} reorderings\n'
            ).format(
                n=d['n_nodes'],
                peak=d['peak_live_nodes'],
                n_vars=d['n_vars'],
                reorder_time=d['reordering_time'],
                n_reorderings=d['n_reorderings'],
                mem=d['mem'])
        return s

    def statistics(
            self:
                BDD,
            exact_node_count:
                _Yes=False
            ) -> dict[
                str,
                _ty.Any]:
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

          - `mem`: bytes in use
          - `unique_size`: total number of
            buckets in unique table
          - `unique_used_fraction`: buckets that
            contain >= 1 node
          - `expected_unique_used_fraction`:
            if properly working

          - `cache_size`: number of slots in cache
          - `cache_used_fraction`: slots with data
          - `cache_lookups`: total number of lookups
          - `cache_hits`: total number of cache hits
          - `cache_insertions`
          - `cache_collisions`
          - `cache_deletions`
        """
        warnings.warn(
            "Changed in `dd` version 0.5.7: "
            "In the `dict` returned by the method "
            "`dd.cudd.BDD.statistics`, "
            "the value of the key `'mem'` "
            "has changed to bytes (from 10**6 bytes).",
            UserWarning)
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
        mem = float(m)
        # unique table
        unique_size = Cudd_ReadSlots(mgr)
        unique_used_fraction = Cudd_ReadUsedSlots(mgr)
        expected_unique_fraction = (
            Cudd_ExpectedUsedSlots(mgr))
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
            expected_unique_used_fraction=
                expected_unique_fraction,
            cache_size=cache_size,
            cache_used_fraction=cache_used_fraction,
            cache_lookups=cache_lookups,
            cache_hits=cache_hits,
            cache_insertions=cache_insertions,
            cache_collisions=cache_collisions,
            cache_deletions=cache_deletions)
        return d

    def configure(
            self:
                BDD,
            **kw
            ) -> dict[
                str,
                _ty.Any]:
        """Read and apply parameter values.

        First read (returned), then apply `kw`.
        Available keyword arguments:

          - `'reordering'`:
                if `True` then enable,
                else disable
          - `'garbage_collection'`:
                if `True` then enable,
                else disable
          - `'max_memory'`: in bytes
          - `'loose_up_to'`:
                unique table fast growth
                upper bound
          - `'max_cache_hard'`:
                cache entries upper bound
          - `'min_hit'`:
                hit ratio for resizing cache
          - `'max_growth'`:
                intermediate growth
                during sifting
          - `'max_swaps'`:
                no more level swaps
                in one sifting
          - `'max_vars'`:
                no more variables moved
                in one sifting

        For more details, read `cuddAPI.c`.
        Example usage:

        ```python
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
        garbage_collection = (
            Cudd_GarbageCollectionEnabled(mgr))
        max_memory = Cudd_ReadMaxMemory(mgr)
        loose_up_to = Cudd_ReadLooseUpTo(mgr)
        max_cache_soft = Cudd_ReadMaxCache(mgr)
        max_cache_hard = Cudd_ReadMaxCacheHard(mgr)
        min_hit = Cudd_ReadMinHit(mgr)
        max_growth = Cudd_ReadMaxGrowth(mgr)
        max_swaps = Cudd_ReadSiftMaxSwap(mgr)
        max_vars = Cudd_ReadSiftMaxVar(mgr)
        d = dict(
            reordering=True if reordering == 1
                else False,
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
                    Cudd_AutodynEnable(
                        mgr, CUDD_REORDER_GROUP_SIFT)
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
                logger.warning(
                    '"max_cache_soft" not settable.')
            else:
                raise ValueError(
                    f'Unknown parameter "{k}"')
        return d

    cpdef tuple succ(
            self,
            u:
                Function):
        """Return `(level, low, high)` for `u`."""
        if u.manager != self.manager:
            raise ValueError(
                '`u.manager != self.manager`')
        i = u.level
        v = u.low
        w = u.high
        return i, v, w

    cpdef incref(
            self,
            u:
                Function):
        """Increment the reference count of `u`.

        Raise `RuntimeError` if `u._ref <= 0`.
        For more details about avoiding this
        read the docstring of the class `Function`.

        The reference count of the BDD node in CUDD
        that `u` points to is incremented.

        Also, the attribute `u._ref` is incremented.

        Calling this method is unnecessary,
        because reference counting is automated.
        """
        if u.node is NULL:
            raise RuntimeError(
                '`u.node` is `NULL` pointer.')
        if u._ref <= 0:
            _utils.raise_runtimerror_about_ref_count(
                u._ref, 'method `dd.cudd.BDD.incref`',
                '`dd.cudd.Function`')
        assert u._ref > 0, u._ref
        u._ref += 1
        self._incref(u.node)

    cpdef decref(
            self,
            u:
                Function,
            recursive:
                _Yes=False,
            _direct:
                _Yes=False):
        """Decrement the reference count of `u`.

        Raise `RuntimeError` if `u._ref <= 0`
        or `u.node is NULL`.
        For more details about avoiding this
        read the docstring of the class `Function`.

        The reference count of the BDD node in CUDD
        that `u` points to is decremented.

        Also, the attribute `u._ref` is decremented.
        If after this decrement, `u._ref == 0`,
        then the pointer `u.node` is set to `NULL`.

        Calling this method is unnecessary,
        because reference counting is automated.

        If early dereferencing of the node is desired
        in order to allow garbage collection,
        then write `del u`, instead of calling
        this method.

        @param recursive:
            if `True`, then call
            `Cudd_RecursiveDeref`,
            else call `Cudd_Deref`
        @param _direct:
            use this parameter only after
            reading the source code of the
            Cython file `dd/cudd.pyx`.
            When `_direct == True`, some of the above
            description does not apply.
        """
        if u.node is NULL:
            raise RuntimeError(
                '`u.node` is `NULL` pointer.')
        # bypass checks and leave `u._ref` unchanged,
        # directly call `_decref`
        if _direct:
            self._decref(u.node, recursive)
            return
        if u._ref <= 0:
            _utils.raise_runtimerror_about_ref_count(
                u._ref, 'method `dd.cudd.BDD.decref`',
                '`dd.cudd.Function`')
        assert u._ref > 0, u._ref
        u._ref -= 1
        self._decref(u.node, recursive)
        if u._ref == 0:
            u.node = NULL

    cdef _incref(
            self,
            u:
                DdRef):
        Cudd_Ref(u)

    cdef _decref(
            self,
            u:
                DdRef,
            recursive:
                _Yes=False):
        # There is little point in checking here
        # the reference count of `u`, because
        # doing that relies on the assumption
        # that `u` still corresponds to a node,
        # which implies that the reference count
        # is positive.
        #
        # This point should not be reachable
        # after `u` reaches zero reference count.
        #
        # Moreover, if the memory has been deallocated,
        # then in principle the attribute `ref`
        # can have any value, so an assertion here
        # would not be ensuring correctness.
        if recursive:
            Cudd_RecursiveDeref(self.manager, u)
        else:
            Cudd_Deref(u)

    def declare(
            self,
            *variables:
                _VariableName
            ) -> None:
        """Add names in `variables` to `self.vars`."""
        for var in variables:
            self.add_var(var)

    cpdef int add_var(
            self,
            var:
                _VariableName,
            index:
                _Nat |
                None=None):
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
            if index is not None and j != index:
                raise AssertionError(j, index)
            return j
        # new var
        if index is None:
            j = len(self._index_of_var)
        else:
            j = index
        u = Cudd_bddIthVar(self.manager, j)
        if u is NULL:
            raise RuntimeError(
                f'failed to add var "{var}"')
        self._add_var(var, j)
        return j

    cpdef int insert_var(
            self,
            var:
                _VariableName,
            level:
                _Level):
        """Create new variable at `level`.

        The name of the variable is
        the string `var`.

        @param var:
            name of variable
            that this function
            will declare
        @param level:
            where the new
            variable will be placed
            in the variable order
            of this BDD manager
        @return:
            number that CUDD
            uses to identify the
            newly created variable.
            This number is also
            called an index of
            the variable.
        @rtype:
            `int` >= 0
        """
        r: DdRef
        r = Cudd_bddNewVarAtLevel(
            self.manager, level)
        if r is NULL:
            raise RuntimeError(
                f'failed to create var "{var}"')
        j = r.index
        self._add_var(var, j)
        return j

    cdef _add_var(
            self,
            var:
                _VariableName,
            index:
                _Nat):
        """Declare new variable `var`.

        Adds to `self` a *new* variable
        named `var`, identified within
        CUDD by the number `index`.

        @param var:
            name of variable that
            this function will declare
        @param index:
            number that
            will identify within CUDD
            the newly created variable
        """
        if var in self.vars:
            raise ValueError(
                f'existing variable: "{var}"')
        if var in self._index_of_var:
            raise ValueError(
                'variable already has index: {i}'.format(
                    i=self._index_of_var[var]))
        if index in self._var_with_index:
            raise ValueError((
                'index already corresponds '
                'to a variable: {v}').format(
                    v=self._var_with_index[index]))
        self.vars.add(var)
        self._index_of_var[var] = index
        self._var_with_index[index] = var
        if (len(self._index_of_var) !=
                len(self._var_with_index)):
            raise AssertionError(
                'the attributes '
                '`_index_of_var` and '
                '`_var_with_index` '
                'have different length')

    cpdef Function var(
            self,
            var:
                _VariableName):
        """Return node for variable named `var`."""
        if var not in self._index_of_var:
            raise ValueError(
                f'undeclared variable "{var}", '
                'the declared variables are:\n'
                f'{self._index_of_var}')
        j = self._index_of_var[var]
        r = Cudd_bddIthVar(self.manager, j)
        return wrap(self, r)

    def var_at_level(
            self,
            level:
                _Level
            ) -> _VariableName:
        """Return name of variable at `level`.

        Raise `ValueError` if `level` is not
        the level of any variable declared in
        `self.vars`.
        """
        j = Cudd_ReadInvPerm(self.manager, level)
        if (j == -1 or j == CUDD_CONST_INDEX or
                j not in self._var_with_index):
            raise ValueError(_tw.dedent(f'''
                No declared variable has level: {level}.
                {_utils.var_counts(self)}
                '''))
        var = self._var_with_index[j]
        return var

    def level_of_var(
            self,
            var:
                _VariableName
            ) -> _Level:
        """Return level of variable named `var`.

        Raise `ValueError` if `var` is not
        a variable in `self.vars`.
        """
        if var not in self._index_of_var:
            raise ValueError(
                f'undeclared variable "{var}", '
                'the declared variables are:\n'
                f'{self._index_of_var}')
        j = self._index_of_var[var]
        level = Cudd_ReadPerm(self.manager, j)
        if level == -1:
            raise AssertionError(
                f'index {j} out of bounds')
        return level

    @property
    def var_levels(
            self
            ) -> _VariableLevels:
        return {
            var: self.level_of_var(var)
            for var in self.vars}

    def _number_of_cudd_vars(
            self
            ) -> _Cardinality:
        """Return number of CUDD indices.

        Can be `> len(self.vars)`.
        """
        n_cudd_vars = Cudd_ReadSize(self.manager)
        if 0 <= n_cudd_vars <= CUDD_CONST_INDEX:
            return n_cudd_vars
        raise RuntimeError(_tw.dedent(f'''
            Unexpected value: {n_cudd_vars}
            returned from `Cudd_ReadSize()`
            (expected <= {CUDD_CONST_INDEX} =
             CUDD_CONST_INDEX)
            '''))

    def reorder(
            self,
            var_order:
                _VariableLevels |
                None=None
            ) -> None:
        """Reorder variables to `var_order`.

        If `var_order` is `None`,
        then invoke sifting.
        """
        reorder(self, var_order)

    cpdef set support(
            self,
            u:
                Function):
        """Return variables that `u` depends on.

        @return:
            set of variable names
        @rtype:
            `set[str]`
        """
        if self.manager != u.manager:
            raise ValueError(
                '`u.manager != self.manager`')
        r: DdRef
        r = Cudd_Support(self.manager, u.node)
        cube = wrap(self, r)
        support = self._cube_to_dict(cube)
        # constant ?
        if not support:
            return set()
        # must be positive unate
        for value in support.values():
            if value is True:
                continue
            raise AssertionError(support)
        return set(support)

    def group(
            self,
            vrs:
                _abc.Mapping[
                    _VariableName,
                    _Nat]
            ) -> None:
        r"""Couple adjacent variables.

        The variables in `vrs` must be at
        levels that form a contiguous
        range.

        ```tla
        ASSUME
            \A value \in vrs.values():
                value >= 2
        ```
        """
        cdef unsigned int group_low
        cdef unsigned int group_size
        for var, group_size in vrs.items():
            if group_size <= 1:
                raise ValueError(
                    'singleton as group '
                    'has no effect')
            group_low = self._index_of_var[var]
            Cudd_MakeTreeNode(
                self.manager, group_low,
                group_size, MTR_DEFAULT)

    def copy(
            self,
            u:
                Function,
            other:
                'BDD' |
                autoref.BDD
            ) -> (
                Function |
                autoref.Function):
        """Transfer BDD with root `u` to `other`."""
        if isinstance(other, BDD):
            return copy_bdd(u, other)
        else:
            return _copy.copy_bdd(u, other)

    cpdef Function let(
            self,
            definitions:
                _Renaming |
                _Assignment |
                dict[_VariableName, Function],
            u:
                Function):
        r"""Substitute variables.

        Variables can be substituted with:
        - other variables (by name)
        - Boolean constant values
          (given as Python `bool` values)
        - binary decision diagrams
          (given as `Function` instances)

        Variables that are to be substituted
        are identified by their names,
        as keys of the argument `definitions`,
        which is a `dict`.

        Multiple variables can be substituted
        at once. This means that variables
        can be swapped too.

        The name of this function originates
        from TLA+ and languages with
        "let" expressions. A "let" expression
        in TLA+ takes the following form:

        ```tla
        LET x == TRUE
        IN x /\ y
        ```

        In a context where `y` can take
        only the values `FALSE` and `TRUE`,
        the above `LET` expression
        is equivalent to the expression `y`.

        In comparison, the expression:

        ```tla
        LET x == FALSE
        IN x /\ y
        ```

        is equivalent to `FALSE`.
        """
        if not definitions:
            logger.warning(
                'Call to `BDD.let` with no effect: '
                '`defs` is empty.')
            return u
        var = next(iter(definitions))
        value = definitions[var]
        if isinstance(value, python_bool):
            return self._cofactor(u, definitions)
        elif isinstance(value, Function):
            return self._compose(u, definitions)
        try:
            value + 's'
        except TypeError:
            raise ValueError(
                'Value must be variable '
                'name as `str`, '
                'or Boolean value as `bool`, '
                'or BDD node as `int`. '
                f'Got: {value}')
        return self._rename(u, definitions)

    cpdef Function _compose(
            self,
            f:
                Function,
            var_sub:
                dict):
        """Return the composition f|_(var = g).

        @param var_sub:
            maps variable names to nodes.
        """
        n = len(var_sub)
        if n == 0:
            logger.warning(
                'call without any effect')
            return f
        if n > 1:
            return self._multi_compose(f, var_sub)
        if n != 1:
            raise ValueError(n)
        var, g = next(iter(var_sub.items()))
        return self._unary_compose(f, var, g)

    cdef Function _unary_compose(
            self,
            f:
                Function,
            var:
                _VariableName,
            g:
                Function):
        """Return single composition."""
        if f.manager != self.manager:
            raise ValueError(
                '`f.manager != self.manager`')
        if g.manager != self.manager:
            raise ValueError(
                '`g.manager != self.manager`')
        r: DdRef
        index = self._index_of_var[var]
        r = Cudd_bddCompose(
            self.manager, f.node, g.node, index)
        if r is NULL:
            raise RuntimeError('compose failed')
        return wrap(self, r)

    cdef Function _multi_compose(
            self,
            f:
                Function,
            var_sub:
                dict[
                    _VariableName,
                    Function]):
        """Return vector composition."""
        if f.manager != self.manager:
            raise ValueError(
                '`f.manager != self.manager`')
        r: DdRef
        cdef DdRef *x
        g: Function
        n_cudd_vars = self._number_of_cudd_vars()
        if n_cudd_vars <= 0:
            raise AssertionError(n_cudd_vars)
        x = <DdRef *> PyMem_Malloc(
            n_cudd_vars *sizeof(DdRef))
        for var in self.vars:
            j = self._index_of_var[var]
            if var in var_sub:
                # substitute
                g = var_sub[var]
                if g.manager != self.manager:
                    raise ValueError((var, g))
                x[j] = g.node
            else:
                # leave var same
                x[j] = Cudd_bddIthVar(
                    self.manager, j)
        try:
            r = Cudd_bddVectorCompose(
                self.manager, f.node, x)
        finally:
            PyMem_Free(x)
        return wrap(self, r)

    cpdef Function _cofactor(
            self,
            f:
                Function,
            values:
                _Assignment):
        """Substitute Booleans for variables.

        @param values:
            maps variable names to Boolean constants
        @return:
            result of substitution
        @rtype:
            `Function`
        """
        if self.manager != f.manager:
            raise ValueError(f)
        r: DdRef
        cube: Function
        cube = self.cube(values)
        r = Cudd_Cofactor(
            self.manager, f.node, cube.node)
        if r is NULL:
            raise RuntimeError(
                'cofactor failed')
        return wrap(self, r)

    cpdef Function _rename(
            self,
            u:
                Function,
            dvars:
                dict[
                    _VariableName,
                    _VariableName]):
        """Return node `u` after renaming variables.

        How to rename the variable is defined
        in the argument `dvars`,
        which is a `dict`.

        The argument value `dvars = dict(x='y')`
        results in variable `'x'` substituted by
        variable `'y'`.

        The argument value
        `dvars = dict(x='y', y='x')` results in
        simultaneous substitution of variable
        `'x'` by variable `'y'`
        and of variable `'y'` by variable `'x'`.
        """
        rename = {
            k: self.var(v)
            for k, v in dvars.items()}
        return self._compose(u, rename)

    cpdef Function _swap(
            self,
            u:
                Function,
            dvars:
                dict[
                    _VariableName,
                    _VariableName]):
        """Return result from swapping variable pairs.

        The variable pairs are defined in
        the argument `dvars`, which is a `dict`.

        Asserts that each variable occurs in
        at most one key-value pair
        of the dictionary `dvars`.

        The argument value `dvars = dict(x='y')`
        results in swapping
        of variables `'x'` and `'y'`,
        which is equivalent to
        simultaneous substitution of
        `'x'` by `'y'` and `'y'` by `'x'`.

        So the argument value
        `dvars = dict(x='y')` has the same
        result as calling `_rename`
        with `dvars = dict(x='y', y='x')`.
        """
        # assert that each variable
        # occurs in at most one
        # key-value pair of the
        # dictionary `dvars`:
        # 1) assert keys and values of
        # `dvars` are disjoint sets
        common = {
            var for var in dvars.values()
            if var in dvars}
        if common:
            raise ValueError(common)
        # 2) assert each value is unique
        values = set(dvars.values())
        if len(dvars) != len(values):
            raise ValueError(dvars)
        #
        # call swapping
        n = len(dvars)
        cdef DdRef *x = <DdRef *> PyMem_Malloc(
            n * sizeof(DdRef))
        cdef DdRef *y = <DdRef *> PyMem_Malloc(
            n * sizeof(DdRef))
        r: DdRef
        cdef DdManager *mgr = u.manager
        f: Function
        for i, xvar in enumerate(dvars):
            yvar = dvars[xvar]
            f = self.var(xvar)
            x[i] = f.node
            f = self.var(yvar)
            y[i] = f.node
        try:
            r = Cudd_bddSwapVariables(
                mgr, u.node, x, y, n)
            if r is NULL:
                raise RuntimeError(
                    'variable swap failed')
        finally:
            PyMem_Free(x)
            PyMem_Free(y)
        return wrap(self, r)

    cpdef Function ite(
            self,
            g:
                Function,
            u:
                Function,
            v:
                Function):
        """Ternary conditional.

        In other words, the root of
        the BDD that represents
        the expression:

        ```tla
        IF g THEN u ELSE v
        ```
        """
        if g.manager != self.manager:
            raise ValueError(
                '`g.manager != self.manager`')
        if u.manager != self.manager:
            raise ValueError(
                '`u.manager != self.manager`')
        if v.manager != self.manager:
            raise ValueError(
                '`v.manager != self.manager`')
        r: DdRef
        r = Cudd_bddIte(
            self.manager,
            g.node, u.node, v.node)
        return wrap(self, r)

    cpdef Function find_or_add(
            self,
            var:
                _VariableName,
            low:
                Function,
            high:
                Function):
        """Return node `IF var THEN high ELSE low`."""
        if low.manager != self.manager:
            raise ValueError(
                '`low.manager != self.manager`')
        if high.manager != self.manager:
            raise ValueError(
                '`high.manager != self.manager`')
        if var not in self.vars:
            raise ValueError(
                f'undeclared variable: {var}, '
                'the declared variables '
                f'are: {self.vars}')
        level = self.level_of_var(var)
        if level >= low.level:
            raise ValueError(
                level, low.level, 'low.level')
        if level >= high.level:
            raise ValueError(
                level, high.level, 'high.level')
        r: DdRef
        index = self._index_of_var[var]
        r = cuddUniqueInter(
            self.manager, index,
            high.node, low.node)
        return wrap(self, r)

    def count(
            self,
            u:
                Function,
            nvars:
                _Cardinality |
                None=None
            ) -> _Cardinality:
        """Return number of models of node `u`.

        @param nvars:
            regard `u` as
            an operator that depends on
            `nvars`-many variables.

            If omitted, then assume
            those variables in `support(u)`.
        """
        if u.manager != self.manager:
            raise ValueError(
                '`u.manager != self.manager`')
        n = len(self.support(u))
        if nvars is None:
            nvars = n
        if nvars < n:
            raise ValueError(nvars, n)
        r = Cudd_CountMinterm(
            self.manager, u.node, nvars)
        if r == CUDD_OUT_OF_MEM:
            raise RuntimeError(
                'CUDD out of memory')
        if r == float('inf'):
            raise RuntimeError(
                'overflow of integer '
                'type double')
        return r

    def pick(
            self,
            u:
                Function,
            care_vars:
                _abc.Set[
                    _VariableName] |
                None=None
            ) -> _Assignment:
        """Return a single assignment.

        @return:
            assignment of values to
            variables
        """
        return next(
            self.pick_iter(u, care_vars),
            None)

    def _pick_iter(
            self,
            u:
                Function,
            care_vars:
                _abc.Set[
                    _VariableName] |
                None=None
            ) -> _abc.Iterable[
                _Assignment]:
        """Return iterator over assignments.

        The returned iterator is generator-based.
        """
        if u.manager != self.manager:
            raise ValueError(
                '`u.manager != self.manager`')
        cdef DdGen *gen
        cdef int *cube
        cdef double value
        support = self.support(u)
        if care_vars is None:
            care_vars = support
        missing = {
            v for v in support
            if v not in care_vars}
        if missing:
            logger.warning(
                'Missing bits:  '
                f'support - care_vars = {missing}')
        config = self.configure(
            reordering=False)
        gen = Cudd_FirstCube(
            self.manager, u.node,
            &cube, &value)
        if gen is NULL:
            raise RuntimeError(
                'first cube failed')
        try:
            r = 1
            while Cudd_IsGenEmpty(gen) == 0:
                if r != 1:
                    raise RuntimeError(
                        'gen not empty but '
                        'no next cube', r)
                d = _cube_array_to_dict(
                    cube, self._index_of_var)
                if not set(d).issubset(support):
                    raise AssertionError(
                        set(d).difference(support))
                for m in _bdd._enumerate_minterms(
                        d, care_vars):
                    yield m
                r = Cudd_NextCube(
                    gen, &cube, &value)
        finally:
            Cudd_GenFree(gen)
        self.configure(
            reordering=config['reordering'])

    def pick_iter(
            self,
            u:
                Function,
            care_vars:
                _abc.Set[
                    _VariableName] |
                None=None
            ) -> _abc.Iterable[
                _Assignment]:
        """Return iterator over assignments.

        The returned iterator is generator-based.
        """
        if self.manager != u.manager:
            raise ValueError(
                '`u.manager != self.manager`')
        support = self.support(u)
        if care_vars is None:
            care_vars = support
        missing = {
            v for v in support
            if v not in care_vars}
        if missing:
            logger.warning(
                'Missing bits:  '
                f'support - care_vars = {missing}')
        cube = dict()
        value = True
        config = self.configure(
            reordering=False)
        for cube in self._sat_iter(
                u, cube, value, support):
            for m in _bdd._enumerate_minterms(
                    cube, care_vars):
                yield m
        self.configure(
            reordering=config['reordering'])

    def _sat_iter(
            self,
            u:
                Function,
            cube:
                _Assignment,
            value:
                python_bool,
            support
            ) -> _abc.Iterable[
                _Assignment]:
        """Recurse to enumerate models."""
        if u.negated:
            value = not value
        # terminal ?
        if u.var is None:
            if value:
                if not set(cube).issubset(support):
                    raise ValueError(set(
                        cube).difference(support))
                yield cube
            return
        # non-terminal
        i, v, w = self.succ(u)
        var = self.var_at_level(i)
        d0 = dict(cube)
        d0[var] = False
        d1 = dict(cube)
        d1[var] = True
        for x in self._sat_iter(
                v, d0, value, support):
            yield x
        for x in self._sat_iter(
                w, d1, value, support):
            yield x

    cpdef Function apply(
            self,
            op:
                _dd_abc.OperatorSymbol,
            u:
                Function,
            v:
                _ty.Optional[Function]
                =None,
            w:
                _ty.Optional[Function]
                =None):
        """Return the result of applying `op`."""
        _utils.assert_operator_arity(op, v, w, 'bdd')
        if self.manager != u.manager:
            raise ValueError(
                '`u.manager != self.manager`')
        if v is not None and self.manager != v.manager:
            raise ValueError(
                '`v.manager != self.manager`')
        if w is not None and self.manager != w.manager:
            raise ValueError(
                '`w.manager != self.manager`')
        r: DdRef
        cdef DdManager *mgr
        mgr = u.manager
        # unary
        r = NULL
        if op in ('~', 'not', '!'):
            r = Cudd_Not(u.node)
        # binary
        elif op in ('and', '/\\', '&', '&&'):
            r = Cudd_bddAnd(mgr, u.node, v.node)
        elif op in ('or', r'\/', '|', '||'):
            r = Cudd_bddOr(mgr, u.node, v.node)
        elif op in ('#', 'xor', '^'):
            r = Cudd_bddXor(mgr, u.node, v.node)
        elif op in ('=>', '->', 'implies'):
            r = Cudd_bddIte(
                mgr, u.node, v.node,
                Cudd_ReadOne(mgr))
        elif op in ('<=>', '<->', 'equiv'):
            r = Cudd_bddXnor(mgr, u.node, v.node)
        elif op in ('diff', '-'):
            r = Cudd_bddIte(
                mgr, u.node, Cudd_Not(v.node),
                Cudd_ReadLogicZero(mgr))
        elif op in (r'\A', 'forall'):
            r = Cudd_bddUnivAbstract(
                mgr, v.node, u.node)
        elif op in (r'\E', 'exists'):
            r = Cudd_bddExistAbstract(
                mgr, v.node, u.node)
        # ternary
        elif op == 'ite':
            r = Cudd_bddIte(
                mgr, u.node, v.node, w.node)
        else:
            raise ValueError(
                f'unknown operator: "{op}"')
        if r is NULL:
            config = self.configure()
            raise RuntimeError((
                'CUDD appears to have '
                'run out of memory.\n'
                'Current settings for '
                'upper bounds are:\n'
                '    max memory = {max_memory} bytes\n'
                '    max cache = {max_cache} entries'
                ).format(
                    max_memory=config['max_memory'],
                    max_cache=config['max_cache_hard']))
        return wrap(self, r)

    cpdef Function _add_int(
            self,
            i:
                int):
        """Return node from `i`.

        Inverse of `Function.__int__()`.
        """
        u: DdRef = _int_to_ddref(i)
        return wrap(self, u)

    cpdef Function cube(
            self,
            dvars:
                _abc.Collection[
                    _VariableName]):
        """Return node for cube over `dvars`."""
        n_cudd_vars = self._number_of_cudd_vars()
        # make cube
        cube: DdRef
        cdef int *x
        x = <int *> PyMem_Malloc(
            n_cudd_vars * sizeof(int))
        _dict_to_cube_array(
            dvars, x, self._index_of_var)
        try:
            cube = Cudd_CubeArrayToBdd(
                self.manager, x)
        finally:
            PyMem_Free(x)
        return wrap(self, cube)

    cdef Function _cube_from_bdds(
            self,
            dvars:
                _abc.Iterable[
                    _VariableName]):
        """Return node for cube over `dvars`.

        Only positive unate cubes implemented for now.
        """
        n = len(dvars)
        # make cube
        cube: DdRef
        cdef DdRef *x
        x = <DdRef *> PyMem_Malloc(
            n * sizeof(DdRef))
        for i, var in enumerate(dvars):
            f = self.var(var)
            x[i] = f.node
        try:
            cube = Cudd_bddComputeCube(
                self.manager, x, NULL, n)
        finally:
            PyMem_Free(x)
        return wrap(self, cube)

    cpdef dict _cube_to_dict(
            self,
            f:
                Function):
        """Collect indices of support variables."""
        if f.manager != self.manager:
            raise ValueError(
                '`f.manager != self.manager`')
        n_cudd_vars = self._number_of_cudd_vars()
        cdef int *x
        x = <int *> PyMem_Malloc(
            n_cudd_vars * sizeof(DdRef))
        try:
            Cudd_BddToCubeArray(
                self.manager, f.node, x)
            d = _cube_array_to_dict(
                x, self._index_of_var)
        finally:
            PyMem_Free(x)
        return d

    cpdef Function quantify(
            self,
            u:
                Function,
            qvars:
                _abc.Iterable[
                    _VariableName],
            forall:
                _Yes=False):
        """Abstract variables `qvars` from node `u`."""
        if u.manager != self.manager:
            raise ValueError(
                '`u.manager != self.manager`')
        cdef DdManager *mgr = u.manager
        c = set(qvars)
        cube = self.cube(c)
        # quantify
        if forall:
            r = Cudd_bddUnivAbstract(
                mgr, u.node, cube.node)
        else:
            r = Cudd_bddExistAbstract(
                mgr, u.node, cube.node)
        return wrap(self, r)

    cpdef Function forall(
            self,
            variables:
                _abc.Iterable[
                    _VariableName],
            u:
                Function):
        """Quantify `variables` in `u` universally.

        Wraps method `quantify` to be more readable.
        """
        return self.quantify(
            u, variables, forall=True)

    cpdef Function exist(
            self,
            variables:
                _abc.Iterable[
                    _VariableName],
            u:
                Function):
        """Quantify `variables` in `u` existentially.

        Wraps method `quantify` to be more readable.
        """
        return self.quantify(
            u, variables, forall=False)

    cpdef assert_consistent(
            self):
        """Raise `AssertionError` if not consistent."""
        if Cudd_DebugCheck(self.manager) != 0:
            raise AssertionError(
                '`Cudd_DebugCheck` errored')
        n = len(self.vars)
        m = len(self._var_with_index)
        k = len(self._index_of_var)
        if n != m:
            raise AssertionError(n, m)
        if m != k:
            raise AssertionError(m, k)

    def add_expr(
            self,
            expr:
                _Formula
            ) -> Function:
        """Return node for expression `e`."""
        return _parser.add_expr(expr, self)

    cpdef str to_expr(
            self,
            u:
                Function):
        """Return a Boolean expression for node `u`."""
        if u.manager != self.manager:
            raise ValueError(
                '`u.manager != self.manager`')
        cache = dict()
        return self._to_expr(u.node, cache)

    cdef str _to_expr(
            self,
            u:
                DdRef,
            cache:
                dict[int, str]):
        if u == Cudd_ReadLogicZero(self.manager):
            return 'FALSE'
        if u == Cudd_ReadOne(self.manager):
            return 'TRUE'
        u_index = _ddref_to_int(u)
        if u_index in cache:
            return cache[u_index]
        v = Cudd_E(u)
        w = Cudd_T(u)
        p = self._to_expr(v, cache)
        q = self._to_expr(w, cache)
        r = Cudd_Regular(u)
        var = self._var_with_index[r.index]
        # pure var ?
        if p == 'FALSE' and q == 'TRUE':
            expr = var
        else:
            expr = f'ite({var}, {q}, {p})'
        # complemented ?
        if Cudd_IsComplement(u):
            expr = f'(~ {expr})'
        cache[u_index] = expr
        return expr

    def dump(
            self,
            filename:
                str,
            roots:
                dict[str, Function] |
                list[Function],
            filetype:
                _BDDFileType |
                None=None
            ) -> None:
        """Write BDDs to `filename`.

        The file type is inferred from the
        extension (case insensitive),
        unless a `filetype` is explicitly given.

        `filetype` can have the values:

        - `'pdf'` for PDF
        - `'png'` for PNG
        - `'svg'` for SVG
        - `'json'` for JSON
        - `'dddmp'` for DDDMP (of CUDD)

        If `filetype is None`, then `filename`
        must have an extension that matches
        one of the file types listed above.

        Dump nodes reachable from `roots`.

        Dumping a JSON file requires that `roots`
        be nonempty.

        Dumping a DDDMP file requires that `roots`
        contain a single node.

        @param roots:
            For JSON: a mapping from
            names to nodes.
        """
        if filetype is None:
            name = filename.lower()
            if name.endswith('.pdf'):
                filetype = 'pdf'
            elif name.endswith('.png'):
                filetype = 'png'
            elif name.endswith('.svg'):
                filetype = 'svg'
            elif name.endswith('.dot'):
                filetype = 'dot'
            elif name.endswith('.p'):
                raise ValueError(
                    'pickling unsupported '
                    'by this class, use JSON')
            elif name.endswith('.json'):
                filetype = 'json'
            elif name.endswith('.dddmp'):
                filetype = 'dddmp'
            else:
                raise ValueError(
                    'cannot infer file type '
                    'from extension of file '
                    f'name "{filename}"')
        if filetype == 'dddmp':
            # single root supported for now
            u, = roots
            self._dump_dddmp(u, filename)
            return
        elif filetype == 'json':
            if roots is None:
                raise ValueError(roots)
            _copy.dump_json(roots, filename)
            return
        elif (filetype != 'pickle' and
                filetype not in _utils.DOT_FILE_TYPES):
            raise ValueError(filetype)
        bdd = autoref.BDD()
        _copy.copy_vars(self, bdd)
            # preserve levels
        if roots is None:
            root_nodes = None
        else:
            cache = dict()
            def mapper(u):
                return _copy.copy_bdd(
                    u, bdd, cache)
            root_nodes = _utils.map_container(
                mapper, roots)
        bdd.dump(
            filename, root_nodes,
            filetype=filetype)

    cpdef _dump_dddmp(
            self,
            u:
                Function,
            fname:
                str):
        """Dump BDD as DDDMP file named `fname`."""
        if u.manager != self.manager:
            raise ValueError(
                '`u.manager != self.manager`')
        n_declared_vars = len(self._var_with_index)
        n_cudd_vars = self._number_of_cudd_vars()
        if n_declared_vars != n_cudd_vars:
            counts = _utils.var_counts(self)
            contiguous = _utils.contiguous_levels(
                '_dump_dddmp', self)
            raise AssertionError(
                f'{counts}\n{contiguous}')
        cdef FILE *f
        cdef char **names
        cdef bytes py_bytes
        names = <char **> PyMem_Malloc(
            n_cudd_vars * sizeof(char *))
        str_mem = list()
        for index, var in self._var_with_index.items():
            py_bytes = var.encode()
            str_mem.append(py_bytes)
                # prevent garbage collection
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
        if i != DDDMP_SUCCESS:
            raise RuntimeError(
                'failed to write to DDDMP file')

    cpdef load(
            self,
            filename:
                str):
        """Return `Function` loaded from `filename`.

        @param filename:
            name of file from
            where the BDD is loaded
        @return:
            roots of loaded BDDs
        @rtype:
            depends on the contents of the file:
            | `dict[str, Function]`
            | `list[Function]`
        """
        if filename.lower().endswith('.dddmp'):
            r = self._load_dddmp(filename)
            return [r]
        elif filename.lower().endswith('.json'):
            return _copy.load_json(filename, self)
        else:
            raise ValueError(
                f'Unknown file type "{filename}"')

    cpdef Function _load_dddmp(
            self,
            filename:
                str):
        n_declared_vars = len(self._var_with_index)
        n_cudd_vars = self._number_of_cudd_vars()
        if n_declared_vars != n_cudd_vars:
            counts = _utils.var_counts(self)
            contiguous = _utils.contiguous_levels(
                '_load_dddmp', self)
            raise AssertionError(f'{counts}\n{contiguous}')
        r: DdRef
        cdef FILE *f
        cdef char **names
        cdef bytes py_bytes
        names = <char **> PyMem_Malloc(
            n_cudd_vars * sizeof(char *))
        str_mem = list()
        for index, var in self._var_with_index.items():
            py_bytes = var.encode()
            str_mem.append(py_bytes)
            names[index] = py_bytes
        try:
            f = fopen(filename.encode(), 'r')
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
                'A malformed DDDMP file '
                'can cause segmentation '
                'faults to `cudd/dddmp`.')
        finally:
            fclose(f)
            PyMem_Free(names)
        if r is NULL:
            raise RuntimeError(
                'failed to load DDDMP file.')
        h = wrap(self, r)
        # `Dddmp_cuddBddArrayLoad` references `r`
        Cudd_RecursiveDeref(self.manager, r)
        return h

    @property
    def false(
            self
            ) -> Function:
        """Boolean value false."""
        return self._bool(False)

    @property
    def true(
            self
            ) -> Function:
        """Boolean value true."""
        return self._bool(True)

    cdef Function _bool(
            self,
            v:
                python_bool):
        """Return leaf node for Boolean `v`."""
        r: DdRef
        if v:
            r = Cudd_ReadOne(self.manager)
        else:
            r = Cudd_ReadLogicZero(self.manager)
        return wrap(self, r)


cpdef Function restrict(
        u:
            Function,
        care_set:
            Function):
    """Restrict `u` to `care_set`.

    The operator "restrict" is defined in
    1990 Coudert ICCAD.
    """
    if u.manager != care_set.manager:
        raise ValueError(
            '`u.manager != care_set.manager`')
    r: DdRef
    r = Cudd_bddRestrict(
        u.manager, u.node, care_set.node)
    return wrap(u.bdd, r)


cpdef Function and_exists(
        u:
            Function,
        v:
            Function,
        qvars:
            _abc.Iterable[
                _VariableName]):
    r"""Return `\E qvars:  u /\ v`."""
    if u.manager != v.manager:
        raise ValueError(
            '`u.manager != v.manager`')
    qvars = set(qvars)
    cube = u.bdd.cube(qvars)
    r = Cudd_bddAndAbstract(
        u.manager, u.node, v.node, cube.node)
    return wrap(u.bdd, r)


cpdef Function or_forall(
        u:
            Function,
        v:
            Function,
        qvars:
            _abc.Iterable[
                _VariableName]):
    r"""Return `\A qvars:  u \/ v`."""
    if u.manager != v.manager:
        raise ValueError(
            '`u.manager != v.manager`')
    qvars = set(qvars)
    cube = u.bdd.cube(qvars)
    r = Cudd_bddAndAbstract(
        u.manager,
        Cudd_Not(u.node),
        Cudd_Not(v.node),
        cube.node)
    r = Cudd_Not(r)
    return wrap(u.bdd, r)


cpdef reorder(
        bdd:
            BDD,
        dvars:
            _VariableLevels |
            None=None):
    """Reorder `bdd` to order in `dvars`.

    If `dvars` is `None`, then invoke group sifting.
    """
    # invoke sifting ?
    if dvars is None:
        Cudd_ReduceHeap(
            bdd.manager,
            CUDD_REORDER_GROUP_SIFT, 1)
        return
    n_declared_vars = len(bdd.vars)
    n_cudd_vars = bdd._number_of_cudd_vars()
    if n_declared_vars != n_cudd_vars:
        counts = _utils.var_counts(bdd)
        contiguous = _utils.contiguous_levels(
            'reorder', bdd)
        raise AssertionError(
            f'{counts}\n{contiguous}')
    # partial reorderings not supported for now
    if len(dvars) != n_cudd_vars:
        raise ValueError(
            'Mismatch of variable numbers:\n'
            'the number of declared variables '
            f'is: {n_cudd_vars}\n'
            f'new variable order: {len(dvars)}')
    cdef int *p
    p = <int *> PyMem_Malloc(
        n_cudd_vars * sizeof(int *))
    level_to_var = {v: k for k, v in dvars.items()}
    for level in range(n_cudd_vars):
        var = level_to_var[level]
        index = bdd._index_of_var[var]
        p[level] = index
    try:
        r = Cudd_ShuffleHeap(bdd.manager, p)
    finally:
        PyMem_Free(p)
    if r != 1:
        raise RuntimeError(
            'Failed to reorder. '
            'Variable groups that are incompatible to '
            'the given order can cause this.')


def copy_vars(
        source:
            BDD,
        target:
            BDD
        ) -> None:
    """Copy variables, preserving CUDD indices."""
    for var, index in source._index_of_var.items():
        target.add_var(var, index=index)


cpdef Function copy_bdd(
        u:
            Function,
        target:
            BDD):
    """Copy BDD of node `u` to manager `target`.

    Turns off reordering in `source`
    when checking for missing vars in `target`.

    ```tla
    ASSUME
        u in source
    ```
    """
    logger.debug('++ transfer bdd')
    source = u.bdd
    if u.manager == target.manager:
        logger.warning(
            'copying node to same manager')
        return u
    # target missing vars ?
    cfg = source.configure(reordering=False)
    supp = source.support(u)
    source.configure(reordering=cfg['reordering'])
    missing = {
        var for var in supp
        if var not in target.vars}
    if missing:
        raise ValueError(
            '`target` BDD is missing the variables:\n'
            f'{missing}\n'
            'the declared variables in `target` are:\n'
            f'{target.vars}\n')
    # mapping of indices
    n_cudd_vars = source._number_of_cudd_vars()
    cdef int *renaming
    renaming = <int *> PyMem_Malloc(
        n_cudd_vars * sizeof(int))
    # only support will show up during BDD traversal
    for var in supp:
        i = source._index_of_var[var]
        j = target._index_of_var[var]
        renaming[i] = j
    try:
        r = Cudd_bddTransferRename(
            source.manager,
            target.manager, u.node, renaming)
    finally:
        PyMem_Free(renaming)
    logger.debug(
        '-- done transferring bdd')
    return wrap(target, r)


cpdef int count_nodes(
        functions:
            list[Function]):
    """Return total nodes used by `functions`.

    Sharing is taken into account.
    """
    cdef DdRef *x
    f: Function
    n = len(functions)
    x = <DdRef *> PyMem_Malloc(
        n * sizeof(DdRef))
    for i, f in enumerate(functions):
        x[i] = f.node
    try:
        k = Cudd_SharingSize(x, n)
    finally:
        PyMem_Free(x)
    return k


cpdef dict count_nodes_per_level(
        bdd:
            BDD):
    """Return mapping of each var to a node count."""
    d = dict()
    for var in bdd.vars:
        level = bdd.level_of_var(var)
        n = bdd.manager.subtables[level].keys
        d[var] = n
    return d


def dump(
        u:
            Function,
        file_name:
            str
        ) -> None:
    """Pickle variable order and dump dddmp file."""
    bdd = u.bdd
    pickle_fname = f'{file_name}.pickle'
    dddmp_fname = f'{file_name}.dddmp'
    order = {
        var: bdd.level_of_var(var)
        for var in bdd.vars}
    d = dict(variable_order=order)
    with open(pickle_fname, 'wb') as f:
        pickle.dump(d, f, protocol=2)
    bdd.dump(u, dddmp_fname)


def load(
        file_name:
            str,
        bdd:
            BDD,
        reordering:
            _Yes=False
        ) -> Function:
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

    @param reordering:
        if `True`,
        then enable reordering during DDDMP load.
    """
    t0 = time.time()
    pickle_fname = f'{file_name}.pickle'
    dddmp_fname = f'{file_name}.dddmp'
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
    logger.info(
        f'BDD load time from file: {dt}')
    return u


cdef _dict_to_cube_array(
        d:
            _Assignment,
        int *x,
        index_of_var:
            _Assignment |
            set[_VariableName]):
    """Assign array of literals `x` from assignment `d`.

    @param x:
        array of literals
        0: negated, 1: positive, 2: don't care
        read `Cudd_FirstCube`
    @param index_of_var:
        `dict` from variables to `bool`
        or `set` of variable names.
    """
    for var in d:
        if var not in index_of_var:
            raise ValueError(var)
    for var, j in index_of_var.items():
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
                f'unknown value: {b}')


cdef dict _cube_array_to_dict(
        int *x,
        index_of_var:
            dict):
    """Return assignment from array of literals `x`.

    @param x:
        read `_dict_to_cube_array`
    """
    d = dict()
    for var, j in index_of_var.items():
        b = x[j]
        if b == 2:
            continue
        elif b == 1:
            d[var] = True
        elif b == 0:
            d[var] = False
        else:
            raise Exception(
                f'unknown polarity: {b}, '
                f'for variable "{var}"')
    return d


cdef Function wrap(
        bdd:
            BDD,
        node:
            DdRef):
    """Return a `Function` that wraps `node`."""
    # because `@classmethod` unsupported
    f = Function()
    f.init(node, bdd)
    return f


cdef class Function:
    r"""Wrapper of `DdNode` from CUDD.

    Attributes (those that are properties are
    described in their docstrings):

      - `_index`
      - `_ref`: safe lower bound on reference count
        of the CUDD BDD node pointed to by this
        `Function` instance. Do not modify this value.
      - `var`
      - `level`
      - `ref`
      - `low`
      - `high`
      - `negated`
      - `support`
      - `dag_size`

    In Python, use as:

    ```python
    from dd.cudd import BDD

    bdd = BDD()
    u = bdd.true
    v = bdd.false
    w = u | ~ v
    ```

    In Cython, use as:

    ```cython
    bdd = BDD()
    cdef DdNode *u
    u = Cudd_ReadOne(bdd.manager)
    f = Function()
    f.init(bdd, u)
    ```


    About reference counting
    ========================

    Nothing needs to be done for reference counting
    by the user: reference counting is automated.

    "Early" dereferencing of a CUDD BDD node is
    possible by using the statement:

    ```python
    del u
    ```

    where `u` is an instance of the class `Function`.
    "Early" here means that the CUDD BDD node will
    be dereferenced before it would have otherwise
    been dereferenced.

    That (possibly) later time would have been when
    Python exited the scope where `u` was defined,
    or even later, in case other references to the
    object with `id(u)` existed.

    The method `dd.cudd.BDD.decref` should not be
    called for "early" dereferencing. Instead,
    write `del u` as above.

    However, if the user decides to call any
    of the methods:

    - `dd.cudd.BDD.incref(u)`
    - `dd.cudd.BDD.decref(u)`

    then the user needs to ensure that `u._ref > 0`
    before each call to these methods,
    taking into account that:

    - `dd.cudd.BDD.incref(u)` increments `u._ref`
    - `dd.cudd.BDD.decref(u)` decrements `u._ref` and
      sets `u.node` to `NULL` when `u._ref` becomes `0`.

    The attribute `u._ref` is *not* the
    reference count of the BDD node in CUDD
    that the C attribute `u.node`
    points to. The value of `u._ref` is
    a lower bound on the reference count of
    the BDD node that `u.node` points to.

    This is a safe approach for accessing
    memory in CUDD. The following example
    demonstrates this approach.

    We start with:

    ```python
    from dd.cudd import BDD

    bdd = BDD()
    bdd.declare('x', 'y')
    u = bdd.add_expr(r'x /\ ~ y')

    w = u
    assert w is u
    ```

    i.e., `u` and `w` are different Python variables
    that point to the *same* instance of `Function`.
    This `Function` instance points to
    a BDD node in CUDD.
    We will refer to this `Function` instance as
    "the object with `id(u)`".

    ```python
    v = bdd.add_expr(r'x /\ ~ y')
    assert v is not u
    ```

    i.e., the Python variable `v` points to an
    instance of `Function` different from the
    `Function` instance that `u` points to.
    We will refer to the `Function` instance that
    `v` points to as "the object with `id(v)`".

    The object with `id(v)` and the object with `id(u)`
    point to the same BDD node in CUDD.

    The statement

    ```python
    bdd.decref(v, recursive=True)
    ```

    decrements:

    - the reference count of the BDD node in CUDD
      that the object with `id(v)` points to

    - the lower bound `v._ref`

    - the reference counts of CUDD BDD nodes that
      are successors, recursively, when a node's
      reference count becomes 0. For more details
      read the docstring of the CUDD function
      `Cudd_RecursiveDeref`.

    Setting the parameter `recursive` to `True`
    here has no effect, because due to `u` the
    reference count of the CUDD BDD node corresponding
    to `v` remains positive after the decrement.

    But in general this is not the case,
    so `recursive=True` is then necessary,
    because afterwards it is impossible to
    dereference the successors of the CUDD BDD node
    that corresponds to `v`. The reason is
    described next.

    The object with `id(v)` *cannot* be used after
    this point, because the call to the method `decref`
    resulted in `v._ref == 0`, so it also set the
    pointer `v.node` to `NULL`.

    Setting `v.node` to `NULL` guards from further
    use of the object with `id(v)` to
    access CUDD BDD nodes.
    The object with `id(v)` should *not* be used
    after this point.

    In this specific example,
    if the method `decref` did not
    set `v.node` to `NULL`, then using `v` beyond
    this point would actually not have caused problems,
    because the CUDD BDD node's reference count
    is still positive (due to the increment
    when the object with `id(u)` was instantiated).

    But in general this is not the case.

    Also, after the attribute `v._ref` becomes `0`,
    there is no safe way for the object with `id(v)`
    to read the reference count of the CUDD BDD node
    that this object points to, even though that
    reference count is positive and the BDD node
    is still accessible via `u` and `w`.

    From the perspective of the object with `id(v)`,
    further access to that CUDD BDD node is unsafe.

    Had the method `decref` not set `u.node` to `NULL`,
    then if we had continued by doing:

    ```python
    bdd.decref(u, recursive=True)
    ```

    then both variables `u` and `w`
    should *not* had been used any further.
    These variables refer to the
    same Python object, and `u._ref == 0`
    (thus `w._ref == 0`). So the same observations
    apply to `u` and `w` as for `v` above.
    """

    __weakref__: object
    cdef public BDD bdd
    cdef DdManager *manager
    node: DdRef
    cdef public int _ref

    cdef init(
            self,
            node:
                DdRef,
            bdd:
                BDD):
        if node is NULL:
            raise ValueError(
                '`DdNode *node` is `NULL` pointer.')
        self.bdd = bdd
        self.manager = bdd.manager
        self.node = node
        self._ref = 1  # lower bound on
            # reference count
            #
            # Assumed invariant:
            # this instance participates in
            # computation only as long as
            # `self._ref > 0`.
            # The user is responsible for
            # implementing this invariant.
        Cudd_Ref(node)

    def __hash__(
            self
            ) -> int:
        return int(self)

    @property
    def _index(
            self
            ) -> _Nat:
        """Index of `self.node`."""
        return Cudd_NodeReadIndex(self.node)

    @property
    def var(
            self
            ) -> (
                _VariableName |
                None):
        """Variable at level where this node is.

        If node is constant, return `None`.
        """
        if Cudd_IsConstant(self.node):
            return None
        return self.bdd._var_with_index[self._index]

    @property
    def level(
            self
            ) -> _Level:
        """Level where this node currently is."""
        i = self._index
        return Cudd_ReadPerm(self.manager, i)

    @property
    def ref(
            self
            ) -> _Cardinality:
        """Reference count of node.

        Returns the sum of the reference count
        of this BDD root, and of the reference
        count of the root of the negated BDD.
        """
        u: DdRef
        u = Cudd_Regular(self.node)
        return u.ref

    @property
    def low(
            self
            ) -> '''
                Function |
                None
                ''':
        """Return "else" node as `Function`."""
        u: DdRef
        if Cudd_IsConstant(self.node):
            return None
        u = Cudd_E(self.node)
        return wrap(self.bdd, u)

    @property
    def high(
            self
            ) -> '''
                Function |
                None
                ''':
        """Return "then" node as `Function`."""
        u: DdRef
        if Cudd_IsConstant(self.node):
            return None
        u = Cudd_T(self.node)
        return wrap(self.bdd, u)

    @property
    def negated(
            self
            ) -> _Yes:
        """`True` if this is a complemented edge.

        Returns `True` if `self` is
        a complemented edge.
        """
        return Cudd_IsComplement(self.node)

    @property
    def support(
            self:
                BDD
            ) -> set[_VariableName]:
        """Return `set` of variables in support."""
        return self.bdd.support(self)

    def __dealloc__(
            self
            ) -> None:
        # when changing this method,
        # update also the function
        # `_test_call_dealloc` below
        if self._ref < 0:
            raise AssertionError(
                "The lower bound `_ref` "
                "on the node's "
                'reference count has '
                f'value {self._ref}, '
                'which is unexpected and '
                'should never happen. '
                'Was the value of `_ref` '
                'changed from outside '
                'this instance?')
        assert self._ref >= 0, self._ref
        if self._ref == 0:
            return
        if self.node is NULL:
            raise AssertionError(
                'The attribute `node` is '
                'a `NULL` pointer. '
                'This is unexpected and '
                'should never happen. '
                'Was the value of `_ref` '
                'changed from outside '
                'this instance?')
        # anticipate multiple calls to `__dealloc__`
        self._ref -= 1
        # deref
        Cudd_RecursiveDeref(
            self.manager, self.node)
        # avoid future access
        # to deallocated memory
        self.node = NULL

    def __int__(
            self
            ) -> int:
        """Inverse of `BDD._add_int()`."""
        return _ddref_to_int(self.node)

    def __repr__(
            self
            ) -> str:
        u: DdRef
        u = Cudd_Regular(self.node)
        return (
            f'<dd.cudd.Function at {hex(id(self))}, '
            'wrapping a DdNode with '
            f'var index: {u.index}, '
            f'ref count: {u.ref}, '
            f'int repr: {int(self)}>')

    def __str__(
            self
            ) -> str:
        return f'@{int(self)}'

    def __len__(
            self
            ) -> _Cardinality:
        return Cudd_DagSize(self.node)

    @property
    def dag_size(
            self
            ) -> _Cardinality:
        """Return number of BDD nodes.

        This is the number of BDD nodes that
        are reachable from this BDD reference,
        i.e., with `self` as root.
        """
        return len(self)

    def __eq__(
            self:
                Function,
            other:
                _ty.Optional[Function]
            ) -> _Yes:
        if other is None:
            return False
        # guard against mixing managers
        if self.manager != other.manager:
            raise ValueError(
                '`self.manager != other.manager`')
        return self.node == other.node

    def __ne__(
            self:
                Function,
            other:
                _ty.Optional[Function]
            ) -> _Yes:
        if other is None:
            return True
        if self.manager != other.manager:
            raise ValueError(
                '`self.manager != other.manager`')
        return self.node != other.node

    def __le__(
            self:
                Function,
            other:
                Function
            ) -> _Yes:
        if self.manager != other.manager:
            raise ValueError(
                '`self.manager != other.manager`')
        leq = Cudd_bddLeq(
            self.manager, self.node, other.node)
        return (leq == 1)

    def __lt__(
            self:
                Function,
            other:
                Function
            ) -> _Yes:
        if self.manager != other.manager:
            raise ValueError(
                '`self.manager != other.manager`')
        leq = Cudd_bddLeq(
            self.manager, self.node, other.node)
        return (
            self.node != other.node and
            leq == 1)

    def __ge__(
            self:
                Function,
            other:
                Function
            ) -> _Yes:
        if self.manager != other.manager:
            raise ValueError(
                '`self.manager != other.manager`')
        geq = Cudd_bddLeq(
            self.manager, other.node, self.node)
        return (geq == 1)

    def __gt__(
            self:
                Function,
            other:
                Function
            ) -> _Yes:
        if self.manager != other.manager:
            raise ValueError(
                '`self.manager != other.manager`')
        geq = Cudd_bddLeq(
            self.manager, other.node, self.node)
        return (
            self.node != other.node and
            geq == 1)

    def __invert__(
            self
            ) -> Function:
        r: DdRef
        r = Cudd_Not(self.node)
        return wrap(self.bdd, r)

    def __and__(
            self:
                Function,
            other:
                Function
            ) -> Function:
        if self.manager != other.manager:
            raise ValueError(
                '`self.manager != other.manager`')
        r = Cudd_bddAnd(
            self.manager, self.node, other.node)
        return wrap(self.bdd, r)

    def __or__(
            self:
                Function,
            other:
                Function
            ) -> Function:
        if self.manager != other.manager:
            raise ValueError(
                '`self.manager != other.manager`')
        r = Cudd_bddOr(
            self.manager, self.node, other.node)
        return wrap(self.bdd, r)

    def implies(
            self:
                Function,
            other:
                Function
            ) -> Function:
        if self.manager != other.manager:
            raise ValueError(
                '`self.manager != other.manager`')
        r = Cudd_bddIte(
            self.manager, self.node,
            other.node, Cudd_ReadOne(self.manager))
        return wrap(self.bdd, r)

    def equiv(
            self:
                Function,
            other:
                Function
            ) -> Function:
        if self.manager != other.manager:
            raise ValueError(
                '`self.manager != other.manager`')
        r = Cudd_bddIte(
            self.manager, self.node,
            other.node, Cudd_Not(other.node))
        return wrap(self.bdd, r)

    def let(
            self:
                Function,
            **definitions:
                _VariableName |
                python_bool |
                Function
            ) -> Function:
        return self.bdd.let(definitions, self)

    def exist(
            self:
                Function,
            *variables:
                _VariableName
            ) -> Function:
        return self.bdd.exist(variables, self)

    def forall(
            self:
                Function,
            *variables:
                _VariableName
            ) -> Function:
        return self.bdd.forall(variables, self)

    def pick(
            self:
                Function,
            care_vars:
                _abc.Set[
                    _VariableName] |
                None=None
            ) -> _Assignment:
        return self.bdd.pick(self, care_vars)

    def count(
            self:
                Function,
            nvars:
                _Cardinality |
                None=None
            ) -> _Cardinality:
        return self.bdd.count(self, nvars)


cdef _ddref_to_int(
        node:
            DdRef):
    """Convert node pointer to numeric index.

    Inverse of `_int_to_ddref()`.
    """
    if sizeof(stdint.uintptr_t) != sizeof(DdRef):
        raise AssertionError(
            'mismatch of sizes')
    index = <stdint.uintptr_t>node
    # 0, 1 used to represent TRUE and FALSE
    # in syntax of expressions
    if 0 <= index:
        index += 2
    if index in (0, 1):
        raise AssertionError(index)
    return index


cdef DdRef _int_to_ddref(
        index:
            int):
    """Convert numeric index to node pointer.

    Inverse of `_ddref_to_int()`.
    """
    if index in (0, 1):
        raise ValueError(index)
    if 2 <= index:
        index -= 2
    u: DdRef = <DdRef><stdint.uintptr_t>index
    return u


"""Tests and test wrappers for C functions."""


cpdef _test_incref():
    bdd = BDD()
    f: Function
    f = bdd.true
    i = f.ref
    bdd._incref(f.node)
    j = f.ref
    if j != i + 1:
        raise AssertionError((j, i))
    # avoid errors in `BDD.__dealloc__`
    bdd._decref(f.node, recursive=True)
    del f


cpdef _test_decref():
    bdd = BDD()
    f: Function
    f = bdd.true
    i = f.ref
    if i != 2:
        raise AssertionError(i)
    bdd._incref(f.node)
    i = f.ref
    if i != 3:
        raise AssertionError(i)
    bdd._decref(f.node, recursive=True)
    j = f.ref
    if j != i - 1:
        raise AssertionError((j, i))
    del f


cpdef _test_dict_to_cube_array():
    cdef int *x
    n = 3
    x = <int *> PyMem_Malloc(
        n * sizeof(int))
    index_of_var = dict(x=0, y=1, z=2)
    d = dict(y=True, z=False)
    _dict_to_cube_array(
        d, x, index_of_var)
    r = [j for j in x[:n]]
    r_ = [2, 1, 0]
    if r != r_:
        raise AssertionError((r, r_))
    PyMem_Free(x)


cpdef _test_cube_array_to_dict():
    cdef int *x
    n = 3
    x = <int *> PyMem_Malloc(
        n * sizeof(int))
    x[0] = 2
    x[1] = 1
    x[2] = 0
    index_of_var = dict(x=0, y=1, z=2)
    d = _cube_array_to_dict(
        x, index_of_var)
    d_ = dict(y=True, z=False)
    if d != d_:
        raise AssertionError((d, d_))
    PyMem_Free(x)


cpdef _test_call_dealloc(
        u:
            Function):
    """Duplicates the code of `Function.__dealloc__`.

    The main purpose of this function is to test the
    exceptions raised in the method `Function.__dealloc__`.

    Exceptions raised in `__dealloc__` are ignored
    (they become messages), and it seems impossible to
    call `__dealloc__` directly (unlike `__del__`),
    so there is no way to assert what exceptions
    are raised in `__dealloc__`.

    This function is the closest thing to testing
    those exceptions.
    """
    self = u
    # the code of `Function.__dealloc__` follows:
    if self._ref < 0:
        raise AssertionError(
            "The lower bound `_ref` on the node's "
            'reference count has value {self._ref}, '
            'which is unexpected and should never happen. '
            'Was the value of `_ref` changed from outside '
            'this instance?')
    assert self._ref >= 0, self._ref
    if self._ref == 0:
        return
    if self.node is NULL:
        raise AssertionError(
            'The attribute `node` is a `NULL` pointer. '
            'This is unexpected and should never happen. '
            'Was the value of `_ref` changed from outside '
            'this instance?')
    # anticipate multiple calls to `__dealloc__`
    self._ref -= 1
    # deref
    Cudd_RecursiveDeref(self.manager, self.node)
    # avoid future access to deallocated memory
    self.node = NULL
