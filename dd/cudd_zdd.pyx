"""Cython interface to ZDD implementation in CUDD.

ZDDs are represented without complemented edges in CUDD (unlike BDDs).
So rectifying a node to "regular" is unnecessary.
Variable `__version__` equals CUDD's version string.


Reference
=========
    Fabio Somenzi
    "CUDD: CU Decision Diagram Package"
    University of Colorado at Boulder
    v2.5.1, 2015
    <http://vlsi.colorado.edu/~fabio/>
"""
# Copyright 2015-2020 by California Institute of Technology
# All rights reserved. Licensed under 3-clause BSD.
#
#
# Copyright (c) 1995-2015, Regents of the University of Colorado
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#
# Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
#
# Neither the name of the University of Colorado nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
import itertools as _itr
import logging
import textwrap as _tw
import typing as _ty
import warnings

from cpython cimport bool as python_bool
from cpython.mem cimport PyMem_Malloc, PyMem_Free
import cython
cimport libc.stdint as stdint
from libc.stdio cimport FILE, fdopen, fopen, fclose
from libcpp cimport bool

from dd import _copy
from dd import _parser
from dd import _utils
from dd import bdd as _bdd


ctypedef cython.int _c_level
ctypedef cython.int _c_int
BDDFileType: _ty.TypeAlias = _ty.Literal[
    'pdf',
    'png',
    'svg']


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
        DdNode **univ
        int reordered
    # local hash tables
    ctypedef stdint.intptr_t ptrint
    struct DdHashItem:
        DdHashItem *next
        DdNode *value
    struct DdHashTable:
        DdHashItem **bucket
        DdHashItem **memoryList
        unsigned int numBuckets
        DdManager *manager
    DdHashTable * cuddHashTableInit(
        DdManager *manager,
        unsigned int keySize,
        unsigned int initSize)
    void cuddHashTableQuit(
        DdHashTable *hash)
    int cuddHashTableInsert1(
        DdHashTable *hash, DdNode *f,
        DdNode *value, ptrint count)
    DdNode * cuddHashTableLookup1(
        DdHashTable *hash, DdNode *f)
    # cache
    DdNode * cuddCacheLookup2Zdd(
        DdManager *table,
        DdNode * (*)(
            DdManager *, DdNode *, DdNode *),
        DdNode *f,
        DdNode *g)
    void cuddCacheInsert2(
        DdManager *table,
        DdNode * (*)(
            DdManager *, DdNode *, DdNode *),
        DdNode *f,
        DdNode *g,
        DdNode *data)
    # node elements
    DdNode *cuddUniqueInter(
        DdManager *unique, int index,
        DdNode *T, DdNode *E)
    DdNode * cuddUniqueInterZdd(
        DdManager *unique, int index,
        DdNode *T, DdNode *E)
    bool cuddIsConstant(
        DdNode *u)
    DdNode *DD_ZERO(
        DdManager *mgr)
    DdNode *DD_ONE(
        DdManager *mgr)
    DdNode *cuddT(
        DdNode *u)  # top cofactors
    DdNode *cuddE(
        DdNode *u)
    # BDD node elements
    DdNode *Cudd_Not(
        DdNode *dd)
    DdNode *Cudd_Regular(
        DdNode *u)
    bool Cudd_IsComplement(
        DdNode *u)
    # reference counting
    void cuddRef(
        DdNode *u)
    void cuddDeref(
        DdNode *u)
    # recursive ITE
    DdNode * cuddZddIte(
        DdManager *dd,
        DdNode *f, DdNode *g, DdNode *h)
    # realignment
    int Cudd_zddRealignmentEnabled(
        DdManager *unique)
    void Cudd_zddRealignEnable(
        DdManager *unique)
    void Cudd_zddRealignDisable(
        DdManager *unique)
    int Cudd_bddRealignmentEnabled(
        DdManager *unique)
    void Cudd_bddRealignEnable(
        DdManager *unique)
    void Cudd_bddRealignDisable(
        DdManager *unique)
cdef extern from 'cudd.h':
    # node
    ctypedef unsigned int DdHalfWord
    struct DdNode:
        DdHalfWord index
        DdHalfWord ref
        DdNode *next
    # manager
    DdManager *Cudd_Init(
        unsigned int numVars,
        unsigned int numVarsZ,
        unsigned int numSlots,
        unsigned int cacheSize,
        size_t maxMemory)
    # generator
    struct DdGen
    # variables
    DdNode *Cudd_zddIthVar(
        DdManager *dd, int index)
    DdNode *Cudd_bddIthVar(
        DdManager *dd, int index)
    DdNode *Cudd_zddSupport(
        DdManager *dd, DdNode *f)
    int Cudd_ReadPermZdd(
        DdManager *dd, int index)
    int Cudd_ReadInvPermZdd(
        DdManager *dd, int level)
    unsigned int Cudd_NodeReadIndex(
        DdNode *u)
    # cofactors (of any given `var`, not only top)
    DdNode *Cudd_zddSubset1(
        DdManager *dd, DdNode *P, int var)
    DdNode *Cudd_zddSubset0(
        DdManager *dd, DdNode *P, int var)
    # conversions between BDDs and ZDDs
    int Cudd_zddVarsFromBddVars(
        DdManager *dd, int multiplicity)
    DdNode *Cudd_zddPortFromBdd(
        DdManager *dd, DdNode *B)
    DdNode *Cudd_zddPortToBdd(
        DdManager *dd, DdNode *f)
    # propositional operators
    DdNode *Cudd_zddIte(
        DdManager *dd,
        DdNode *f, DdNode *g, DdNode *h)
    DdNode *Cudd_zddUnion(
        DdManager *dd, DdNode *P, DdNode *Q)
    DdNode *Cudd_zddIntersect(
        DdManager *dd, DdNode *P, DdNode *Q)
    DdNode *Cudd_zddDiff(
        DdManager *dd, DdNode *P, DdNode *Q)
    # constants
    DdNode *Cudd_ReadZddOne(
        DdManager *dd, int i)
        # `i` is the index of the topmost variable
    DdNode *Cudd_ReadZero(DdManager *dd)
    # counting
    int Cudd_zddDagSize(
        DdNode *p_node)
    double Cudd_zddCountMinterm(
        DdManager *zdd, DdNode *node, int path)
    int Cudd_zddCount(
        DdManager *zdd, DdNode *P)
    int Cudd_BddToCubeArray(
        DdManager *dd, DdNode *cube, int *array)
    # pick
    DdGen *Cudd_zddFirstPath(
        DdManager *zdd, DdNode *f, int **path)
    int Cudd_zddNextPath(
        DdGen *gen, int **path)
    int Cudd_IsGenEmpty(
        DdGen *gen)
    int Cudd_GenFree(
        DdGen *gen)
    # info
    int Cudd_PrintInfo(
        DdManager *dd, FILE *fp)
    int Cudd_ReadZddSize(
        DdManager *dd)
    long Cudd_zddReadNodeCount(
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
    ctypedef enum Cudd_ReorderingType:
        pass
    void Cudd_AutodynEnableZdd(
        DdManager *unique,
        Cudd_ReorderingType method)
    void Cudd_AutodynDisableZdd(
        DdManager *unique)
    int Cudd_ReorderingStatusZdd(
        DdManager *unique,
        Cudd_ReorderingType *method)
    int Cudd_zddReduceHeap(
        DdManager *table,
        Cudd_ReorderingType heuristic,
        int minsize)
    int Cudd_zddShuffleHeap(
        DdManager *table, int *permutation)
    void Cudd_SetSiftMaxSwap(
        DdManager *dd, int sms)
    int Cudd_ReadSiftMaxSwap(
        DdManager *dd)
    void Cudd_SetSiftMaxVar(
        DdManager *dd, int smv)
    int Cudd_ReadSiftMaxVar(
        DdManager *dd)
    # The function `Cudd_zddReduceHeap` increments the
    # counter `dd->reorderings`. The function `Cudd_ReadReorderings`
    # reads this counter.
    unsigned int Cudd_ReadReorderings(
        DdManager *dd)
    # The function `Cudd_zddReduceHeap` adds to the attribute
    # `dd->reordTime`. The function `Cudd_ReadReorderingTime`
    # reads this attribute.
    long Cudd_ReadReorderingTime(
        DdManager *dd)
    # manager config
    size_t Cudd_ReadMaxMemory(
        DdManager *dd)
    size_t Cudd_SetMaxMemory(
        DdManager *dd, size_t maxMemory)
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
    # reference counting
    void Cudd_Ref(
        DdNode *n)
    void Cudd_Deref(
        DdNode *n)
    void Cudd_RecursiveDerefZdd(
        DdManager *table, DdNode *n)
    int Cudd_CheckZeroRef(
        DdManager *manager)
    # checks
    int Cudd_DebugCheck(
        DdManager *table)
    void Cudd_Quit(
        DdManager *unique)
    # manager config
    void Cudd_EnableGarbageCollection(
        DdManager *dd)
    void Cudd_DisableGarbageCollection(
        DdManager *dd)
    int Cudd_GarbageCollectionEnabled(
        DdManager * dd)
    # BDD functions
    DdNode *Cudd_bddIte(
        DdManager *dd,
        DdNode *f, DdNode *g, DdNode *h)
cdef extern from 'util.h':
    void FREE(void *ptr)

    # node elements
ctypedef DdNode *DdRef
cdef CUDD_UNIQUE_SLOTS = 2**8
cdef CUDD_CACHE_SLOTS = 2**18
cdef CUDD_REORDER_SIFT = 4
cdef CUDD_OUT_OF_MEM = -1
cdef MAX_CACHE = <unsigned int> - 1  # entries
__version__ = CUDD_VERSION.decode('utf-8')


# 2**30 = 1 GiB (gibibyte, read ISO/IEC 80000)
DEFAULT_MEMORY = 1 * 2**30
logger = logging.getLogger(__name__)


class CouldNotCreateNode(Exception):
    pass


cdef class ZDD:
    """Wrapper of CUDD manager.

    Interface similar to `dd._abc.BDD` and `dd.cudd.BDD`.
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
            memory_estimate=None,
            initial_cache_size=None,
            *arg,
            **kw):
        """Initialize ZDD manager.

        @param memory_estimate:
            maximum allowed memory, in bytes.
        """
        self.manager = NULL  # prepare for `__dealloc__`
        total_memory = _utils.total_memory()
        default_memory = DEFAULT_MEMORY
        if memory_estimate is None:
            memory_estimate = default_memory
        if total_memory is None:
            pass
        elif memory_estimate >= total_memory:
            memory_example = round(total_memory / 2)
            msg = (
                'Error in `dd.cudd_zdd.ZDD`: '
                f'total physical memory is {total_memory} bytes, '
                f'but requested {memory_estimate} bytes. '
                'To avoid this error, pass an amount of memory, '
                f'for example: `ZDD({memory_example})`.')
            # Motivation is described in
            # comments inside `dd.cudd.BDD.__cinit__`.
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
            memory_estimate=None,
            initial_cache_size=None):
        logger.info(f'Using CUDD v{__version__}')
        self.configure(reordering=True, max_cache_hard=MAX_CACHE)
        self.vars = set()
        self._index_of_var = dict()  # map: str -> unique fixed int
        self._var_with_index = dict()

    def __dealloc__(
            self):
        if self.manager is NULL:
            raise RuntimeError(
                '`self.manager` is `NULL`, which suggests that '
                'an exception was raised inside the method '
                '`dd.cudd_zdd.ZDD.__cinit__`.')
        n = Cudd_CheckZeroRef(self.manager)
        if n != 0:
            raise AssertionError(
                f'Still {n} nodes '
                'referenced upon shutdown.')
        Cudd_Quit(self.manager)

    def __eq__(
            self:
                ZDD,
            other:
                ZDD):
        """Return `True` if `other` has same manager.

        If `other is None`, then return `False`.
        """
        if other is None:
            return False
        return self.manager == other.manager

    def __ne__(
            self:
                ZDD,
            other:
                ZDD):
        """Return `True` if `other` has different manager.

        If `other is None`, then return `True`.
        """
        if other is None:
            return True
        return self.manager != other.manager

    def __len__(
            self):
        """Return number of nodes with non-zero references."""
        return Cudd_CheckZeroRef(self.manager)

    def __contains__(
            self,
            u:
                Function):
        """Return `True` if `u.node` in `self.manager`."""
        if u.manager != self.manager:
            raise ValueError(
                'undefined containment, because '
                '`u.manager != self.manager`')
        try:
            Cudd_NodeReadIndex(u.node)
            return True
        except:
            return False

    # This method is similar to
    # the method `dd.cudd.BDD.__str__`.
    def __str__(
            self):
        d = self.statistics()
        s = (
            'Zero-omitted binary decision diagram (CUDD wrapper).\n'
            '\t {n} live nodes now\n'
            '\t {peak} live nodes at peak\n'
            '\t {n_vars} ZDD variables\n'
            '\t {mem:10.1f} bytes in use\n'
            '\t {reorder_time:10.1f} sec spent reordering\n'
            '\t {n_reorderings} reorderings\n').format(
                n=d['n_nodes'],
                peak=d['peak_live_nodes'],
                n_vars=d['n_vars'],
                reorder_time=d['reordering_time'],
                n_reorderings=d['n_reorderings'],
                mem=d['mem'])
        return s

    # This method is similar to
    # the method `dd.cudd.BDD.statistics`.
    def statistics(
            self:
                ZDD,
            exact_node_count=False):
        """Return `dict` with CUDD node counts and times.

        For details read the docstring of the method
        `dd.cudd.BDD.statistics`.
        """
        warnings.warn(
            "Changed in `dd` version 0.5.7: "
            "In the `dict` returned by the method "
            '`dd.cudd_zdd.ZDD.statistics`, '
            "the value of the key `'mem'` "
            "has changed to bytes (from 10**6 bytes).",
            UserWarning)
        cdef DdManager *mgr
        mgr = self.manager
        n_vars = Cudd_ReadZddSize(mgr)
        # nodes
        if exact_node_count:
            n_nodes = Cudd_zddReadNodeCount(mgr)
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

    # This method is similar to the method
    # `dd.cudd.BDD.configure`.
    def configure(
            self,
            **kw):
        """Read and apply parameter values.

        For details read the docstring of the method
        `dd.cudd.BDD.configure`.
        """
        cdef int method
        cdef DdManager *mgr
        mgr = self.manager
        # read
        reordering = Cudd_ReorderingStatusZdd(
            self.manager, <Cudd_ReorderingType *>&method)
        garbage_collection = Cudd_GarbageCollectionEnabled(self.manager)
        max_memory = Cudd_ReadMaxMemory(mgr)
        loose_up_to = Cudd_ReadLooseUpTo(mgr)
        max_cache_soft = Cudd_ReadMaxCache(mgr)
        max_cache_hard = Cudd_ReadMaxCacheHard(mgr)
        min_hit = Cudd_ReadMinHit(mgr)
        max_growth = Cudd_ReadMaxGrowth(mgr)
        max_swaps = Cudd_ReadSiftMaxSwap(mgr)
        max_vars = Cudd_ReadSiftMaxVar(mgr)
        d = dict(
            reordering=
                True if reordering == 1 else False,
            garbage_collection=
                True if garbage_collection == 1 else False,
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
                    self._enable_reordering()
                else:
                    self._disable_reordering()
            elif k == 'garbage_collection':
                if v:
                    Cudd_EnableGarbageCollection(self.manager)
                else:
                    Cudd_DisableGarbageCollection(self.manager)
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
                raise ValueError(
                    f'Unknown parameter "{k}"')
        return d

    cpdef succ(
            self,
            u:
                Function):
        """Return `(level, low, high)` for `u`."""
        if u.manager != self.manager:
            raise ValueError('`u.manager != self.manager`')
        i = u.level
        v = u.low
        w = u.high
        if v is not None and i >= v.level:
            raise AssertionError('v.level')
        if w is not None and i >= w.level:
            raise AssertionError('w.level')
        return i, v, w

    cpdef incref(
            self,
            u:
                Function):
        """Increment the reference count of `u`.

        For details read the docstring of the
        method `dd.cudd.BDD.incref`.
        """
        if u.node is NULL:
            raise RuntimeError('`u.node` is `NULL` pointer.')
        if u._ref <= 0:
            _utils._raise_runtimerror_about_ref_count(
                u._ref, 'method `dd.cudd_zdd.ZDD.incref`',
                '`dd.cudd_zdd.Function`')
        assert u._ref > 0, u._ref
        u._ref += 1
        self._incref(u.node)

    cpdef decref(
            self,
            u:
                Function,
            recursive=False,
            _direct=False):
        """Decrement the reference count of `u`.

        For details read the docstring of the
        method `dd.cudd.BDD.decref`.

        @param recursive:
            if `True`, then call
            `Cudd_RecursiveDerefZdd`,
            else call `Cudd_Deref`
        @param _direct:
            use this parameter only after
            reading the source code of the
            Cython file `dd/cudd_zdd.pyx`.
            When `_direct == True`, some of the above
            description does not apply.
        """
        if u.node is NULL:
            raise RuntimeError('`u.node` is `NULL` pointer.')
        # bypass checks and leave `u._ref` unchanged,
        # directly call `_decref`
        if _direct:
            self._decref(u.node, recursive)
            return
        if u._ref <= 0:
            _utils._raise_runtimerror_about_ref_count(
                u._ref, 'method `dd.cudd_zdd.ZDD.decref`',
                '`dd.cudd_zdd.Function`')
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
            recursive=False):
        if recursive:
            Cudd_RecursiveDerefZdd(self.manager, u)
        else:
            Cudd_Deref(u)

    def declare(
            self,
            *variables):
        """Add names in `variables` to `self.vars`."""
        for var in variables:
            self.add_var(var)

    cpdef add_var(
            self,
            var,
            index=None):
        """Return index of variable named `var`.

        If a variable named `var` exists,
        then assert that it has `index`.
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
        u = Cudd_zddIthVar(self.manager, j)
        # ref and recursive deref,
        # in order to cancel refs out
        Cudd_Ref(u)
        Cudd_RecursiveDerefZdd(self.manager, u)
        if u is NULL:
            raise RuntimeError(
                f'failed to add var "{var}"')
        self._add_var(var, j)
        return j

    cdef _add_var(
            self,
            var:
                str,
            int index):
        """Add to `self` a *new* variable named `var`."""
        if var in self.vars:
            raise ValueError(
                f'existing variable: {var}')
        if var in self._index_of_var:
            raise ValueError(
                'variable already has '
                f'index: {self._index_of_var[var]}')
        if index in self._var_with_index:
            raise ValueError(
                'index already corresponds '
                'to a variable: '
                f'{self._var_with_index[index]}')
        self.vars.add(var)
        self._index_of_var[var] = index
        self._var_with_index[index] = var
        if (len(self._index_of_var) !=
                len(self._var_with_index)):
            raise AssertionError(
                'the attributes `_index_of_var` and '
                '`_var_with_index` have different length')

    cpdef Function var(
            self,
            var):
        """Return node for variable named `var`."""
        if var not in self._index_of_var:
            raise ValueError(
                f'undeclared variable "{var}", '
                'the declared variables are:\n'
                f'{self._index_of_var}')
        j = self._index_of_var[var]
        r = _ith_var(var, self)
        return r

    # CUDD implementation of `var`
    cpdef Function _var_cudd(
            self,
            var):
        """Return node for variable named `var`."""
        if var not in self._index_of_var:
            raise ValueError(
                f'undeclared variable "{var}", '
                'the declared variables are:\n'
                f'{self._index_of_var}')
        j = self._index_of_var[var]
        r = Cudd_zddIthVar(self.manager, j)
        return wrap(self, r)

    def _add_bdd_var(
            self,
            j):
        """Declare a BDD variable with index `j`."""
        Cudd_bddIthVar(self.manager, j)

    def var_at_level(
            self,
            level):
        """Return name of variable at `level`.

        Raise `ValueError` if `level` is not
        the level of any variable declared in
        `self.vars`.
        """
        j = Cudd_ReadInvPermZdd(self.manager, level)
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
            var):
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
        level = Cudd_ReadPermZdd(self.manager, j)
        if level == -1:
            raise AssertionError(
                f'index {j} out of bounds')
        return level

    @property
    def var_levels(
            self):
        """Return `dict` that maps variables to levels."""
        return {var: self.level_of_var(var)
                for var in self.vars}

    def _index_at_level(
            self,
            level:
                int
            ) -> (
                int |
                None):
        """Return index of CUDD variable at `level`.

        The presence of such an index does not mean that
        a variable has been declared for that index.

        Declaring variables with indices over a set of
        noncontiguous integers creates these intermediate
        indices. For example:

        ```python
        import dd.cudd_zdd as _zdd
        import pytest

        zdd = _zdd.ZDD()
        zdd.add_var('x', 1)
        assert zdd.level_of_var('x') == 1
        # no `ZDD` declared variable at level 0
        # CUDD does return an index for level 0
        with pytest.raises(ValueError):
            zdd.level_of_var(0)
        # no CUDD variable at level 2
        with pytest.raises(ValueError):
            zdd.level_of_var(2)
        ```

        The usefulness of this method is during
        recursion over BDDs. If this method returns
        `None`, then this means that `level`
        is below the bottommost CUDD variable,
        therefore also below the bottommost
        `dd.cudd.ZDD` variable.

        So a return value of `None` means that
        we have reached the constant nodes
        (even though it can be
        `level > CUDD_CONST_INDEX`).

        Checking `len(zdd.vars) == level` is
        not equivalent, for example:

        ```python
        import dd.cudd_zdd as _zdd

        zdd = _zdd.ZDD()
        zdd.add_var('x', 2)
        n_declared_vars = len(zdd.vars)
        max_var_level = max(
            zdd.level_of_var(var)
            for var in zdd.vars)
        n_cudd_vars = zdd._number_of_cudd_vars()
        print(f'''
            {n_vars = }
            {max_var_level = }
            {n_cudd_vars = }
            ''')
        ```

        So if the recursion stopped at level `n_vars`,
        it would not reach the nodes at `max_var_level`.

        Any computation with noncontiguous levels of
        declared variables is equivalent to a computation
        with contiguous levels.

        @param level:
            level >= 0 for which the corresponding
            CUDD variable index will be returned,
            if it exists
        """
        # `Cudd_ReadInvPermZdd()`:
        # - returns `CUDD_CONST_INDEX` if
        #   `level == CUDD_CONST_INDEX`
        # - returns `invperm[self.manager.level]` if
        #   `0 <= level < self.manager.sizeZ`
        # - otherwise returns `-1`
        j = Cudd_ReadInvPermZdd(self.manager, level)
        if j == -1:
            return None
        if j < 0:
            raise RuntimeError(
                f'unexpected value: {j}, returned from '
                'CUDD function `Cudd_ReadInvPermZdd()`')
        return j

    cpdef python_bool _gt_var_levels(
            self,
            level:
                int):
        """Return `True` if `level` > any variable level.

        Raise `ValueError` if `level < 0`.
        Similar to how `Cudd_ReadInvPermZdd()` works.

        Note that the constant nodes are below all
        variable levels:

        ```python
        import dd.cudd_zdd

        zdd = dd.cudd_zdd.ZDD()
        assert zdd._gt_var_levels(zdd.false.level)
        ```

        Read also `_index_at_level()`

        @param level:
            >= 0
        @return:
            `True` if any CUDD variable has
            level < of given `level`
        """
        if level < 0:
            raise ValueError(
                f'requires `level >= 0`, got:  {level}')
        n_cudd_vars = Cudd_ReadZddSize(self.manager)
        if 0 <= n_cudd_vars <= CUDD_CONST_INDEX:
            return level >= n_cudd_vars
        raise RuntimeError(_tw.dedent(f'''
            Unexpected value: {n_cudd_vars} returned
            from CUDD function `Cudd_ReadZddSize()`
            (0 <= expected <= {CUDD_CONST_INDEX} =
             CUDD_CONST_INDEX)
            '''))

    cpdef int _number_of_cudd_vars(
            self):
        """Return number of CUDD indices.

        Can be `> len(self.vars)`, because CUDD creates
        variable indices also for levels in between
        those of variables declared using `ZDD.declare()`.

        Read also `_index_at_level()`.

        @rtype:
            `int` >= 0
        """
        n_cudd_vars = Cudd_ReadZddSize(self.manager)
        if 0 <= n_cudd_vars <= CUDD_CONST_INDEX:
            return n_cudd_vars
        raise RuntimeError(_tw.dedent(f'''
            Unexpected value: {n_cudd_vars} returned
            from CUDD function `Cudd_ReadZddSize()`
            (0 <= expected <= {CUDD_CONST_INDEX} =
             CUDD_CONST_INDEX)
            '''))

    def reorder(
            self,
            var_order=None):
        """Reorder variables to `var_order`.

        If `var_order` is `None`, then invoke sifting.
        """
        if var_order is None:
            Cudd_zddReduceHeap(self.manager, CUDD_REORDER_SIFT, 1)
            return
        n = len(var_order)
        if n != len(self.vars):
            raise ValueError(
                'Mismatch of variable numbers:\n'
                'the number of declared variables is:  '
                f'{len(self.vars)}\n'
                f'new variable order has length:  {n}')
        cdef int *p
        p = <int *> PyMem_Malloc(n * sizeof(int))
        for var, level in var_order.items():
            index = self._index_of_var[var]
            p[level] = index
        try:
            r = Cudd_zddShuffleHeap(self.manager, p)
        finally:
            PyMem_Free(p)
        if r != 1:
            raise RuntimeError('Failed to reorder.')

    def _enable_reordering(
            self):
        """Enable dynamic reordering of ZDDs."""
        Cudd_AutodynEnableZdd(self.manager, CUDD_REORDER_SIFT)

    def _disable_reordering(
            self):
        """Disable dynamic reordering of ZDDs."""
        Cudd_AutodynDisableZdd(self.manager)

    cpdef set support(
            self,
            u:
                Function):
        """Return `set` of variables that `u` depends on.

        These are the variables that the Boolean function
        represented by the ZDD with root `u` depends on.
        """
        if self.manager != u.manager:
            raise ValueError('`u.manager != self.manager`')
        return _c_support(u)

    cpdef _support_py(
            self,
            u:
                Function):
        # Python implementation
        if self.manager != u.manager:
            raise ValueError('`u.manager != self.manager`')
        visited = set()
        support = set()
        level = 0
        self._support(level, u, support, visited)
        return support

    cdef _support(
            self,
            level,
            u:
                Function,
            support,
            visited):
        """Recurse to compute the support of `u`."""
        # terminal ?
        if u == self.false or self._gt_var_levels(level):
            return
        if u in visited:
            return
        var = self.var_at_level(level)
        u_level, v, w = self.succ(u)
        if level > u_level:
            raise ValueError(level, u_level)
        if level < u_level:
            support.add(var)
            self._support(level + 1, u, support, visited)
        elif v == w:
            self._support(level + 1, v, support, visited)
        else:
            support.add(var)
            self._support(level + 1, v, support, visited)
            self._support(level + 1, w, support, visited)
        visited.add(u)

    cpdef _support_cudd(
            self,
            f:
                Function):
        """Return `set` of variables that node `f` depends on."""
        if self.manager != f.manager:
            raise ValueError('`f.manager != self.manager`')
        r: DdRef
        r = Cudd_zddSupport(self.manager, f.node)
        f = wrap(self, r)
        supp = self._cube_to_dict(f)
        # constant ?
        if not supp:
            return set()
        # must be positive unate
        if set(supp.values()) != {True}:
            raise AssertionError(supp)
        return set(supp)

    def _copy_bdd_vars(
            self,
            bdd):
        """Copy BDD to ZDD variables."""
        Cudd_zddVarsFromBddVars(self.manager, 1)

    def _bdd_to_zdd(
            self,
            u
            ) -> Function:
        """Copy BDD `u` to a ZDD in `self`.

        @param u:
            node in a `dd.cudd.BDD` manager
        @type u:
            `dd.cudd.Function`
        """
        r: DdRef
        bdd = u.bdd
        u_ = bdd.copy(u, self)
        r = <DdNode *>u_.node
        r = Cudd_zddPortFromBdd(self.manager, r)
        return wrap(self, r)

    def copy(
            self,
            u,
            other):
        """Transfer ZDD with root `u` to `other`.

        @param other:
            `ZDD` or `BDD` manager
        @type other:
            | `dd.cudd_zdd.ZDD`
            | `dd.cudd.BDD`
            | `dd.autoref.BDD`
        @rtype:
            | `dd.cudd_zdd.Function`
            | `dd.cudd.Function`
            | `dd.autoref.Function`
        """
        return _copy.copy_zdd(u, other)

    cpdef Function let(
            self,
            definitions:
                dict[str, str] |
                dict[str, python_bool] |
                dict[str, Function],
            u:
                Function):
        """Replace variables with `definitions` in `u`.

        @param definitions:
            maps variable names
            to either:
            - Boolean values, or
            - variable names, or
            - ZDD nodes
        @rtype:
            `Function`
        """
        if self.manager != u.manager:
            raise ValueError('`u.manager != self.manager`')
        d = definitions
        if not d:
            logger.warning(
                'Call to `ZDD.let` with no effect, '
                'because the dictionary `definitions` '
                'is empty.')
            return u
        var = next(iter(d))
        value = d[var]
        if isinstance(value, python_bool):
            return self._cofactor_root(u, d)
        elif isinstance(value, Function):
            # return self._compose_root(u, d)
            return _c_compose(u, d)
        try:
            value + 's'
        except TypeError:
            raise ValueError(
                'Value must be variable name as `str`, '
                'or Boolean value as `bool`, '
                f'or ZDD node as `int`. Got: {value}')
        return self._rename(u, d)

    cpdef Function _cofactor_root(
            self,
            u:
                Function,
            d:
                dict[str, python_bool]):
        """Return cofactor of `u` as defined in `d`.

        @param d:
            maps variable names to Boolean values
        """
        if self.manager != u.manager:
            raise ValueError('`u.manager != self.manager`')
        level = 0
        self.manager.reordered = 1
        while self.manager.reordered == 1:
            cache = dict()
            self.manager.reordered = 0
            try:
                r = self._cofactor(level, u, d, cache)
            except CouldNotCreateNode:
                r = None
        return r

    cpdef Function _cofactor(
            self,
            level:
                int,
            u:
                Function,
            d,
            cache):
        """Recursively compute the cofactor of `u`."""
        # terminal ?
        if u == self.false or self._gt_var_levels(level):
            return u
        t = (u, level)
        if t in cache:
            return cache[t]
        var = self.var_at_level(level)
        i = u.level
        if level > i:
            raise ValueError((level, i))
        if level < i:
            if var in d:
                value = d[var]
                if value:
                    r = self.false
                else:
                    r = self._cofactor(level + 1, u, d, cache)
                r = self.find_or_add(var, r, r)
            else:
                r = self._cofactor(level + 1, u, d, cache)
        else:
            if level != i:
                raise AssertionError((level, i))
            _, v, w = self.succ(u)
            if var in d:
                value = d[var]
                if value:
                    r = self._cofactor(level + 1, w, d, cache)
                else:
                    r = self._cofactor(level + 1, v, d, cache)
                r = self.find_or_add(var, r, r)
            else:
                p = self._cofactor(level + 1, v, d, cache)
                q = self._cofactor(level + 1, w, d, cache)
                r = self.find_or_add(var, p, q)
        cache[t] = r
        return r

    cpdef Function _cofactor_cudd(
            self,
            u:
                Function,
            var:
                str,
            value):
        """CUDD implementation of cofactor."""
        if self.manager != u.manager:
            raise ValueError('`u.manager != self.manager`')
        r: DdRef
        index = self._index_of_var[var]
        if value:
            r = Cudd_zddSubset1(self.manager, u.node, index)
        else:
            r = Cudd_zddSubset0(self.manager, u.node, index)
        return wrap(self, r)

    cpdef Function _compose_root(
            self,
            u:
                Function,
            d):
        """Return the composition defined in `d`.

        @param d:
            `dict` from variable names (`str`)
            to ZDD nodes (`Function`).
        """
        if self.manager != u.manager:
            raise ValueError('`u.manager != self.manager`')
        self.manager.reordered = 1
        while self.manager.reordered == 1:
            cache = dict()
            self.manager.reordered = 0
            try:
                r = self._compose(0, u, d, cache)
            except CouldNotCreateNode:
                r = None
        return r

    cpdef Function _compose(
            self,
            level:
                int,
            u:
                Function,
            d,
            cache):
        """Recursively compute composition of `u`."""
        if level > u.level:
            raise ValueError(
                'requires `level <= u.level`, but: '
                f'{level = } > {u.level = }')
        # terminal ?
        if u == self.false:
            return u
        if self._gt_var_levels(level):
            return self.true  # full ZDDs at output
        t = (u, level)
        if t in cache:
            return cache[t]
        var = self.var_at_level(level)
        u_level = u.level
        if var in d:
            g = d[var]
        else:
            g = self.var(var)
        if level < u_level:
            if level + 1 > u.level:
                raise ValueError(
                    'expected `level + 1 <= u.level`, but '
                    f'{level + 1} = level + 1 > '
                    f'u.level = {u.level}')
            r = self._compose(level + 1, u, d, cache)
            r = self._ite_recursive(g, self.false, r)
        else:
            if level != u.level:
                raise AssertionError(
                    'expected `level == u.level`, but '
                    f'{level} = level != '
                    f'u.level = {u.level}')
            _, v, w = self.succ(u)
            if level + 1 > v.level:
                raise AssertionError(
                    'expected `level + 1 <= v.level`, but '
                    f'{level + 1} = level + 1 > '
                    f'v.level = {v.level}')
            if level + 1 > w.level:
                raise AssertionError(
                    'expected `level + 1 <= w.level`, but '
                    f'{level + 1} = level + 1 > '
                    f'w.level = {w.level}')
            p = self._compose(level + 1, v, d, cache)
            if level + 1 > w.level:
                raise AssertionError(
                    'expected `level + 1 <= w.level`, but '
                    f'{level + 1} = level + 1 > '
                    f'w.level = {w.level}')
            q = self._compose(level + 1, w, d, cache)
            r = self._ite_recursive(g, q, p)
        cache[t] = r
        return r

    cpdef Function _rename(
            self,
            u:
                Function,
            d):
        """Return node from renaming in `u` the variables in `d`."""
        if self.manager != u.manager:
            raise ValueError('`u.manager != self.manager`')
        rename = {k: self.var(v) for k, v in d.items()}
        # return self._compose_root(u, rename)
        return _c_compose(u, rename)

    cpdef Function ite(
            self,
            g:
                Function,
            u:
                Function,
            v:
                Function):
        """Ternary conditional `IF g THEN u ELSE v` for ZDDs.

        Calls `Cudd_zddIte`.
        """
        # for calling `cuddZddIte`
        # read the method `_ite_recursive`
        if g.manager != self.manager:
            raise ValueError('`g.manager != self.manager`')
        if u.manager != self.manager:
            raise ValueError('`u.manager != self.manager`')
        if v.manager != self.manager:
            raise ValueError('`v.manager != self.manager`')
        r: DdRef
        r = Cudd_zddIte(self.manager, g.node, u.node, v.node)
        if r is NULL:
            raise CouldNotCreateNode()
        return wrap(self, r)

    cpdef Function _ite_recursive(
            self,
            g:
                Function,
            u:
                Function,
            v:
                Function):
        """Recursive call to ternary conditional.

        Raises `CouldNotCreateNode` if reordering occurred.
        Calls `cuddZddIte`.
        """
        if g.manager != self.manager:
            raise ValueError('`g.manager != self.manager`')
        if u.manager != self.manager:
            raise ValueError('`u.manager != self.manager`')
        if v.manager != self.manager:
            raise ValueError('`v.manager != self.manager`')
        r: DdRef
        r = cuddZddIte(self.manager, g.node, u.node, v.node)
        if r is NULL:
            raise CouldNotCreateNode()
        return wrap(self, r)

    cpdef find_or_add(
            self,
            var:
                str,
            low:
                Function,
            high:
                Function):
        """Return node `IF var THEN high ELSE low`."""
        if low.manager != self.manager:
            raise ValueError('`low.manager != self.manager`')
        if high.manager != self.manager:
            raise ValueError('`high.manager != self.manager`')
        if var not in self.vars:
            raise ValueError(
                f'undeclared variable: {var}, '
                f'not in: {self.vars}')
        level = self.level_of_var(var)
        if level >= low.level:
            raise ValueError(level, low.level, 'low.level')
        if level >= high.level:
            raise ValueError(level, high.level, 'high.level')
        r: DdRef
        index = self._index_of_var[var]
        if high == self.false:
            r = low.node
        else:
            r = cuddUniqueInterZdd(
                self.manager, index, high.node, low.node)
            if r is NULL:
                raise CouldNotCreateNode()
        f = wrap(self, r)
        if level > f.level:
            raise AssertionError(level, f.level, 'f.level')
        return f

    cdef DdRef _find_or_add(
            self,
            index:
                int,
            low:
                DdRef,
            high:
                DdRef
            ) except NULL:
        """Implementation of method `find_or_add` in C."""
        r: DdRef
        if low is NULL:
            raise AssertionError('`low is NULL`')
        if high is NULL:
            raise AssertionError('`high is NULL`')
        if high == Cudd_ReadZero(self.manager):
            return low
        r = cuddUniqueInterZdd(
            self.manager, index, high, low)
        if r is NULL:
            raise AssertionError('r is NULL')
        return r

    cpdef _top_cofactor(
            self,
            u:
                Function,
            level:
                int):
        """Return cofactor at `level`."""
        u_level = u.level
        if level > u_level:
            raise ValueError((level, u_level))
        if level < u_level:
            return (u, self.false)
        v, w = u.low, u.high
        if v is None:
            raise AssertionError('`v is None`')
        if w is None:
            raise AssertionError('`w is None`')
        return (v, w)

    def count(
            self,
            u:
                Function,
            nvars=None):
        """Return nuber of models of node `u`.

        @param nvars:
            regard `u` as an operator that
            depends on `nvars` many variables.

            If omitted, then assume those in `support(u)`.
        """
        if u.manager != self.manager:
            raise ValueError('nodes from different managers')
        support = self.support(u)
        r = self._count(0, u, support, cache=dict())
        n_support = len(support)
        if nvars == None:
            nvars = n_support
        if nvars < n_support:
            raise ValueError((nvars, n_support))
        return r * 2**(nvars - n_support)

    def _count(
            self,
            level:
                int,
            u:
                Function,
            support,
            cache:
                dict):
        """Recurse to count satisfying assignments."""
        if u == self.false:
            return 0
        if self._gt_var_levels(level):
            return 1
        if u in cache:
            return cache[u]
        v, w = self._top_cofactor(u, level)
        var = self.var_at_level(level)
        if var in support:
            nv = self._count(level + 1, v, support, cache)
            nw = self._count(level + 1, w, support, cache)
            r = nv + nw
        else:
            r = self._count(level + 1, v, support, cache)
        cache[u] = r
        return r

    def _count_cudd(
            self,
            u:
                Function,
            nvars:
                int):
        """CUDD implementation of `self.count`."""
        # returns different results
        if u.manager != self.manager:
            raise ValueError('nodes from different managers')
        n = len(self.support(u))
        if nvars < n:
            raise ValueError((nvars, n))
        r = Cudd_zddCountMinterm(self.manager, u.node, nvars)
        if r == CUDD_OUT_OF_MEM:
            raise RuntimeError('CUDD out of memory')
        if r == float('inf'):
            raise RuntimeError('overflow of integer type double')
        return r

    def pick(
            self,
            u:
                Function,
            care_vars=None):
        """Return a single satisfying assignment as `dict`."""
        return next(self.pick_iter(u, care_vars), None)

    def pick_iter(
            self,
            u:
                Function,
            care_vars=None):
        """Return iterator over satisfying assignments.

        The returned iterator is generator-based.
        """
        if self.manager != u.manager:
            raise ValueError('nodes from different managers')
        support = self.support(u)
        if care_vars is None:
            care_vars = support
        missing = support.difference(care_vars)
        if missing:
            logger.warning(
                'Missing bits:  '
                rf'support \ care_vars = {missing}')
        cube = dict()
        value = True
        config = self.configure(reordering=False)
        level = 0
        for cube in self._sat_iter(level, u, cube, value, support):
            for m in _bdd._enumerate_minterms(cube, care_vars):
                yield m
        self.configure(reordering=config['reordering'])

    def _pick_iter_cudd(
            self,
            u:
                Function,
            care_vars=None):
        """CUDD implementation of `self.pick_iter`."""
        # assigns also to variables outside the support
        if self.manager != u.manager:
            raise ValueError('nodes from different ZDD managers')
        cdef DdGen *gen
        cdef int *path
        cdef double value
        support = self.support(u)
        if care_vars is None:
            care_vars = support
        missing = support.difference(care_vars)
        if missing:
            logger.warning(
                'Missing bits:  '
                rf'support \ care_vars = {missing}')
        config = self.configure(reordering=False)
        gen = Cudd_zddFirstPath(self.manager, u.node, &path)
        if gen is NULL:
            raise RuntimeError('first path failed')
        try:
            r = 1
            while Cudd_IsGenEmpty(gen) == 0:
                if r != 1:
                    raise RuntimeError(
                        f'gen not empty but no next path: {r}')
                d = _path_array_to_dict(path, self._index_of_var)
                if not set(d).issubset(support):
                    raise AssertionError(
                        set(d).difference(support))
                for m in _bdd._enumerate_minterms(d, care_vars):
                    yield m
                r = Cudd_zddNextPath(gen, &path)
        finally:
            Cudd_GenFree(gen)
        self.configure(reordering=config['reordering'])

    def _sat_iter(
            self,
            level,
            u,
            cube,
            value,
            support):
        """Recurse to enumerate models."""
        # terminal ?
        if u == self.false or self._gt_var_levels(level):
            if u != self.false:
                if not set(cube).issubset(support):
                    raise ValueError(
                        set(cube).difference(support))
                yield cube
            return
        # non-terminal
        i, v, w = self.succ(u)
        var = self.var_at_level(level)
        if level > i:
            raise ValueError((level, i))
        if level < i:
            cube[var] = False
            if var not in support:
                raise ValueError((var, support, '<'))
            for x in self._sat_iter(
                    level + 1, u, cube, value, support):
                yield x
        elif v != w:
            if level != i:
                raise AssertionError((level, i))
            if var not in support:
                raise ValueError((var, support, '=='))
            d0 = dict(cube)
            d0[var] = False
            d1 = dict(cube)
            d1[var] = True
            for x in self._sat_iter(
                    level + 1, v, d0, value, support):
                yield x
            for x in self._sat_iter(
                    level + 1, w, d1, value, support):
                yield x
        else:
            if level != i:
                raise AssertionError((level, i))
            if not (v == w):
                raise AssertionError((v, w))
            for x in self._sat_iter(
                    level + 1, v, cube, value, support):
                yield x

    cpdef Function apply(
            self,
            op,
            u:
                Function,
            v:
                Function
                # | None
                =None,
            w:
                Function
                # | None
                =None):
        r"""Return as `Function` the result of applying `op`.

        @type op:
            `str` in
            - `'~'`, `'not'`, `'!'`
              (logical negation)
            - `'/\\'`, `'and'`, `'&'`, `'&&'`
              (conjunction)
            - `'or'`, `r'\/'`, `'|'`, `'||'`
              (disjunction)
            - `'#'`, `'xor'`, `'^'`
              (different values)
            - `'=>'`, `'implies'`, `'->'`
              (logical implication)
            - `'<=>'`, `'equiv'`, `'<->'`
              (logical equivalence)
            - `'ite'`
              (ternary conditional)
            - `r'\A'`, `'forall'`
              (universal quantification)
            - `r'\E'`, `'exists'`
              (existential quantification)
            - `'-'`
              (`a - b` means `a /\ ~ b`)
        """
        if self.manager != u.manager:
            raise ValueError(
                'node `u` is from different ZDD manager')
        if v is not None and self.manager != v.manager:
            raise ValueError(
                'node `v` is from different ZDD manager')
        if w is not None and self.manager != w.manager:
            raise ValueError(
                'node `w` is from different ZDD manager')
        r: DdRef
        neg_node: DdRef
        t: Function
        cdef DdManager *mgr
        mgr = u.manager
        # unary
        r = NULL
        if op in ('~', 'not', '!'):
            if v is not None:
                raise ValueError(
                    f'`v is not None`, but: {v}')
            if w is not None:
                raise ValueError(
                    f'`w is not None`, but: {w}')
            r = Cudd_zddDiff(
                mgr, Cudd_ReadZddOne(mgr, 0), u.node)
        # binary
        elif op in ('and', '/\\', '&', '&&'):
            if w is not None:
                raise ValueError(
                    f'`w is not None`, but: {w}')
            r = Cudd_zddIntersect(mgr, u.node, v.node)
        elif op in ('or', r'\/', '|', '||'):
            if w is not None:
                raise ValueError(
                    f'`w is not None`, but: {w}')
            r = Cudd_zddUnion(mgr, u.node, v.node)
        elif op in ('#', 'xor', '^'):
            if w is not None:
                raise ValueError(
                    f'`w is not None`, but: {w}')
            neg_node = Cudd_zddDiff(
                mgr, Cudd_ReadZddOne(mgr, 0), v.node)
            neg = wrap(self, neg_node)
            r = Cudd_zddIte(mgr, u.node, neg.node, v.node)
        elif op in ('=>', '->', 'implies'):
            if w is not None:
                raise ValueError(
                    f'`w is not None`, but: {w}')
            r = Cudd_zddIte(
                mgr,
                u.node, v.node, Cudd_ReadZddOne(mgr, 0))
        elif op in ('<=>', '<->', 'equiv'):
            if w is not None:
                raise ValueError(
                    f'`w is not None`, but: {w}')
            neg_node = Cudd_zddDiff(
                mgr, Cudd_ReadZddOne(mgr, 0), v.node)
            neg = wrap(self, neg_node)
            r = Cudd_zddIte(mgr, u.node, v.node, neg.node)
        elif op in ('diff', '-'):
            if w is not None:
                raise ValueError(
                    f'`w is not None`, but: {w}')
            r = Cudd_zddDiff(mgr, u.node, v.node)
        elif op in (r'\A', 'forall'):
            if w is not None:
                raise ValueError(
                    f'`w is not None`, but: {w}')
            qvars = self.support(u)
            cube = _dict_to_zdd(qvars, v.zdd)
            r = _forall_root(
                mgr, v.node, cube.node)
        elif op in (r'\E', 'exists'):
            if w is not None:
                raise ValueError(
                    f'`w is not None`, but: {w}')
            qvars = self.support(u)
            cube = _dict_to_zdd(qvars, v.zdd)
            r = _exist_root(
                mgr, v.node, cube.node)
        # ternary
        elif op == 'ite':
            if v is None:
                raise ValueError('`v is None`')
            if w is None:
                raise ValueError('`w is None`')
            r = Cudd_zddIte(mgr, u.node, v.node, w.node)
        else:
            raise ValueError(
                f'unknown operator: "{op}"')
        if r is NULL:
            config = self.configure()
            raise RuntimeError(
                'CUDD appears to have run out of memory.\n'
                f'Computing the operator {op}\n.'
                'Current settings for upper bounds:\n'
                f'    max memory = {config["max_memory"]} bytes\n'
                f'    max cache = {config["max_cache_hard"]} entries')
        res = wrap(self, r)
        return res

    cpdef _add_int(
            self,
            i):
        """Return node from integer `i`."""
        u: DdRef
        if i in (0, 1):
            raise ValueError(
                rf'{i} \in {{0, 1}}')
        # invert `Function.__int__`
        if 2 <= i:
            i -= 2
        u = <DdNode *><stdint.uintptr_t>i
        return wrap(self, u)

    cpdef Function cube(
            self,
            dvars):
        """Return conjunction of variables in `dvars`.

        If `dvars` is a `dict`, then a Boolean value
        `False` results in a negated variable.

        @param dvars:
            `dict` or container of variables
            as `str`
        @rtype:
            `Function`
        """
        r = self.true
        for var in dvars:
            u = self.var(var)
            if isinstance(dvars, dict):
                value = dvars[var]
            else:
                value = True
            if value is True:
                r &= u
            elif value is False:
                r &= ~ u
            else:
                raise ValueError(
                    f'value not Boolean: {value}')
        return r

    cpdef Function _disjoin_root(
            self,
            u:
                Function,
            v:
                Function):
        """Disjoin `u` and `v`."""
        level = 0
        self.manager.reordered = 1
        while self.manager.reordered == 1:
            try:
                self.manager.reordered = 0
                cache = dict()
                r = self._disjoin(level, u, v, cache)
            except CouldNotCreateNode:
                r = None
        return r

    cdef Function _disjoin(
            self,
            level,
            u:
                Function,
            v:
                Function,
            cache):
        """Recursively disjoin `u` and `v`.

        The recursion starts at `level`.
        """
        if u == self.false:
            return v
        if v == self.false:
            return u
        if self._gt_var_levels(level):
            if u.low is not None:
                raise ValueError(
                    (u, u.low, level, self.var_levels))
            if v.low is not None:
                raise ValueError(
                    (v, v.low, level, self.var_levels))
            if u != v:
                raise AssertionError(
                    (level, u, v))
            return u
        t = (u, v)
        if t in cache:
            return cache[t]
        pu, qu = self._top_cofactor(u, level)
        pv, qv = self._top_cofactor(v, level)
        p = self._disjoin(level + 1, pu, pv, cache)
        q = self._disjoin(level + 1, qu, qv, cache)
        var = self.var_at_level(level)
        r = self.find_or_add(var, p, q)
        cache[t] = r
        return r

    cpdef Function _conjoin_root(
            self,
            u:
                Function,
            v:
                Function):
        """Conjoin `u` and `v`."""
        level = 0
        self.manager.reordered = 1
        while self.manager.reordered == 1:
            try:
                self.manager.reordered = 0
                cache = dict()
                r = self._conjoin(level, u, v, cache)
            except CouldNotCreateNode:
                r = None
        return r

    cdef Function _conjoin(
            self,
            level,
            u:
                Function,
            v:
                Function,
            cache):
        """Recursively conjoin `u` and `v`.

        The recursion starts at `level`.
        """
        if u == self.false:
            return u
        if v == self.false:
            return v
        if self._gt_var_levels(level):
            if u.low is not None:
                raise ValueError(
                    (u, u.low, level, self.var_levels))
            if v.low is not None:
                raise ValueError(
                    (v, v.low, level, self.var_levels))
            if u != v:
                raise AssertionError(
                    (level, u, v))
            return u
        t = (u, v)
        if t in cache:
            return cache[t]
        pu, qu = self._top_cofactor(u, level)
        pv, qv = self._top_cofactor(v, level)
        p = self._conjoin(level + 1, pu, pv, cache)
        q = self._conjoin(level + 1, qu, qv, cache)
        var = self.var_at_level(level)
        r = self.find_or_add(var, p, q)
        cache[t] = r
        return r

    cpdef Function quantify(
            self,
            u:
                Function,
            qvars,
            forall=False):
        """Abstract variables `qvars` from node `u`."""
        if u.manager != self.manager:
            raise ValueError('`u.manager != self.manager`')
        # similar to the C implementation
        # return self._quantify_using_cube_root(
        #     u, qvars, forall)

        # implementation that uses a `dict`
        # return self._quantify_root(
        #     u, qvars, forall)

        # C implementation
        r: Function
        if forall:
            r = _c_forall(qvars, u)
        else:
            r = _c_exist(qvars, u)
        return r

    cpdef Function _quantify_root(
            self,
            u:
                Function,
            qvars,
            forall=False):
        """Abstract variables `qvars` in `u`.

        @param u:
            node
        @param qvars:
            `set` of quantified variables
        @param forall:
            if `True`,
            then quantify `qvars` universally,
            else existentially.
        """
        level = 0
        self.manager.reordered = 1
        while self.manager.reordered == 1:
            self.manager.reordered = 0
            cache = dict()
            r = self._quantify(
                level, u, qvars, forall, cache)
        return r

    cpdef Function _quantify_using_cube_root(
            self,
            u:
                Function,
            qvars,
            forall=False):
        """Abstract variables `qvars` in `u`.

        This implementation usses a ZDD to represent
        the set of variables to quantify.
        """
        level = 0
        cube = _dict_to_zdd(qvars, self)
        self.manager.reordered = 1
        while self.manager.reordered == 1:
            self.manager.reordered = 0
            cache = dict()
            r = self._quantify_using_cube(
                level, u, cube, forall, cache)
        return r

    def _quantify_using_cube(
            self,
            level,
            u,
            cube,
            forall,
            cache):
        """Recurse to quantify variables.

        This implementation uses a ZDD to represent
        the set of variables to quantify.
        """
        if u == self.false or self._gt_var_levels(level):
            return u
        t = (u, level)
        if t in cache:
            return cache[t]
        v, w = self._top_cofactor(u, level)
        if cube.low != cube.high:
            raise ValueError((cube, cube.low, cube.high))
        new_cube, _ = self._top_cofactor(cube, level)
        p = self._quantify_using_cube(level + 1, v, new_cube, forall, cache)
        q = self._quantify_using_cube(level + 1, w, new_cube, forall, cache)
        var = self.var_at_level(level)
        if level > cube.level:
            raise ValueError((level, cube, cube.level))
        if level == cube.level:
            if forall:
                r = self._conjoin(
                    level + 1, p, q, dict())
            else:
                r = self._disjoin(
                    level + 1, p, q, dict())
            r = self.find_or_add(var, r, r)
        else:
            r = self.find_or_add(var, p, q)
        cache[t] = r
        return r

    def _quantify(
            self,
            level,
            u,
            qvars,
            forall,
            cache):
        """Recurse to quantify variables."""
        if (level > u.level):
            raise ValueError(
                (level, u.level, u))
        # terminal ?
        if u == self.false or self._gt_var_levels(level):
            return u
        t = (u, level)
        if t in cache:
            r = cache[t]
            if level > r.level:
                raise AssertionError(
                    (level, r.level, r, '= cache[(u, level)]'))
            return r
        v, w = self._top_cofactor(u, level)
        if level >= v.level:
            raise AssertionError((level, v.level, v))
        if level >= w.level:
            raise AssertionError((level, w.level, w))
        p = self._quantify(level + 1, v, qvars, forall, cache)
        q = self._quantify(level + 1, w, qvars, forall, cache)
        if level >= p.level:
            raise AssertionError((level, p.level, p))
        if level >= q.level:
            raise AssertionError((level, q.level, q))
        var = self.var_at_level(level)
        if var in qvars:
            if forall:
                r = self._conjoin(
                    level + 1, p, q, dict())
            else:
                r = self._disjoin(
                    level + 1, p, q, dict())
            r = self.find_or_add(var, r, r)
        else:
            r = self.find_or_add(var, p, q)
        if min(level, u.level) > r.level:
            raise AssertionError(
                (level, u.level, r.level, 'u, r'))
        cache[t] = r
        if level > r.level:
            raise AssertionError((level, r.level, 'r'))
        return r

    def _quantify_optimized(
            self,
            level,
            u,
            qvars,
            forall,
            cache):
        """Recurse to quantify variables."""
        # terminal ?
        if u == self.false or self._gt_var_levels(level):
            return u
        if u in cache:
            return cache[u]
        u_level = u.level
        var = self.var_at_level(level)
        if level < u_level:
            r = self._quantify(
                level + 1, u, qvars, forall, cache)
            if var in qvars:
                r = self.find_or_add(var, r, r)
        else:
            _, v, w = self.succ(u)
            p = self._quantify(
                level + 1, v, qvars, forall, cache)
            q = self._quantify(
                level + 1, w, qvars, forall, cache)
            if var in qvars:
                if forall:
                    r = self._conjoin(
                        level + 1, p, q, dict())
                else:
                    r = self._disjoin(
                        level + 1, p, q, dict())
                r = self.find_or_add(var, r, r)
            else:
                r = self.find_or_add(var, p, q)
        cache[u] = r
        return r

    cpdef Function forall(
            self,
            variables,
            u:
                Function):
        """Quantify `variables` in `u` universally.

        Wraps method `quantify` to be more readable.
        """
        return self.quantify(u, variables, forall=True)

    cpdef Function exist(
            self,
            variables,
            u:
                Function):
        """Quantify `variables` in `u` existentially.

        Wraps method `quantify` to be more readable.
        """
        return self.quantify(u, variables, forall=False)

    cpdef assert_consistent(
            self):
        """Raise `AssertionError` if not consistent."""
        if Cudd_DebugCheck(self.manager) != 0:
            raise AssertionError('`Cudd_DebugCheck` errored')
        n = len(self.vars)
        m = len(self._var_with_index)
        k = len(self._index_of_var)
        if n != m:
            raise AssertionError(
                f'`len(self.vars) == {n}` but '
                f'`len(self._var_with_index) == {m}`\n'
                f'{self.vars = }\n'
                f'{self._var_with_index = }')
        if m != k:
            raise AssertionError(
                f'`len(self._var_with_index) == {m}` but '
                f'`len(self._index_of_var) == {k}`\n'
                f'{self._var_with_index = }\n'
                f'{self._index_of_var = }')
        if set(self.vars) != set(self._index_of_var):
            raise AssertionError(
                '`set(self.vars) != '
                'set(self._index_of_var)`\n'
                f'{self.vars = }\n'
                f'{self._index_of_var = }')
        if set(self._var_with_index) != set(
                self._index_of_var.values()):
            raise AssertionError(
                '`set(self._var_with_index) != '
                'set(self._index_of_var.values())`\n'
                f'{self._var_with_index = }\n'
                f'{self._index_of_var = }')

    def add_expr(
            self,
            expr):
        """Return node for `str` expression `e`."""
        return _parser.add_expr(expr, self)

    cpdef str to_expr(
            self,
            u:
                Function):
        """Return a Boolean expression for node `u`."""
        if u.manager != self.manager:
            raise ValueError('`u.manager != self.manager`')
        cache = dict()
        level = 0
        return self._to_expr(level, u, cache)

    cpdef str _to_expr(
            self,
            level,
            u:
                Function,
            cache:
                dict):
        """Recursively compute an expression."""
        if u == self.false:
            return 'FALSE'
        if self._gt_var_levels(level):
            return 'TRUE'
        if u in cache:
            return cache[u]
        v, w = self._top_cofactor(u, level)
        p = self._to_expr(level + 1, v, cache)
        q = self._to_expr(level + 1, w, cache)
        var = self.var_at_level(level)
        if p == 'FALSE' and q == 'TRUE':
            s = var
        elif p == q:
            s = p
        else:
            s = f'ite({var}, {q}, {p})'
        cache[u] = s
        return s

    cpdef dump(
            self,
            filename:
                str,
            roots:
                list[Function],
            filetype:
                str
                # | None
                =None):
        """Write ZDD as a diagram to file `filename`.

        The file type is inferred from the
        extension (case insensitive),
        unless a `filetype` is explicitly given.

        `filetype` can have the values:

        - `'pdf'` for PDF
        - `'png'` for PNG
        - `'svg'` for SVG

        If `filetype is None`, then `filename`
        must have an extension that matches
        one of the file types listed above.

        Only the ZDD manager nodes that are reachable from the
        ZDD references in `roots` are included in the diagram.

        @param filename:
            file name,
            e.g., `"diagram.pdf"`
        @param roots:
            container of nodes
        """
        if filetype is None:
            name = filename.lower()
            if name.endswith('.pdf'):
                filetype = 'pdf'
            elif name.endswith('.png'):
                filetype = 'png'
            elif name.endswith('.svg'):
                filetype = 'svg'
            else:
                raise ValueError(
                    'cannot infer file type '
                    'from extension of file '
                    f'name "{filename}"')
        if filetype in ('pdf', 'png', 'svg'):
            self._dump_figure(
                roots, filename, filetype)
        else:
            raise ValueError(
                f'unknown file type "{filetype}", '
                'the method `dd.cudd_zdd.ZDD.dump` '
                'supports writing diagrams as '
                'PDF, PNG, or SVG files.')

    def _dump_figure(
            self,
            roots,
            filename,
            filetype,
            **kw):
        """Write BDDs to `filename` as figure."""
        pd = _to_pydot(roots)
        if filetype == 'pdf':
            pd.write_pdf(filename, **kw)
        elif filetype == 'png':
            pd.write_png(filename, **kw)
        elif filetype == 'svg':
            pd.write_svg(filename, **kw)
        else:
            raise ValueError(
                f'Unknown file type of "{filename}"')

    cpdef load(
            self,
            filename):
        raise NotImplementedError()

    # Same with the method `dd.cudd.BDD._cube_to_dict`.
    cpdef _cube_to_dict(
            self,
            f:
                Function):
        """Recurse to collect indices of support variables."""
        if f.manager != self.manager:
            raise ValueError('`f.manager != self.manager`')
        n = self._number_of_cudd_vars()
        cdef int *x
        x = <int *> PyMem_Malloc(n * sizeof(DdNode *))
        try:
            Cudd_BddToCubeArray(self.manager, f.node, x)
            d = _cube_array_to_dict(x, self._index_of_var)
        finally:
            PyMem_Free(x)
        return d

    @property
    def false(
            self):
        """`Function` for Boolean value FALSE.

        Relevant properties:
            `ZDD.true` and `ZDD.true_node`.
        """
        return self._bool(False)

    @property
    def true(
            self):
        """`Function` for Boolean value TRUE.

        Read also the docstring of the
        property `ZDD.true_node`.

        Relevant properties:
            `ZDD.false`, `ZDD.true_node`
        """
        return self._bool(True)

    @property
    def true_node(
            self):
        """Return the constant ZDD node for TRUE.

        Compare with the property `true`,
        for example the value of `ZDD.true.level`
        with the value of `ZDD.true_node.level`,
        after at least one variable has been
        declared:

        ```python
        import dd.cudd_zdd as _zdd

        zdd = _zdd.ZDD()
        zdd.declare('x')
        a = zdd.true.level
        b = zdd.true_node.level
        print(f'level of `zdd.true`:  {a}')
        print(f'level of `zdd.true_node`:  {b}')
        ```

        Relevant properties:
            `ZDD.false`, `ZDD.true`
        """
        r: DdRef
        r = DD_ONE(self.manager)
        return wrap(self, r)

    cdef Function _bool(
            self,
            v):
        """Return terminal node for Boolean `v`."""
        r: DdRef
        if v:
            r = Cudd_ReadZddOne(self.manager, 0)
        else:
            r = Cudd_ReadZero(self.manager)
        return wrap(self, r)


cdef Function wrap(
        bdd:
            ZDD,
        node:
            DdRef):
    """Return a `Function` that wraps `node`."""
    # because `@classmethod` unsupported
    f = Function()
    f.init(node, bdd)
    return f


cdef class Function:
    """Wrapper of ZDD `DdNode` from CUDD.

    For details, read the docstring of the
    class `dd.cudd.Function`.
    """

    __weakref__: object
    cdef public ZDD bdd
    cdef public ZDD zdd
    cdef DdManager *manager
    node: DdRef
    cdef public int _ref

    cdef init(
            self,
            node:
                DdRef,
            zdd:
                ZDD):
        if node is NULL:
            raise ValueError('`DdNode *node` is `NULL` pointer.')
        self.zdd = zdd
        self.bdd = zdd  # keep this attribute for writing
            # common algorithms for BDDs and ZDDs where possible
        self.manager = zdd.manager
        self.node = node
        self._ref = 1  # lower bound on reference count
        Cudd_Ref(node)

    def __hash__(
            self):
        return int(self)

    @property
    def _index(
            self):
        """Index of `self.node`."""
        return Cudd_NodeReadIndex(self.node)

    @property
    def var(
            self):
        """Variable at level where this node is.

        If node is constant, return `None`.
        """
        if cuddIsConstant(self.node):
            return None
        return self.zdd._var_with_index[self._index]

    @property
    def level(
            self):
        """Level where this node currently is."""
        i = self._index
        return Cudd_ReadPermZdd(self.manager, i)

    @property
    def ref(
            self):
        """Reference count of node."""
        return self.node.ref

    @property
    def low(
            self):
        """Return "else" node as `Function`."""
        if cuddIsConstant(self.node):
            return None
        u: DdRef
        # refer to the lines:
        #
        # else if (top_var == level) {
        #     res = cuddE(P);
        #
        # inside the function `zdd_subset0_aux`,
        # in the file `cudd/cuddZddSetop.c`.
        u = cuddE(self.node)
        return wrap(self.zdd, u)

    @property
    def high(
            self):
        """Return "then" node as `Function`."""
        if cuddIsConstant(self.node):
            return None
        u: DdRef
        # refer to the lines:
        #
        # } else if (top_var == level) {
        # res = cuddT(P);
        #
        # inside the function `zdd_subset1_aux`,
        # in file `cudd/cuddZddSetop.c`.
        u = cuddT(self.node)
        return wrap(self.zdd, u)

    @property
    def negated(
            self):
        raise Exception(
            'No complemented edges for ZDDs in CUDD, '
            'only for BDDs.')

    @property
    def support(
            self:
                ZDD):
        """Return `set` of variables in support."""
        return self.zdd.support(self)

    def __dealloc__(
            self):
        # when changing this method,
        # update also the function
        # `_test_call_dealloc` below
        if self._ref < 0:
            raise AssertionError(
                "The lower bound `_ref` on the node's "
                f'reference count has value {self._ref}, '
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
        Cudd_RecursiveDerefZdd(self.manager, self.node)
        # avoid future access to deallocated memory
        self.node = NULL

    def __int__(
            self):
        # inverse is `ZDD._add_int`
        if sizeof(stdint.uintptr_t) != sizeof(DdNode *):
            raise RuntimeError(
                'expected equal pointer sizes')
        i = <stdint.uintptr_t>self.node
        # 0, 1 are true and false in logic syntax
        if 0 <= i:
            i += 2
        if i in (0, 1):
            raise AssertionError(i)
        return i

    def __repr__(
            self):
        return (
            f'<dd.cudd_zdd.Function at {hex(id(self))}, '
            'wrapping a (ZDD) DdNode with '
            f'var index: {self._index}, '
            f'ref count: {self.ref}, '
            f'int repr: {int(self)}>')

    def __str__(
            self):
        return f'@{int(self)}'

    def __len__(
            self):
        # The function `Cudd_zddDagSize`
        # is deprecated because it duplicates
        # the function `Cudd_DagSize`.
        return Cudd_zddDagSize(self.node)

    @property
    def dag_size(
            self):
        """Return number of ZDD nodes.

        This is the number of ZDD nodes that
        are reachable from this ZDD reference,
        i.e., with `self` as root.
        """
        return len(self)

    def __eq__(
            self:
                Function,
            other:
                Function):
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
                Function):
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
                Function):
        if self.manager != other.manager:
            raise ValueError(
                '`self.manager != other.manager`')
        return (other | ~ self) == self.zdd.true

    def __lt__(
            self:
                Function,
            other:
                Function):
        if self.manager != other.manager:
            raise ValueError(
                '`self.manager != other.manager`')
        return (
            self.node != other.node and
            (other | ~ self) == self.zdd.true)

    def __ge__(
            self:
                Function,
            other:
                Function):
        if self.manager != other.manager:
            raise ValueError(
                '`self.manager != other.manager`')
        return (self | ~ other) == self.zdd.true

    def __gt__(
            self:
                Function,
            other:
                Function):
        if self.manager != other.manager:
            raise ValueError(
                '`self.manager != other.manager`')
        return (
            self.node != other.node and
            (self | ~ other) == self.zdd.true)

    def __invert__(
            self):
        r: DdRef
        r = Cudd_zddDiff(
            self.manager,
            Cudd_ReadZddOne(self.manager, 0),
            self.node)
        return wrap(self.zdd, r)

    def __and__(
            self:
                Function,
            other:
                Function):
        if self.manager != other.manager:
            raise ValueError('`self.manager != other.manager`')
        r = Cudd_zddIntersect(self.manager, self.node, other.node)
        return wrap(self.zdd, r)

    def __or__(
            self:
                Function,
            other:
                Function):
        if self.manager != other.manager:
            raise ValueError('`self.manager != other.manager`')
        r = Cudd_zddUnion(self.manager, self.node, other.node)
        return wrap(self.zdd, r)

    def implies(
            self:
                Function,
            other:
                Function):
        if self.manager != other.manager:
            raise ValueError('`self.manager != other.manager`')
        r = Cudd_zddIte(
            self.manager, self.node,
            other.node, Cudd_ReadZddOne(self.manager, 0))
        return wrap(self.zdd, r)

    def equiv(
            self:
                Function,
            other:
                Function):
        return self.zdd.apply('<=>', self, other)

    def let(
            self:
                Function,
            **definitions):
        return self.zdd.let(definitions, self)

    def exist(
            self:
                Function,
            *variables):
        return self.zdd.exist(variables, self)

    def forall(
            self:
                Function,
            *variables):
        return self.zdd.forall(variables, self)

    def pick(
            self:
                Function,
            care_vars=None):
        return self.zdd.pick(self, care_vars)

    def count(
            self:
                Function,
            nvars=None):
        return self.zdd.count(self, nvars)


# Similar to the function `dd.cudd._cube_array_to_dict`
cdef dict _path_array_to_dict(
        int *x,
        index_of_var:
            dict):
    """Return assignment from array of literals `x`."""
    d = dict()
    for var, j in index_of_var.items():
        b = x[j]
        if b == 2:  # absence of ZDD node
            d[var] = False
        elif b == 1:  # "then" arc
            d[var] = True
        elif b == 0:  # "else" arc
            d[var] = False
        else:
            raise ValueError(
                f'unknown polarity: {b}, '
                f'for variable "{var}"')
    return d


# Copy of the function `dd.cudd._cube_array_to_dict`
# TODO: place in a header file, if used in this module
cdef dict _cube_array_to_dict(
        int *x,
        index_of_var:
            dict):
    """Return assignment from array of literals `x`.

    @param x:
        read `dd.cudd._dict_to_cube_array`
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
            raise ValueError(
                f'unknown polarity: {b}, '
                f'for variable "{var}"')
    return d


def to_nx(
        u:
            Function
        ) -> '_utils.MultiDiGraph':
    """Return graph for the ZDD rooted at `u`."""
    _nx = _utils.import_module('networkx')
    g = _nx.MultiDiGraph()
    _to_nx(g, u, umap=dict())
    return g


def _to_nx(
        g,
        u,
        umap):
    """Recursively construct a ZDD graph."""
    u_int = int(u)
    # visited ?
    if u_int in umap:
        return
    u_nd = umap.setdefault(u_int, len(umap))
    if u.var is None:
        label = 'FALSE' if u == u.bdd.false else 'TRUE'
    else:
        label = u.var
    g.add_node(u_nd, label=label)
    if u.var is None:
        return
    v, w = u.low, u.high
    if v is None:
        raise AssertionError(v)
    if w is None:
        raise AssertionError(w)
    v_int = int(v)
    w_int = int(w)
    _to_nx(g, v, umap)
    _to_nx(g, w, umap)
    v_nd = umap[v_int]
    w_nd = umap[w_int]
    g.add_edge(u_nd, v_nd, taillabel='0', style='dashed')
    g.add_edge(u_nd, w_nd, taillabel='1', style='solid')


def _to_pydot(
        roots
        ) -> '_utils.Dot':
    """Return graph for the ZDD rooted at `u`."""
    global _pydot
    _pydot = _utils.import_module('pydot')
    if not roots:
        raise ValueError(
            f'No `roots` given:  {roots}')
    assert roots, roots
    g = _pydot.Dot('zdd', graph_type='digraph')
    # construct graphs
    subgraphs = _add_nodes_for_zdd_levels(g, roots)
    # mapping CUDD ZDD node ID -> node name in `pydot` graph
    umap = dict()
    for u in roots:
        _to_pydot_recurse(
            g, u, umap, subgraphs)
    _add_nodes_for_external_references(
        roots, umap, g, subgraphs[-1])
    return g


def _add_nodes_for_zdd_levels(
        g,
        roots
        ) -> dict:
    """Create nodes and subgraphs for ZDD levels.

    For each level of any ZDD node reachable from `roots`,
    a new node `u_level` and a new subgraph `h_level` are created.
    The node `u_level` is labeled with the level (as numeral),
    and added to the subgraph `h_level`.

    For each pair of consecutive levels in
    `sorted(set of levels of nodes reachable from roots)`,
    an edge is added to graph `g`, pointing from
    the node labeled with the smaller level,
    to the node labeled with the larger level.

    Level `-1` is considered to represent external references
    to ZDD nodes, i.e., instances of the class `Function`.

    The collection of subgraphs (`h_level` above) is returned.

    @return:
        subgraphs (as `pydot.Subgraph`) for
        the ZDD levels of nodes reachable from `roots`,
        as a `dict` that maps each ZDD level to a subgraph
    """
    # mapping level -> var
    level_to_var = _collect_var_levels(roots)
    # add layer for external ZDD references
    level_to_var[-1] = None
    subgraphs = dict()
    level_node_names = list()
    for level in sorted(level_to_var):
        h = _pydot.Subgraph('', rank='same')
        g.add_subgraph(h)
        subgraphs[level] = h
        # add phantom node
        u = f'L{level}'
        level_node_names.append(u)
        if level == -1:
            # layer for external ZDD references
            label = 'ref'
        else:
            # ZDD level
            label = str(level)
        _add_pydot_node(h, u, label=label, shape='none')
    # auxiliary edges for ranking of levels
    a, a1 = _itr.tee(level_node_names)
    next(a1, None)
    for u, v in zip(a, a1):
        _add_pydot_edge(g, u, v, style='invis')
    return subgraphs


def _to_pydot_recurse(
        g:
            '_utils.Dot',
        u:
            Function,
        umap:
            dict,
        subgraphs):
    """Recursively construct a ZDD graph."""
    u_int = int(u)
    # visited ?
    if u_int in umap:
        return
    u_nd = umap.setdefault(u_int, len(umap))
    if u.var is None:
        label = 'FALSE' if u == u.bdd.false else 'TRUE'
    else:
        label = u.var
    h = subgraphs[u.level]
    _add_pydot_node(h, u_nd, label=label)
    if u.var is None:
        return
    v, w = u.low, u.high
    if v is None:
        raise AssertionError(v)
    if w is None:
        raise AssertionError(w)
    v_int = int(v)
    w_int = int(w)
    _to_pydot_recurse(g, v, umap, subgraphs)
    _to_pydot_recurse(g, w, umap, subgraphs)
    v_nd = umap[v_int]
    w_nd = umap[w_int]
    _add_pydot_edge(g, u_nd, v_nd, taillabel='0', style='dashed')
    _add_pydot_edge(g, u_nd, w_nd, taillabel='1', style='solid')


def _add_nodes_for_external_references(
        roots:
            list[Function],
        umap,
        g:
            '_utils.Dot',
        h:
            '_utils.Dot'):
    """Add nodes to `g` that represent the references in `roots`.

    @param roots:
        external references to ZDD nodes
    @param g:
        ZDD graph
    @param h:
        subgraph of `g`
    """
    for u in roots:
        if u is None:
            raise ValueError(u)
        u_int = int(u)
        u_nd = umap[u_int]
        # add node to subgraph at level -1
        ref_nd = f'ref{int(u)}'
        label = f'@{int(u)}'
        _add_pydot_node(h, ref_nd, label=label)
        # add edge from external reference to ZDD node
        _add_pydot_edge(
            g, ref_nd, u_nd,
            style='dashed')


def _add_pydot_node(
        g,
        node_name,
        **kw):
    """Add a node to the `pydot` graph `g`."""
    node = _pydot.Node(name=str(node_name), **kw)
    g.add_node(node)


def _add_pydot_edge(
        g,
        source_node_name,
        target_node_name,
        **kw):
    """Add an edge to the `pydot` graph `g`."""
    edge = _pydot.Edge(
        str(source_node_name),
        str(target_node_name),
        **kw)
    g.add_edge(edge)


def _collect_var_levels(
        roots:
            list[Function]):
    """Add variables and levels reachable from `roots`.

    @param roots:
        container of ZDD nodes
    @return:
        `dict` that maps
        each level (as `int`) to a variable (as `str`),
        only for levels of nodes that are
        reachable from the ZDD node `u`
    """
    level_to_var = dict()
    visited = set()
    for u in roots:
        _collect_var_levels_recurse(
            u, level_to_var, visited)
    return level_to_var


def _collect_var_levels_recurse(
        u:
            Function,
        level_to_var:
            dict[int, str],
        visited:
            set[int]):
    """Recursively collect variables and levels.

    @param level_to_var:
        maps each level to a variable,
        only for levels of nodes that are
        reachable from the ZDD node `u`
    @param visited:
        already visited ZDD nodes
    """
    u_int = int(u)
    if u_int in visited:
        return
    visited.add(u_int)
    level_to_var[u.level] = u.var
    if u.var is None:
        return
    v, w = u.low, u.high
    if v is None:
        raise AssertionError(v)
    if w is None:
        raise AssertionError(w)
    _collect_var_levels_recurse(v, level_to_var, visited)
    _collect_var_levels_recurse(w, level_to_var, visited)


cpdef Function _dict_to_zdd(
        qvars,
        zdd):
    """Return a ZDD that is TRUE over `qvars`.

    This ZDD has nodes at levels of variables in
    `qvars`. Each such node has same low and high.
    """
    levels = {zdd.level_of_var(var) for var in qvars}
    r = zdd.true_node
    for level in sorted(levels, reverse=True):
        var = zdd.var_at_level(level)
        r = zdd.find_or_add(var, r, r)
    return r


cpdef set _cube_to_universe_root(
        cube:
            Function,
        zdd):
    """Map the conjunction `cube` to its support."""
    qvars = set()
    _cube_to_universe(cube, qvars, zdd)
    qvars_ = zdd.support(cube)
    if qvars != qvars_:
        raise AssertionError((qvars, qvars_))
    return qvars


cpdef _cube_to_universe(
        cube:
            Function,
        qvars,
        zdd):
    """Recursively map `cube` to its support."""
    if cube == zdd.false:
        return
    if cube == zdd.true_node:
        return
    if cube.low != cube.high:
        var = cube.var
        qvars.add(var)
        if cube.low != zdd.false:
            raise ValueError((cube, cube.low, len(cube.low)))
    _cube_to_universe(cube.high, qvars, zdd)


cpdef Function _ith_var(
        var,
        zdd):
    """Return ZDD of variable `var`.

    This function requires that declared variables
    have a contiguous range of levels.
    """
    n_declared_vars = len(zdd.vars)
    n_cudd_vars = zdd._number_of_cudd_vars()
    if n_declared_vars > n_cudd_vars:
        # note that `zdd.var_levels()` cannot
        # be called here, because not all declared
        # variables have levels in CUDD, given
        # that `n_declared_vars > n_cudd_vars`
        raise AssertionError(_tw.dedent(f'''
            Found unexpected number of declared variables
            ({n_declared_vars}),
            compared to number of CUDD variable indices
            ({n_cudd_vars}).
            Expected number of declared variables
            <= number of CUDD variable indices.
            The declared variables and their indices are:
                {zdd._index_of_var}
            '''))
    if n_declared_vars != n_cudd_vars:
        counts = _utils.var_counts(zdd)
        contiguous = _utils.contiguous_levels(
            '_ith_var', zdd)
        raise AssertionError(f'{counts}\n{contiguous}')
    level = zdd.level_of_var(var)
    r = zdd.true_node
    for j in range(len(zdd.vars) - 1, -1, -1):
        v = zdd.var_at_level(j)
        if j == level:
            r = zdd.find_or_add(v, zdd.false, r)
        else:
            r = zdd.find_or_add(v, r, r)
    return r


# changes to the function `_c_exist`
# are copied here
cpdef Function _c_forall(
        variables,
        u:
            Function):
    """Universally quantify `variables` in `u`."""
    r: DdRef
    cube = _dict_to_zdd(variables, u.bdd)
    r = _forall_root(u.manager, u.node, cube.node)
    return wrap(u.bdd, r)


# changes to the function `_exist_root`
# are copied here
cdef DdNode *_forall_root(
        DdManager *mgr,
        u:
            DdRef,
        cube:
            DdRef
        ) except NULL:
    r"""Root of recursion for \A."""
    if mgr is NULL:
        raise AssertionError('`mgr is NULL`')
    if u is NULL:
        raise AssertionError('`u is NULL`')
    if cube is NULL:
        raise AssertionError('`cube is NULL`')
    mgr.reordered = 1
    while mgr.reordered == 1:
        mgr.reordered = 0
        r = _forall(mgr, 0, u, cube)
    if r is NULL:
        raise AssertionError('`r is NULL`')
    return r


cdef DdNode *_forall_cache_id(
        DdManager *mgr,
        u:
            DdRef,
        cube:
            DdRef
        ) noexcept:
    """Used only as cache key.

    Passed inside the function `_forall()`
    to the C functions:

    - `cuddCacheLookup2Zdd()`
    - `cuddCacheInsert2()`
    """


# changes to the function `_exist`
# are copied here
cdef DdNode *_forall(
        DdManager *mgr,
        level:
            _c_level,
        u:
            DdRef,
        cube:
            DdRef
        ) except? NULL:
    r"""Recursive \A.

    Asserts that:
    - `level` <= level of `u`
    - `level` <= level of `cube`
    """
    if level < 0:
        raise AssertionError(
            f'`{level = } < 0`')
    if u is NULL:
        raise AssertionError('`u is NULL`')
    if cube is NULL:
        raise AssertionError('`cube is NULL`')
    index = Cudd_ReadInvPermZdd(mgr, level)
    if (u == DD_ZERO(mgr) or
            index == -1 or
            index == CUDD_CONST_INDEX):
        return u
    r = cuddCacheLookup2Zdd(
        mgr, _forall_cache_id, u, cube)
    if r is not NULL:
        return r
    u_index = Cudd_NodeReadIndex(u)
    u_level = Cudd_ReadPermZdd(mgr, u_index)
    cube_index = Cudd_NodeReadIndex(cube)
    cube_level = Cudd_ReadPermZdd(mgr, cube_index)
    if level > u_level:
        raise AssertionError((level, u_level))
    if level > cube_level:
        raise AssertionError((level, cube_level))
    # top cofactor
    if level < u_level:
        v, w = u, DD_ZERO(mgr)
    else:
        v, w = cuddE(u), cuddT(u)
    if level < cube_level:
        new_cube = cube
    else:
        if cuddE(cube) != cuddT(cube):
            raise AssertionError(<int>cube)
        new_cube = cuddE(cube)
    p = _forall(mgr, level + 1, v, new_cube)
    if p is NULL:
        return NULL
    cuddRef(p)
    q = _forall(mgr, level + 1, w, new_cube)
    if q is NULL:
        Cudd_RecursiveDerefZdd(mgr, p)
        return NULL
    cuddRef(q)
    if level == cube_level:
        conj = _conjoin(mgr, level + 1, p, q)
        if conj is NULL:
            Cudd_RecursiveDerefZdd(mgr, p)
            Cudd_RecursiveDerefZdd(mgr, q)
            return NULL
        cuddRef(conj)
        r = _find_or_add(mgr, index, conj, conj)
        Cudd_RecursiveDerefZdd(mgr, conj)
    else:
        r = _find_or_add(mgr, index, p, q)
    if r is NULL:
        Cudd_RecursiveDerefZdd(mgr, p)
        Cudd_RecursiveDerefZdd(mgr, q)
        return NULL
    cuddRef(r)
    Cudd_RecursiveDerefZdd(mgr, p)
    Cudd_RecursiveDerefZdd(mgr, q)
    cuddCacheInsert2(
        mgr, _forall_cache_id, u, cube, r)
    cuddDeref(r)
    return r


cpdef Function _c_exist(
        variables,
        u:
            Function):
    """Existentially quantify `variables` in `u`."""
    r: DdRef
    cube: Function
    cube = _dict_to_zdd(variables, u.bdd)
    r = _exist_root(u.manager, u.node, cube.node)
    return wrap(u.bdd, r)


cdef DdNode *_exist_root(
        DdManager *mgr,
        u:
            DdRef,
        cube:
            DdRef
        ) except NULL:
    r"""Root of recursion for \E."""
    if mgr is NULL:
        raise AssertionError('`mgr is NULL`')
    if u is NULL:
        raise AssertionError('`u is NULL`')
    if cube is NULL:
        raise AssertionError('`cube is NULL`')
    mgr.reordered = 1
    while mgr.reordered == 1:
        mgr.reordered = 0
        r = _exist(mgr, 0, u, cube)
    if r is NULL:
        raise AssertionError('`r is NULL`')
    return r


cdef DdNode *_exist_cache_id(
        DdManager *mgr,
        u:
            DdRef,
        cube:
            DdRef
        ) noexcept:
    """Used only as cache key.

    Passed inside the function `_exist()`
    to the C functions:

    - `cuddCacheLookup2Zdd()`
    -  `cuddCacheInsert2()`
    """


cdef DdNode *_exist(
        DdManager *mgr,
        level:
            _c_level,
        u:
            DdRef,
        cube:
            DdRef
        ) except? NULL:
    r"""Recursive \E.

    Asserts that:
    - `level` <= level of `u`
    - `level` <= level of `cube`
    """
    if level < 0:
        raise AssertionError(
            f'`{level = } < 0`')
    if u is NULL:
        raise AssertionError('`u is NULL`')
    if cube is NULL:
        raise AssertionError('`cube is NULL`')
    index = Cudd_ReadInvPermZdd(mgr, level)
    if (u == DD_ZERO(mgr) or
            index == -1 or
            index == CUDD_CONST_INDEX):
        return u
    r = cuddCacheLookup2Zdd(
        mgr, _exist_cache_id, u, cube)
    if r is not NULL:
        return r
    u_index = Cudd_NodeReadIndex(u)
    u_level = Cudd_ReadPermZdd(mgr, u_index)
    cube_index = Cudd_NodeReadIndex(cube)
    cube_level = Cudd_ReadPermZdd(mgr, cube_index)
    if level > u_level:
        raise AssertionError((level, u_level))
    if level > cube_level:
        raise AssertionError((level, cube_level))
    # top cofactor
    if level < u_level:
        v, w = u, DD_ZERO(mgr)
    else:
        v, w = cuddE(u), cuddT(u)
    if level < cube_level:
        new_cube = cube
    else:
        if cuddE(cube) != cuddT(cube):
            raise AssertionError('expected:  E == T')
        new_cube = cuddE(cube)
    p = _exist(mgr, level + 1, v, new_cube)
    if p is NULL:
        return NULL
    cuddRef(p)
    q = _exist(mgr, level + 1, w, new_cube)
    if q is NULL:
        Cudd_RecursiveDerefZdd(mgr, p)
        return NULL
    cuddRef(q)
    if level > cube_level:
        raise AssertionError((level, cube_level))
    if level == cube_level:
        disj = _disjoin(mgr, level + 1, p, q)
        if disj is NULL:
            Cudd_RecursiveDerefZdd(mgr, p)
            Cudd_RecursiveDerefZdd(mgr, q)
            return NULL
        cuddRef(disj)
        r = _find_or_add(mgr, index, disj, disj)
        Cudd_RecursiveDerefZdd(mgr, disj)
    else:
        r = _find_or_add(mgr, index, p, q)
    if r is NULL:
        Cudd_RecursiveDerefZdd(mgr, p)
        Cudd_RecursiveDerefZdd(mgr, q)
        return NULL
    cuddRef(r)
    Cudd_RecursiveDerefZdd(mgr, p)
    Cudd_RecursiveDerefZdd(mgr, q)
    cuddCacheInsert2(
        mgr, _exist_cache_id, u, cube, r)
    cuddDeref(r)
    return r


cdef DdNode *_find_or_add(
        DdManager *mgr,
        index:
            _c_int,
        v:
            DdRef,
        w:
            DdRef
        ) except? NULL:
    """Find node in table or add new node.

    Calls `cuddUniqueInterZdd` and
    ensures canonicity of ZDDs.

    Returns `NULL` when:
    - memory is exhausted
    - reordering occurred
    - a termination request was detected
    - a timeout expired

    These cases are based on the docstring
    of the CUDD function `cuddUniqueInterZdd()`.
    """
    if mgr is NULL:
        raise AssertionError('`mgr is NULL`')
    if index < 0 or index > CUDD_CONST_INDEX:
        raise AssertionError(
            f'`{index = }`')
    if v is NULL:
        raise AssertionError('`v is NULL`')
    if w is NULL:
        raise AssertionError('`w is NULL`')
    if w == DD_ZERO(mgr):
        return v
    return cuddUniqueInterZdd(mgr, index, w, v)


cpdef Function _c_disjoin(
        u:
            Function,
        v:
            Function):
    """Return the disjunction of `u` and `v`.

    @param u, v:
        ZDD node
    @rtype:
        `Function`
    """
    r: DdRef
    cdef DdManager *mgr
    mgr = u.manager
    r = _disjoin_root(
        mgr, u.node, v.node)
    return wrap(u.bdd, r)


cdef DdNode *_disjoin_root(
        DdManager *mgr,
        u:
            DdRef,
        v:
            DdRef
        ) except NULL:
    """Return the disjunction of `u` and `v`."""
    if mgr is NULL:
        raise AssertionError('`mgr is NULL`')
    if u is NULL:
        raise AssertionError('`u is NULL`')
    if v is NULL:
        raise AssertionError('`v is NULL`')
    mgr.reordered = 1
    while mgr.reordered == 1:
        mgr.reordered = 0
        r = _disjoin(mgr, 0, u, v)
    if r is NULL:
        raise AssertionError('`r is NULL`')
    return r


# This function is used for the hash in cache.
#
# This function exists because
# `except? NULL` cannot be
# used in the signature of the
# function `_disjoin_root()`.
#
# Doing so changes the signature
# in a way that passing `_disjoin_root()`
# to the C function `cuddCacheLookup2Zdd()`
# raises a Cython compilation error.
cdef DdNode *_disjoin_cache_id(
        DdManager *mgr,
        u:
            DdRef,
        v:
            DdRef
        ) noexcept:
    """Used only as cache key.

    Passed inside the function `_disjoin()`
    to the C functions:

    - `cuddCacheLookup2Zdd()`
    - `cuddCacheInsert2()`
    """


# The function `_disjoin()` returns `NULL`
# also in cases that are not due to
# raising an exception.
#
# Those cases are due to reaching the point where
# the tables need to be resized, and reordering
# invoked.
cdef DdNode *_disjoin(
        DdManager *mgr,
        level:
            _c_level,
        u:
            DdRef,
        v:
            DdRef
        ) except? NULL:
    """Recursively disjoin `u` and `v`.

    Asserts that:
    - `level` <= level of `u`
    - `level` <= level of `v`
    """
    # `mgr is not NULL` BY `_disjoin_root()`.
    # `mgr` remains unchanged throughout
    # the recursion, and it is impossible
    # to call `_disjoin()` from Python,
    # so `mgr` not checked here, for efficiency.
    if level < 0:
        raise AssertionError(
            f'`{level = } < 0`')
    if u is NULL:
        raise AssertionError('`u is NULL`')
    if v is NULL:
        raise AssertionError('`v is NULL`')
    index = Cudd_ReadInvPermZdd(mgr, level)
    # TODO: review reference counting
    if u == DD_ZERO(mgr):
        return v
    if v == DD_ZERO(mgr):
        return u
    if index == -1 or index == CUDD_CONST_INDEX:
        if u != DD_ONE(mgr):
            raise AssertionError(
                'nonconstant node `u` given, '
                f'when given level:  {level}, '
                f'with index:  {index}')
        if v != DD_ONE(mgr):
            raise AssertionError(
                'nonconstant node `v` given, '
                f'when given level:  {level}, '
                f'with index:  {index}')
        return u
    r = cuddCacheLookup2Zdd(
        mgr, _disjoin_cache_id, u, v)
    if r is not NULL:
        return r
    u_index = Cudd_NodeReadIndex(u)
    u_level = Cudd_ReadPermZdd(mgr, u_index)
    v_index = Cudd_NodeReadIndex(v)
    v_level = Cudd_ReadPermZdd(mgr, v_index)
    if level > u_level:
        raise AssertionError((level, u_level))
    if level > v_level:
        raise AssertionError((level, v_level))
    if level < u_level:
        pu, qu = u, DD_ZERO(mgr)
    else:
        pu, qu = cuddE(u), cuddT(u)
    if level < v_level:
        pv, qv = v, DD_ZERO(mgr)
    else:
        pv, qv = cuddE(v), cuddT(v)
    p = _disjoin(mgr, level + 1, pu, pv)
    if p is NULL:
        return NULL
    cuddRef(p)
    q = _disjoin(mgr, level + 1, qu, qv)
    if q is NULL:
        Cudd_RecursiveDerefZdd(mgr, p)
        return NULL
    cuddRef(q)
    r = _find_or_add(mgr, index, p, q)
    if r is NULL:
        Cudd_RecursiveDerefZdd(mgr, p)
        Cudd_RecursiveDerefZdd(mgr, q)
        return NULL
    cuddRef(r)
    Cudd_RecursiveDerefZdd(mgr, p)
    Cudd_RecursiveDerefZdd(mgr, q)
    cuddCacheInsert2(
        mgr, _disjoin_cache_id, u, v, r)
    cuddDeref(r)
    return r


cpdef Function _c_conjoin(
        u:
            Function,
        v:
            Function):
    """Return the conjunction of `u` and `v`.

    @param u, v:
        ZDD node
    @rtype:
        `Function`
    """
    r: DdRef
    cdef DdManager *mgr
    mgr = u.manager
    r = _conjoin_root(
        mgr, u.node, v.node)
    return wrap(u.bdd, r)


cdef DdNode *_conjoin_root(
        DdManager *mgr,
        u:
            DdRef,
        v:
            DdRef
        ) except NULL:
    """Return the conjunction of `u` and `v`."""
    if mgr is NULL:
        raise AssertionError('`mgr is NULL`')
    if u is NULL:
        raise AssertionError('`u is NULL`')
    if v is NULL:
        raise AssertionError('`v is NULL`')
    mgr.reordered = 1
    while mgr.reordered == 1:
        mgr.reordered = 0
        r = _conjoin(mgr, 0, u, v)
    if r is NULL:
        raise AssertionError('`r is NULL`')
    return r


# Similar to function `_disjoin_cache_id()`.
# This function is used for the hash in cache.
cdef DdNode *_conjoin_cache_id(
        DdManager *mgr,
        u:
            DdRef,
        v:
            DdRef
        ) noexcept:
    """Used only as cache key.

    Passed inside the function `_conjoin()`
    to the C functions:

    - `cuddCacheLookup2Zdd()`
    - `cuddCacheInsert2()`
    """


cdef DdNode *_conjoin(
        DdManager *mgr,
        level:
            _c_level,
        u:
            DdRef,
        v:
            DdRef
        ) except? NULL:
    """Recursively conjoin `u` and `v`.

    Asserts that:
    - `level` <= level of `u`
    - `level` <= level of `v`
    """
    if level < 0:
        raise AssertionError(
            f'`{level = } < 0`')
    if u is NULL:
        raise AssertionError('`u is NULL`')
    if v is NULL:
        raise AssertionError('`v is NULL`')
    index = Cudd_ReadInvPermZdd(mgr, level)
    if u == DD_ZERO(mgr):
        return u
    if v == DD_ZERO(mgr):
        return v
    if index == -1 or index == CUDD_CONST_INDEX:
        if u != DD_ONE(mgr):
            raise AssertionError(
                'nonconstant node `u` given, '
                f'when given level:  {level}, '
                f'with index:  {index}')
        if v != DD_ONE(mgr):
            raise AssertionError(
                'nonconstant node `v` given, '
                f'when given level:  {level}, '
                f'with index:  {index}')
        return u
    r = cuddCacheLookup2Zdd(
        mgr, _conjoin_cache_id, u, v)
    if r is not NULL:
        return r
    u_index = Cudd_NodeReadIndex(u)
    u_level = Cudd_ReadPermZdd(mgr, u_index)
    v_index = Cudd_NodeReadIndex(v)
    v_level = Cudd_ReadPermZdd(mgr, v_index)
    if level > u_level:
        raise AssertionError((level, u_level))
    if level > v_level:
        raise AssertionError((level, v_level))
    if level < u_level:
        pu, qu = u, DD_ZERO(mgr)
    else:
        pu, qu = cuddE(u), cuddT(u)
    if level < v_level:
        pv, qv = v, DD_ZERO(mgr)
    else:
        pv, qv = cuddE(v), cuddT(v)
    p = _conjoin(mgr, level + 1, pu, pv)
    if p is NULL:
        return NULL
    cuddRef(p)
    q = _conjoin(mgr, level + 1, qu, qv)
    if q is NULL:
        Cudd_RecursiveDerefZdd(mgr, p)
        return NULL
    cuddRef(q)
    r = _find_or_add(mgr, index, p, q)
    if r is NULL:
        Cudd_RecursiveDerefZdd(mgr, p)
        Cudd_RecursiveDerefZdd(mgr, q)
        return NULL
    cuddRef(r)
    Cudd_RecursiveDerefZdd(mgr, p)
    Cudd_RecursiveDerefZdd(mgr, q)
    cuddCacheInsert2(
        mgr, _conjoin_cache_id, u, v, r)
    cuddDeref(r)
    return r


cpdef Function _c_compose(
        u:
            Function,
        dvars:
            dict[str, Function]):
    """Compute composition of `u` with `dvars`.

    @param dvars:
        maps variable names to ZDD nodes
    """
    r: DdRef
    cdef DdManager *mgr
    g: Function
    mgr = u.manager
    zdd = u.bdd
    n_declared_vars = len(zdd.vars)
    n_cudd_vars = zdd._number_of_cudd_vars()
    if n_declared_vars != n_cudd_vars:
        counts = _utils.var_counts(zdd)
        contiguous = _utils.contiguous_levels(
            '_c_compose', zdd)
        raise AssertionError(f'{counts}\n{contiguous}')
    # convert `dvars` to `DdNode **`
    cdef DdNode **vector
    vector = <DdNode **> PyMem_Malloc(
        n_cudd_vars * sizeof(DdNode *))
    for var in zdd.vars:
        i = zdd._index_of_var[var]
        if var in dvars:
            g = dvars[var]
        else:
            g = zdd.var(var)
        cuddRef(g.node)
        if g.ref <= 0:
            raise AssertionError((var, g.ref))
        vector[i] = g.node
    # compose
    r = NULL
    try:
        r = _compose_root(mgr, u.node, vector)
    finally:
        if r is not NULL:
            cuddRef(r)
            if r.ref <= 0:
                raise AssertionError(r.ref)
        for i in range(n_cudd_vars):
            Cudd_RecursiveDerefZdd(mgr, vector[i])
        if r is not NULL:
            cuddDeref(r)
        PyMem_Free(vector)
    if r is NULL:
        raise AssertionError('r is NULL')
    return wrap(u.bdd, r)


cdef DdNode *_compose_root(
        DdManager *mgr,
        u:
            DdRef,
        DdNode **vector
        ) except NULL:
    """Root of recursive composition."""
    if mgr is NULL:
        raise AssertionError('`mgr is NULL`')
    if u is NULL:
        raise AssertionError('`u is NULL`')
    if vector is NULL:
        raise AssertionError('`vector is NULL`')
    r: DdRef
    level = 0
    mgr.reordered = 1
    while mgr.reordered == 1:
        mgr.reordered = 0
        table = dict()
        # table = cuddHashTableInit(mgr, 1, 2)
        # if table is NULL:
        #     return NULL
        r = _compose(mgr, level, table, u, vector)
        # if mgr.reordered == 1:
        #     if r is not NULL:
        #         raise AssertionError(r)
        if r is not NULL:
            cuddRef(r)
            if r.ref <= 0:
                raise AssertionError(r.ref)
        # cuddHashTableQuitZdd(table)
        for nd in table.values():
            Cudd_RecursiveDerefZdd(mgr,
                <DdNode *><stdint.uintptr_t>nd)
        if r is not NULL:
            cuddDeref(r)
    if r is NULL:
        raise AssertionError('`r is NULL`')
    return r


cdef DdNode *_compose(
        DdManager *mgr,
        level:
            _c_level,
        # DdHashTable *table,
        table:
            dict,
        u:
            DdRef,
        DdNode **vector
        ) except? NULL:
    """Recursively compute composition.

    The composition is defined in the
    array `vector`.

    Asserts that:
    - `level` <= level of `u`
    """
    if level < 0:
        raise AssertionError(
            f'`{level = } < 0`')
    if u is NULL:
        raise AssertionError('`u is NULL`')
    if vector is NULL:
        raise AssertionError('`vector is NULL`')
    if u == DD_ZERO(mgr):
        return u
    if u == DD_ONE(mgr):
        r = Cudd_ReadZddOne(mgr, 0)
        if r is NULL:
            raise AssertionError(
                '`Cudd_ReadZddOne()` returned `NULL`.')
        return r
    t = (<stdint.uintptr_t>u, level)
    if t in table:
        return <DdNode *><stdint.uintptr_t>table[t]
    # r = cuddHashTableLookup1(table, u)
    # if r is not NULL:
    #     return r
    u_index = Cudd_NodeReadIndex(u)
    u_level = Cudd_ReadPermZdd(mgr, u_index)
    if level > u_level:
        raise AssertionError((level, u_level))
    index = Cudd_ReadInvPermZdd(mgr, level)
    g = vector[index]
    if g is NULL:
        raise AssertionError('`g is NULL`')
    if g.ref <= 0:
        raise AssertionError((index, g.ref))
    if level < u_level:
        if level + 1 > u_level:
            raise AssertionError((level, u_level))
        c = _compose(
            mgr, level + 1, table, u, vector)
        if c is NULL:
            return NULL
        cuddRef(c)
        if c.ref <= 0:
            raise AssertionError(c.ref)
        r = cuddZddIte(mgr, g, DD_ZERO(mgr), c)
        if r is NULL:
            Cudd_RecursiveDerefZdd(mgr, c)
            return NULL
        cuddRef(r)
        if r.ref <= 0:
            raise AssertionError(r.ref)
        Cudd_RecursiveDerefZdd(mgr, c)
    else:
        if level != u_level:
            raise AssertionError((level, u_level))
        v, w = cuddE(u), cuddT(u)
        if v.ref <= 0:
            raise AssertionError(v.ref)
        if w.ref <= 0:
            raise AssertionError(w.ref)
        p = _compose(
            mgr, level + 1, table, v, vector)
        if p is NULL:
            return NULL
        cuddRef(p)
        if p.ref <= 0:
            raise AssertionError(p.ref)
        q = _compose(
            mgr, level + 1, table, w, vector)
        if q is NULL:
            Cudd_RecursiveDerefZdd(mgr, p)
            return NULL
        cuddRef(q)
        if q.ref <= 0:
            raise AssertionError(q.ref)
        r = cuddZddIte(mgr, g, q, p)
        if r is NULL:
            Cudd_RecursiveDerefZdd(mgr, q)
            Cudd_RecursiveDerefZdd(mgr, p)
            return NULL
        cuddRef(r)
        if r.ref <= 0:
            raise AssertionError(r.ref)
        Cudd_RecursiveDerefZdd(mgr, p)
        Cudd_RecursiveDerefZdd(mgr, q)
    # insert in the hash table
    cuddRef(r)
    table[t] = <stdint.uintptr_t>r
    # fanout = <ptrint> u.ref
    # tr = cuddHashTableInsert1(table, u, r, fanout)
    # if tr == 0:
    #     Cudd_RecursiveDerefZdd(mgr, r)
    #     return NULL
    cuddDeref(r)
    return r


# This function is similar to `cuddHashTableQuit`.
cdef bint cuddHashTableQuitZdd(
        DdHashTable * hash
        ) except False:
    """Shutdown a hash table.

    This function calls `Cudd_RecursiveDerefZdd()`.
    The function `cuddHashTableQuit()` calls
    `Cudd_RecursiveDeref()`.
    """
    if hash is NULL:
        raise AssertionError('`hash is NULL`')
    cdef unsigned int i;
    cdef DdManager *dd = hash.manager;
    cdef DdHashItem *bucket;
    cdef DdHashItem **memlist
    cdef DdHashItem **nextmem;
    cdef unsigned int numBuckets = hash.numBuckets;
    for i in range(numBuckets):
        bucket = hash.bucket[i]
        while bucket is not NULL:
            Cudd_RecursiveDerefZdd(dd, bucket.value)
            bucket = bucket.next
    memlist = hash.memoryList
    while (memlist is not NULL):
        nextmem = <DdHashItem **> memlist[0]
        FREE(memlist)
        memlist = nextmem
    FREE(hash.bucket)
    FREE(hash)
    return True


cpdef set _c_support(
        u:
            Function):
    """Compute support of `u`.

    @param u:
        ZDD node
    @rtype:
        `set`
    """
    zdd = u.bdd
    n = max(zdd._var_with_index) + 1
    cdef int *support
    support = <int *> PyMem_Malloc(n * sizeof(int))
    for i in range(n):
        support[i] = 0
    try:
        level = 0
        if u.manager is NULL:
            raise AssertionError('`u.manager is NULL`')
        _support(u.manager, level, Cudd_Regular(u.node), support)
        _clear_markers(Cudd_Regular(u.node))
        support_vars = set()
        for i in range(n):
            if support[i] == 1:
                var = zdd._var_with_index[i]
                support_vars.add(var)
    finally:
        PyMem_Free(support)
    return support_vars


cdef bint _support(
        DdManager *mgr,
        level:
            _c_level,
        u:
            DdRef,
        int *support
        ) except False:
    """Recursively compute the support."""
    if level < 0:
        raise AssertionError(
            f'`{level = } < 0`')
    if u is NULL:
        raise AssertionError('`u is NULL`')
    if support is NULL:
        raise AssertionError('`support is NULL`')
    index = Cudd_ReadInvPermZdd(mgr, level)
    # terminal ?
    if (u == DD_ZERO(mgr) or
            index == -1 or
            index == CUDD_CONST_INDEX):
        return True
    # visited ?
    if Cudd_IsComplement(u.next):
        return True
    u_index = Cudd_NodeReadIndex(u)
    u_level = Cudd_ReadPermZdd(mgr, u_index)
    if level > u_level:
        raise AssertionError((level, u_level))
    v, w = Cudd_Regular(cuddE(u)), cuddT(u)
    if level < u_level:
        support[index] = 1
        _support(mgr, level + 1, u, support)
    elif v == w:
        _support(mgr, level + 1, v, support)
    else:
        support[index] = 1
        _support(mgr, level + 1, v, support)
        _support(mgr, level + 1, w, support)
    u.next = Cudd_Not(u.next)
    return True


cdef bint _clear_markers(
        u:
            DdRef
        ) except False:
    """Recursively clear complementation bits."""
    if u is NULL:
        raise AssertionError('`u is NULL`')
    if not Cudd_IsComplement(u.next):
        return True
    u.next = Cudd_Regular(u.next)
    if cuddIsConstant(u):
        return True
    v, w = Cudd_Regular(cuddE(u)), cuddT(u)
    _clear_markers(v)
    _clear_markers(w)
    return True


cpdef _test_call_dealloc(
        u:
            Function):
    """Duplicates the code of `Function.__dealloc__`.

    For details read the docstring of the function
    `dd.cudd._test_call_dealloc`.
    """
    self = u
    # the code of `Function.__dealloc__` follows:
    if self._ref < 0:
        raise AssertionError(
            "The lower bound `_ref` on the node's "
            f'reference count has value {self._ref}, '
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
    Cudd_RecursiveDerefZdd(self.manager, self.node)
    # avoid future access to deallocated memory
    self.node = NULL


cpdef _call_method_disjoin(
        zdd:
            ZDD,
        level:
            int,
        u:
            Function,
        v:
            Function,
        cache):
    """Wrapper of method `ZDD._disjoin()`.

    To enable testing the `cdef` method from Python.
    """
    return zdd._disjoin(level, u, v, cache)


cpdef _call_method_conjoin(
        zdd:
            ZDD,
        level:
            int,
        u:
            Function,
        v:
            Function,
        cache):
    """Wrapper of method `ZDD._conjoin()`.

    Similar to `_call_method_disjoin()`.
    """
    return zdd._conjoin(level, u, v, cache)


cpdef _call_disjoin(
        level:
            int,
        u:
            Function,
        v:
            Function):
    """Wrapper of function `_disjoin()`.

    To enable testing the `cdef` function from Python.
    """
    r = _disjoin(
        u.bdd.manager,
        level,
        u.node,
        v.node)
    return wrap(u.bdd, r)


cpdef _call_conjoin(
        level:
            int,
        u:
            Function,
        v:
            Function):
    """Wrapper of function `_conjoin()`.

    Similar to the function `_call_disjoin()`.
    """
    r = _conjoin(
        u.bdd.manager,
        level,
        u.node,
        v.node)
    return wrap(u.bdd, r)
