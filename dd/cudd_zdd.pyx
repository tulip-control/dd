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
    http://vlsi.colorado.edu/~fabio/
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
import logging
import warnings

from dd import _copy
from dd import _parser
from dd import _utils
from dd import bdd as _bdd
from libcpp cimport bool
from libc.stdio cimport FILE, fdopen, fopen, fclose
from libc cimport stdint
from cpython cimport bool as python_bool
from cpython.mem cimport PyMem_Malloc, PyMem_Free
import psutil
# inline:
# import networkx


IF USE_CYSIGNALS:
    from cysignals.signals cimport sig_on, sig_off
ELSE:
    # for non-POSIX systems
    noop = lambda: None
    sig_on = noop
    sig_off = noop


cdef extern from 'cuddInt.h':
    cdef char* CUDD_VERSION
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
        DdNode **univ
        int reordered
    # local hash tables
    ctypedef stdint.intptr_t ptrint
    cdef struct DdHashItem:
        DdHashItem *next
        DdNode *value
    cdef struct DdHashTable:
        DdHashItem **bucket
        DdHashItem **memoryList
        unsigned int numBuckets
        DdManager *manager
    cdef DdHashTable * cuddHashTableInit(
        DdManager *manager,
        unsigned int keySize,
        unsigned int initSize)
    cdef void cuddHashTableQuit(DdHashTable *hash)
    cdef int cuddHashTableInsert1(
        DdHashTable *hash, DdNode *f,
        DdNode *value, ptrint count)
    cdef DdNode * cuddHashTableLookup1(
        DdHashTable *hash, DdNode *f)
    # cache
    cdef DdNode * cuddCacheLookup2Zdd(
        DdManager *table,
        DdNode * (*)(DdManager *, DdNode *, DdNode *),
        DdNode *f,
        DdNode *g)
    cdef void cuddCacheInsert2(
        DdManager *table,
        DdNode * (*)(DdManager *, DdNode *, DdNode *),
        DdNode *f,
        DdNode *g,
        DdNode *data)
    # node elements
    cdef DdNode *cuddUniqueInter(
        DdManager *unique, int index, DdNode *T, DdNode *E)
    cdef DdNode * cuddUniqueInterZdd(
        DdManager *unique, int index, DdNode *T, DdNode *E)
    cdef bool cuddIsConstant(DdNode *u)
    cdef DdNode *DD_ZERO(DdManager *mgr)
    cdef DdNode *DD_ONE(DdManager *mgr)
    cdef DdNode *cuddT(DdNode *u)  # top cofactors
    cdef DdNode *cuddE(DdNode *u)
    # BDD node elements
    cdef DdNode *Cudd_Not(DdNode *dd)
    cdef DdNode *Cudd_Regular(DdNode *u)
    cdef bool Cudd_IsComplement(DdNode *u)
    # reference counting
    cdef void cuddRef(DdNode *u)
    cdef void cuddDeref(DdNode *u)
    # recursive ITE
    cdef DdNode * cuddZddIte(
        DdManager *dd, DdNode *f, DdNode *g, DdNode *h)
    # realignment
    cdef int Cudd_zddRealignmentEnabled(DdManager *unique)
    cdef void Cudd_zddRealignEnable(DdManager *unique)
    cdef void Cudd_zddRealignDisable(DdManager *unique)
    cdef int Cudd_bddRealignmentEnabled(DdManager *unique)
    cdef void Cudd_bddRealignEnable(DdManager *unique)
    cdef void Cudd_bddRealignDisable(DdManager *unique)
cdef extern from 'cudd.h':
    # node
    ctypedef unsigned int DdHalfWord
    cdef struct DdNode:
        DdHalfWord index
        DdHalfWord ref
        DdNode *next
    # manager
    cdef DdManager *Cudd_Init(
        unsigned int numVars,
        unsigned int numVarsZ,
        unsigned int numSlots,
        unsigned int cacheSize,
        size_t maxMemory)
    # generator
    cdef struct DdGen
    # variables
    cdef DdNode *Cudd_zddIthVar(DdManager *dd, int i)
    cdef DdNode *Cudd_bddIthVar(DdManager *dd, int i)
    cdef DdNode *Cudd_zddSupport(DdManager *dd, DdNode *f)
    cdef int Cudd_ReadPermZdd(DdManager *dd, int i)
    cdef int Cudd_ReadInvPermZdd(DdManager *dd, int i)
    cdef unsigned int Cudd_NodeReadIndex(DdNode *u)
    # cofactors (of any given `var`, not only top)
    cdef DdNode *Cudd_zddSubset1(DdManager *dd, DdNode *P, int var)
    cdef DdNode *Cudd_zddSubset0(DdManager *dd, DdNode *P, int var)
    # conversions between BDDs and ZDDs
    cdef int Cudd_zddVarsFromBddVars(DdManager *dd, int multiplicity)
    cdef DdNode *Cudd_zddPortFromBdd(DdManager *dd, DdNode *B)
    cdef DdNode *Cudd_zddPortToBdd(DdManager *dd, DdNode *f)
    # propositional operators
    cdef DdNode *Cudd_zddIte(DdManager *dd, DdNode *f, DdNode *g, DdNode *h)
    cdef DdNode *Cudd_zddUnion(DdManager *dd, DdNode *P, DdNode *Q)
    cdef DdNode *Cudd_zddIntersect(DdManager *dd, DdNode *P, DdNode *Q)
    cdef DdNode *Cudd_zddDiff(DdManager *dd, DdNode *P, DdNode *Q)
    # constants
    cdef DdNode *Cudd_ReadZddOne(DdManager *dd, int i)
        # `i` is the index of the topmost variable
    cdef DdNode *Cudd_ReadZero(DdManager *dd)
    # counting
    cdef int Cudd_zddDagSize(DdNode *p_node)
    cdef double Cudd_zddCountMinterm(DdManager *zdd, DdNode *node, int path)
    cdef int Cudd_zddCount(DdManager *zdd, DdNode *P)
    cdef int Cudd_BddToCubeArray(DdManager *dd, DdNode *cube, int *array)
    # pick
    cdef DdGen *Cudd_zddFirstPath(
        DdManager *zdd, DdNode *f, int **path)
    cdef int Cudd_zddNextPath(DdGen *gen, int **path)
    cdef int Cudd_IsGenEmpty(DdGen *gen)
    cdef int Cudd_GenFree(DdGen *gen)
    # info
    cdef int Cudd_PrintInfo(DdManager *dd, FILE *fp)
    cdef int Cudd_ReadZddSize(DdManager *dd)
    cdef long Cudd_zddReadNodeCount(DdManager *dd)
    cdef long Cudd_ReadPeakNodeCount(DdManager *dd)
    cdef int Cudd_ReadPeakLiveNodeCount(DdManager *dd)
    cdef size_t Cudd_ReadMemoryInUse(DdManager *dd)
    cdef unsigned int Cudd_ReadSlots(DdManager *dd)
    cdef double Cudd_ReadUsedSlots(DdManager *dd)
    cdef double Cudd_ExpectedUsedSlots(DdManager *dd)
    cdef unsigned int Cudd_ReadCacheSlots(DdManager *dd)
    cdef double Cudd_ReadCacheUsedSlots(DdManager *dd)
    cdef double Cudd_ReadCacheLookUps(DdManager *dd)
    cdef double Cudd_ReadCacheHits(DdManager *dd)
    # reordering
    ctypedef enum Cudd_ReorderingType:
        pass
    cdef void Cudd_AutodynEnableZdd(
        DdManager *unique, Cudd_ReorderingType method)
    cdef void Cudd_AutodynDisableZdd(DdManager *unique)
    cdef int Cudd_ReorderingStatusZdd(
        DdManager *unique, Cudd_ReorderingType *method)
    cdef int Cudd_zddReduceHeap(
        DdManager *table,
        Cudd_ReorderingType heuristic,
        int minsize)
    cdef int Cudd_zddShuffleHeap(DdManager *table, int *permutation)
    cdef void Cudd_SetSiftMaxSwap(DdManager *dd, int sms)
    cdef int Cudd_ReadSiftMaxSwap(DdManager *dd)
    cdef void Cudd_SetSiftMaxVar(DdManager *dd, int smv)
    cdef int Cudd_ReadSiftMaxVar(DdManager *dd)
    # The function `Cudd_zddReduceHeap` increments the
    # counter `dd->reorderings`. The function `Cudd_ReadReorderings`
    # reads this counter.
    cdef unsigned int Cudd_ReadReorderings(DdManager *dd)
    # The function `Cudd_zddReduceHeap` adds to the attribute
    # `dd->reordTime`. The function `Cudd_ReadReorderingTime`
    # reads this attribute.
    cdef long Cudd_ReadReorderingTime(DdManager *dd)
    # manager config
    cdef size_t Cudd_ReadMaxMemory(DdManager *dd)
    cdef size_t Cudd_SetMaxMemory(DdManager *dd,
                                size_t maxMemory)
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
    # reference counting
    cdef void Cudd_Ref(DdNode *n)
    cdef void Cudd_Deref(DdNode *n)
    cdef void Cudd_RecursiveDerefZdd(DdManager *table, DdNode *n)
    cdef int Cudd_CheckZeroRef(DdManager *manager)
    # checks
    cdef int Cudd_DebugCheck(DdManager *table)
    cdef void Cudd_Quit(DdManager *unique)
    # manager config
    cdef void Cudd_EnableGarbageCollection(DdManager *dd)
    cdef void Cudd_DisableGarbageCollection(DdManager *dd)
    cdef int Cudd_GarbageCollectionEnabled(DdManager * dd)
    # BDD functions
    cdef DdNode *Cudd_bddIte(DdManager *dd, DdNode *f,
                             DdNode *g, DdNode *h)
cdef extern from 'util.h':
    void FREE(void *ptr)

    # node elements
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


cdef class ZDD(object):
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

    def __cinit__(self,
                  memory_estimate=None,
                  initial_cache_size=None):
        """Initialize ZDD manager.

        @param memory_estimate: maximum allowed memory, in bytes.
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
        logger.info('Using CUDD v{n}'.format(n=__version__))
        self.configure(reordering=True, max_cache_hard=MAX_CACHE)
        self.vars = set()
        self._index_of_var = dict()  # map: str -> unique fixed int
        self._var_with_index = dict()

    def __dealloc__(self):
        n = len(self)
        if n != 0:
            raise AssertionError((
                'Still {n} nodes '
                'referenced upon shutdown.'
                ).format(n=n))
        Cudd_Quit(self.manager)

    def __richcmp__(ZDD self, ZDD other, op):
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
            raise Exception('Only `__eq__` and `__ne__` defined')

    def __len__(self):
        """Return number of nodes with non-zero references."""
        return Cudd_CheckZeroRef(self.manager)

    def __contains__(self, Function u):
        """Return `True` if `u.node` in `self.manager`."""
        assert u.manager == self.manager, 'undefined containment'
        try:
            Cudd_NodeReadIndex(u.node)
            return True
        except:
            return False

    # This method is similar to
    # the method `dd.cudd.BDD.__str__`.
    def __str__(self):
        d = self.statistics()
        s = (
            'Zero-suppressed binary decision diagram (CUDD wrapper).\n'
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
    def statistics(ZDD self, exact_node_count=False):
        """Return `dict` with CUDD node counts and times.

        For details see the docstring of the method
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
    def configure(self, **kw):
        """Read and apply parameter values.

        For details see the docstring of the method
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
                raise Exception(
                    'Unknown parameter "{k}"'.format(k=k))
        return d

    cpdef succ(self, Function u):
        """Return `(level, low, high)` for `u`."""
        assert u.manager == self.manager
        i = u.level
        v = u.low
        w = u.high
        if v is not None:
            assert i < v.level, 'v.level'
        if w is not None:
            assert i < w.level, 'w.level'
        return i, v, w

    cpdef incref(self, Function u):
        """Increment the reference count of `u`.

        For details read the docstring of the
        method `dd.cudd.BDD.incref`.
        """
        if u._ref <= 0:
            _utils._raise_runtimerror_about_ref_count(
                u._ref, 'method `dd.cudd_zdd.ZDD.incref`',
                '`dd.cudd_zdd.Function`')
        assert u._ref > 0, u._ref
        u._ref += 1
        self._incref(u.node)

    cpdef decref(
            self, Function u, recursive=False,
            _direct=False):
        """Decrement the reference count of `u`.

        For details read the docstring of the
        method `dd.cudd.BDD.decref`.

        @param recursive: if `True`, then call
            `Cudd_RecursiveDerefZdd`,
            else call `Cudd_Deref`
        @param _direct: use this parameter only after
            reading the source code of the
            Cython file `dd/cudd_zdd.pyx`.
            When `_direct == True`, some of the above
            description does not apply.
        """
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

    cdef _incref(self, DdNode *u):
        Cudd_Ref(u)

    cdef _decref(self, DdNode *u, recursive=False):
        if recursive:
            Cudd_RecursiveDerefZdd(self.manager, u)
        else:
            Cudd_Deref(u)

    def declare(self, *variables):
        """Add names in `variables` to `self.vars`."""
        for var in variables:
            self.add_var(var)

    cpdef add_var(self, var, index=None):
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
            assert j == index or index is None, (j, index)
            return j
        # new var
        if index is None:
            j = len(self._index_of_var)
        else:
            j = index
        u = Cudd_zddIthVar(self.manager, j)
        wrap(self, u)  # ref and recursive deref, to cancel ref out
        assert u != NULL, 'failed to add var "{v}"'.format(v=var)
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
        r = _ith_var(var, self)
        return r

    # CUDD implementation of `var`
    cpdef Function _var_cudd(self, var):
        """Return node for variable named `var`."""
        assert var in self._index_of_var, (
            'undefined variable "{v}", '
            'known variables are:\n {d}').format(
                v=var, d=self._index_of_var)
        j = self._index_of_var[var]
        r = Cudd_zddIthVar(self.manager, j)
        return wrap(self, r)

    def _add_bdd_var(self, j):
        """Declare a BDD variable with index `j`."""
        Cudd_bddIthVar(self.manager, j)

    def var_at_level(self, level):
        """Return name of variable at `level`."""
        j = Cudd_ReadInvPermZdd(self.manager, level)
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
        level = Cudd_ReadPermZdd(self.manager, j)
        assert level != -1, 'index {j} out of bounds'.format(j=j)
        return level

    @property
    def var_levels(self):
        """Return `dict` that maps variables to levels."""
        return {var: self.level_of_var(var)
                for var in self.vars}

    def reorder(self, var_order=None):
        """Reorder variables to `var_order`.

        If `var_order` is `None`, then invoke sifting.
        """
        if var_order is None:
            Cudd_zddReduceHeap(self.manager, CUDD_REORDER_SIFT, 1)
            return
        n = len(var_order)
        assert n == len(self.vars), (
            'Mismatch of variable numbers:\n'
            'declared variables: {n}\n'
            'new variable order: {m}').format(
                n=len(self.vars), m=n)
        cdef int *p
        p = <int *> PyMem_Malloc(n * sizeof(int))
        for var, level in var_order.iteritems():
            index = self._index_of_var[var]
            p[level] = index
        try:
            r = Cudd_zddShuffleHeap(self.manager, p)
        finally:
            PyMem_Free(p)
        assert r == 1, 'Failed to reorder.'

    def _enable_reordering(self):
        """Enable dynamic reordering of ZDDs."""
        Cudd_AutodynEnableZdd(self.manager, CUDD_REORDER_SIFT)

    def _disable_reordering(self):
        """Disable dynamic reordering of ZDDs."""
        Cudd_AutodynDisableZdd(self.manager)

    cpdef set support(self, Function u):
        """Return `set` of variables that `u` depends on.

        These are the variables that the Boolean function
        represented by the ZDD with root `u` depends on.
        """
        logger.debug('support')
        assert self.manager == u.manager
        return _c_support(u)

    cpdef _support_py(self, Function u):
        # Python implementation
        logger.debug('support')
        assert self.manager == u.manager, u
        visited = set()
        support = set()
        level = 0
        self._support(level, u, support, visited)
        return support

    cdef _support(self, level, Function u, support, visited):
        """Recurse to compute the support of `u`."""
        # terminal ?
        if u == self.false or level == len(self.vars):
            return
        if u in visited:
            return
        var = self.var_at_level(level)
        u_level, v, w = self.succ(u)
        assert level <= u_level, (level, u_level)
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

    cpdef _support_cudd(self, Function f):
        """Return `set` of variables that node `f` depends on."""
        assert self.manager == f.manager, f
        cdef DdNode *r
        r = Cudd_zddSupport(self.manager, f.node)
        f = wrap(self, r)
        supp = self._cube_to_dict(f)
        # constant ?
        if not supp:
            return set()
        # must be positive unate
        assert set(supp.values()) == {True}, supp
        return set(supp)

    def _copy_bdd_vars(self, bdd):
        """Copy BDD to ZDD variables."""
        Cudd_zddVarsFromBddVars(self.manager, 1)

    def _bdd_to_zdd(self, u):
        """Copy BDD `u` to a ZDD in `self`.

        @param u: node in a `dd.cudd.BDD` manager
        @type u: `dd.cudd.Function`
        @rtype: `Function`
        """
        cdef DdNode *r
        bdd = u.bdd
        u_ = bdd.copy(u, self)
        r = <DdNode *>u_.node
        r = Cudd_zddPortFromBdd(self.manager, r)
        return wrap(self, r)

    def copy(self, u, other):
        """Transfer ZDD with root `u` to `other`.

        @param other: `ZDD` or `BDD` manager
        @type other: `dd.cudd_zdd.ZDD` or
            `dd.cudd.BDD` or `dd.autoref.BDD`
        @rtype: `dd.cudd_zdd.Function`
            or `dd.cudd.Function`
            or `dd.autoref.Function`
        """
        return _copy.copy_zdd(u, other)

    cpdef Function let(
            self, definitions, Function u):
        """Replace variables with `definitions` in `u`.

        @param definitions: `dict` mapping variable names (`str`)
            to either:
            - Boolean values (`bool`), or
            - variable names (`str`), or
            - ZDD nodes (`Function`)
        @type u: `Function`
        @rtype: `Function`
        """
        logger.debug('let')
        assert self.manager == u.manager
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
                'or ZDD node as `int`. Got: {value}'.format(
                    value=value))
        return self._rename(u, d)

    cpdef Function _cofactor_root(
            self, Function u, d):
        """Return cofactor of `u` as defined in `d`.

        @param d: `dict` from variable names (`str`)
            to Boolean values (`bool`).
        """
        logger.debug('_cofactor_root')
        assert self.manager == u.manager
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
            self, int level, Function u, d, cache):
        """Recursively compute the cofactor of `u`."""
        # terminal ?
        if u == self.false or level == len(self.vars):
            return u
        t = (u, level)
        if t in cache:
            return cache[t]
        var = self.var_at_level(level)
        i = u.level
        assert level <= i, (level, i)
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
            assert level == i, (level, i)
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
            self, Function u, str var, value):
        """CUDD implementation of cofactor."""
        assert self.manager == u.manager
        cdef DdNode *r
        index = self._index_of_var[var]
        if value:
            r = Cudd_zddSubset1(self.manager, u.node, index)
        else:
            r = Cudd_zddSubset0(self.manager, u.node, index)
        return wrap(self, r)

    cpdef Function _compose_root(
            self, Function u, d):
        """Return the composition defined in `d`.

        @param d: `dict` from variable names (`str`)
            to ZDD nodes (`Function`).
        """
        logger.debug('_compose_root')
        assert self.manager == u.manager
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
            self, int level, Function u, d, cache):
        """Recursively compute composition of `u`."""
        assert level <= u.level, (
            level, u.level, 'level <= u.level')
        # terminal ?
        if u == self.false:
            return u
        if level == len(self.vars):
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
            assert level + 1 <= u.level, (
                'level + 1 <= u.level')
            r = self._compose(level + 1, u, d, cache)
            r = self._ite_recursive(g, self.false, r)
        else:
            assert level == u_level, (level, u_level)
            _, v, w = self.succ(u)
            assert level + 1 <= v.level, 'v.level'
            assert level + 1 <= w.level, 'w.level'
            p = self._compose(level + 1, v, d, cache)
            assert level + 1 <= w.level, 'w.level 2'
            q = self._compose(level + 1, w, d, cache)
            r = self._ite_recursive(g, q, p)
        cache[t] = r
        return r

    cpdef Function _rename(self, Function u, d):
        """Return node from renaming in `u` the variables in `d`."""
        logger.debug('_rename')
        assert self.manager == u.manager
        rename = {k: self.var(v) for k, v in d.items()}
        # return self._compose_root(u, rename)
        return _c_compose(u, rename)

    cpdef Function ite(
            self, Function g, Function u, Function v):
        """Ternary conditional `IF g THEN u ELSE v` for ZDDs.

        Calls `Cudd_zddIte`.
        """
        # for calling `cuddZddIte`
        # see the method `_ite_recursive`
        logger.debug('ite')
        assert g.manager == self.manager
        assert u.manager == self.manager
        assert v.manager == self.manager
        cdef DdNode *r
        r = Cudd_zddIte(self.manager, g.node, u.node, v.node)
        if r == NULL:
            raise CouldNotCreateNode()
        return wrap(self, r)

    cpdef Function _ite_recursive(
            self, Function g, Function u, Function v):
        """Recursive call to ternary conditional.

        Raises `CouldNotCreateNode` if reordering occurred.
        Calls `cuddZddIte`.
        """
        assert g.manager == self.manager
        assert u.manager == self.manager
        assert v.manager == self.manager
        cdef DdNode *r
        r = cuddZddIte(self.manager, g.node, u.node, v.node)
        if r == NULL:
            raise CouldNotCreateNode()
        return wrap(self, r)

    cpdef find_or_add(
            self, str var, Function low, Function high):
        """Return node `IF var THEN high ELSE low`."""
        assert low.manager == self.manager, 'low.manager'
        assert high.manager == self.manager, 'high.manager'
        assert var in self.vars, (var, self.vars, 'var')
        level = self.level_of_var(var)
        assert level < low.level, (level, low.level, 'low.level')
        assert level < high.level, (level, high.level, 'high.level')
        cdef DdNode *r
        index = self._index_of_var[var]
        if high == self.false:
            r = low.node
        else:
            r = cuddUniqueInterZdd(
                self.manager, index, high.node, low.node)
            if r == NULL:
                raise CouldNotCreateNode()
        f = wrap(self, r)
        assert level <= f.level, (level, f.level, 'f.level')
        return f

    cdef DdNode *_find_or_add(
            self, int index, DdNode *low, DdNode *high):
        """Implementation of method `find_or_add` in C."""
        cdef DdNode *r
        if high == Cudd_ReadZero(self.manager):
            return low
        r = cuddUniqueInterZdd(
            self.manager, index, high, low)
        assert r != NULL
        return r

    cpdef _top_cofactor(self, u, level):
        """Return cofactor at `level`.

        @param u: node
        @type u: `Function`
        @type level: `int`
        """
        u_level = u.level
        assert level <= u_level, (level, u_level)
        if level < u_level:
            return (u, self.false)
        v, w = u.low, u.high
        assert v is not None
        assert w is not None
        return (v, w)

    def count(self, Function u, nvars=None):
        """Return nuber of models of node `u`.

        @param nvars: regard `u` as an operator that
            depends on `nvars` many variables.

            If omitted, then assume those in `support(u)`.
        """
        logger.debug('count')
        assert u.manager == self.manager
        support = self.support(u)
        r = self._count(0, u, support, cache=dict())
        n_support = len(support)
        if nvars == None:
            nvars = n_support
        assert nvars >= n_support, (nvars, n_support)
        return r * 2**(nvars - n_support)

    def _count(
            self, int level, Function u, support, dict cache):
        """Recurse to count satisfying assignments."""
        if u == self.false:
            return 0
        if level == len(self.vars):
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

    def _count_cudd(self, Function u, int nvars):
        """CUDD implementation of `self.count`."""
        # returns different results
        assert u.manager == self.manager
        n = len(self.support(u))
        assert nvars >= n, (nvars, n)
        r = Cudd_zddCountMinterm(self.manager, u.node, nvars)
        assert r != CUDD_OUT_OF_MEM
        assert r != float('inf'), (
            'overflow of integer type double')
        return r

    def pick(self, Function u, care_vars=None):
        """Return a single satisfying assignment as `dict`."""
        logger.debug('pick')
        return next(self.pick_iter(u, care_vars), None)

    def pick_iter(self, Function u, care_vars=None):
        """Return generator over satisfying assignments."""
        logger.debug('pick_iter')
        assert self.manager == u.manager
        support = self.support(u)
        if care_vars is None:
            care_vars = support
        missing = support.difference(care_vars)
        if missing:
            logger.warning((
                'Missing bits:  '
                r'support \ care_vars = {missing}').format(
                    missing=missing))
        cube = dict()
        value = True
        config = self.configure(reordering=False)
        level = 0
        for cube in self._sat_iter(level, u, cube, value, support):
            for m in _bdd._enumerate_minterms(cube, care_vars):
                yield m
        self.configure(reordering=config['reordering'])

    def _pick_iter_cudd(self, Function u, care_vars=None):
        """CUDD implementation of `self.pick_iter`."""
        # assigns also to variables outside the support
        assert self.manager == u.manager
        cdef DdGen *gen
        cdef int *path
        cdef double value
        support = self.support(u)
        if care_vars is None:
            care_vars = support
        missing = support.difference(care_vars)
        if missing:
            logger.warning((
                'Missing bits:  '
                r'support \ care_vars = {missing}').format(
                    missing=missing))
        config = self.configure(reordering=False)
        gen = Cudd_zddFirstPath(self.manager, u.node, &path)
        assert gen != NULL, 'first path failed'
        try:
            r = 1
            while Cudd_IsGenEmpty(gen) == 0:
                assert r == 1, ('gen not empty but no next path', r)
                d = _path_array_to_dict(path, self._index_of_var)
                assert set(d).issubset(support), set(d).difference(support)
                for m in _bdd._enumerate_minterms(d, care_vars):
                    yield m
                r = Cudd_zddNextPath(gen, &path)
        finally:
            Cudd_GenFree(gen)
        self.configure(reordering=config['reordering'])

    def _sat_iter(self, level, u, cube, value, support):
        """Recurse to enumerate models."""
        # terminal ?
        if u == self.false or level == len(self.vars):
            if u != self.false:
                assert set(cube).issubset(support), set(
                    cube).difference(support)
                yield cube
            return
        # non-terminal
        i, v, w = self.succ(u)
        var = self.var_at_level(level)
        assert level <= i, (level, i)
        if level < i:
            cube[var] = False
            assert var in support, (var, support, '<')
            for x in self._sat_iter(
                    level + 1, u, cube, value, support):
                yield x
        elif v != w:
            assert level == i, (level, i)
            assert var in support, (var, support, '==')
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
            assert level == i, (level, i)
            assert v == w, (v, w)
            for x in self._sat_iter(
                    level + 1, v, cube, value, support):
                yield x

    cpdef Function apply(
            self,
            op,
            Function u,
            Function v=None,
            Function w=None):
        """Return as `Function` the result of applying `op`."""
        logger.debug('apply')
        assert self.manager == u.manager
        if v is not None:
            assert self.manager == v.manager
        if w is not None:
            assert self.manager == w.manager
        cdef DdNode *r
        cdef DdNode *neg_node
        cdef Function t
        cdef DdManager *mgr
        mgr = u.manager
        # unary
        r = NULL
        if op in ('~', 'not', '!'):
            assert v is None, v
            assert w is None, w
            r = Cudd_zddDiff(mgr, Cudd_ReadZddOne(mgr, 0), u.node)
        # binary
        elif op in ('and', '/\\', '&', '&&'):
            assert w is None, w
            r = Cudd_zddIntersect(mgr, u.node, v.node)
        elif op in ('or', r'\/', '|', '||'):
            assert w is None, w
            r = Cudd_zddUnion(mgr, u.node, v.node)
        elif op in ('xor', '^'):
            assert w is None, w
            neg_node = Cudd_zddDiff(mgr, Cudd_ReadZddOne(mgr, 0), v.node)
            neg = wrap(self, neg_node)
            r = Cudd_zddIte(mgr, u.node, neg.node, v.node)
        elif op in ('=>', '->', 'implies'):
            assert w is None, w
            r = Cudd_zddIte(mgr, u.node, v.node, Cudd_ReadZddOne(mgr, 0))
        elif op in ('<=>', '<->', 'equiv'):
            assert w is None, w
            neg_node = Cudd_zddDiff(mgr, Cudd_ReadZddOne(mgr, 0), v.node)
            neg = wrap(self, neg_node)
            r = Cudd_zddIte(mgr, u.node, v.node, neg.node)
        elif op in ('diff', '-'):
            assert w is None, w
            r = Cudd_zddDiff(mgr, u.node, v.node)
        elif op in (r'\A', 'forall'):
            assert w is None, w
            qvars = self.support(u)
            res = self.forall(qvars, v)
            Cudd_Ref(res.node)
            r = res.node
        elif op in (r'\E', 'exists'):
            assert w is None, w
            qvars = self.support(u)
            res = self.exist(qvars, v)
            Cudd_Ref(res.node)
            r = res.node
        # ternary
        elif op == 'ite':
            assert v is not None
            assert w is not None
            r = Cudd_zddIte(mgr, u.node, v.node, w.node)
        else:
            raise Exception(
                'unknown operator: "{op}"'.format(op=op))
        if r == NULL:
            config = self.configure()
            raise Exception((
                'CUDD appears to have run out of memory.\n'
                'Computing the operator {op}\n.'
                'Current settings for upper bounds:\n'
                '    max memory = {max_memory} bytes\n'
                '    max cache = {max_cache} entries').format(
                    max_memory=config['max_memory'],
                    max_cache=config['max_cache_hard'],
                    op=op))
        res = wrap(self, r)
        if op in (r'\A', 'forall', r'\E', 'exist'):
            Cudd_RecursiveDerefZdd(mgr, r)
        return res

    cpdef _add_int(self, i):
        """Return node from integer `i`."""
        cdef DdNode *u
        assert i not in (0, 1), i
        # invert `Function.__int__`
        if 2 <= i:
            i -= 2
        u = <DdNode *><stdint.uintptr_t>i
        return wrap(self, u)

    cpdef Function cube(self, dvars):
        """Return conjunction of variables in `dvars`.

        If `dvars` is a `dict`, then a Boolean value
        `False` results in a negated variable.

        @param dvars: `dict` or container of variables
            as `str`
        @rtype: Function
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
                    'value not Boolean: {b}'.format(
                        b=value))
        return r

    cpdef Function _disjoin_root(
            self, Function u, Function v):
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
            self, level, Function u, Function v, cache):
        """Recursively disjoin `u` and `v`.

        The recursion starts at `level`.
        """
        if u == self.false:
            return v
        if v == self.false:
            return u
        if level == len(self.vars):
            assert u.low is None
            return u
        if level == len(self.vars):
            assert v.low is None
            return v
        assert level < len(self.vars), (level, len(self.vars))
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
            self, Function u, Function v):
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
            self, level, Function u, Function v, cache):
        """Recursively conjoin `u` and `v`.

        The recursion starts at `level`.
        """
        if u == self.false:
            return u
        if v == self.false:
            return v
        if level == len(self.vars):
            assert u.low is None
            return v
        if level == len(self.vars):
            assert v.low is None
            return u
        assert level < len(self.vars), (level, len(self.vars))
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
            self, Function u, qvars, forall=False):
        """Abstract variables `qvars` from node `u`."""
        logger.debug('quantify')
        # similar to the C implementation
        # return self._quantify_using_cube_root(
        #     u, qvars, forall)

        # implementation that uses a `dict`
        # return self._quantify_root(
        #     u, qvars, forall)

        # C implementation
        cdef Function r
        if forall:
            r = _c_forall(qvars, u)
        else:
            r = _c_exist(qvars, u)
        return r

    cpdef Function _quantify_root(
            self, Function u, qvars, forall=False):
        """Abstract variables `qvars` in `u`.

        @param u: node
        @param qvars: `set` of quantified variables
        @param forall: if `True`,
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
            self, Function u, qvars, forall=False):
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
            self, level, u, cube, forall, cache):
        """Recurse to quantify variables.

        This implementation uses a ZDD to represent
        the set of variables to quantify.
        """
        if u == self.false or level == len(self.vars):
            return u
        t = (u, level)
        if t in cache:
            return cache[t]
        v, w = self._top_cofactor(u, level)
        assert cube.low == cube.high
        new_cube, _ = self._top_cofactor(cube, level)
        p = self._quantify_using_cube(level + 1, v, new_cube, forall, cache)
        q = self._quantify_using_cube(level + 1, w, new_cube, forall, cache)
        var = self.var_at_level(level)
        assert level <= cube.level, (level, cube.level)
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
            self, level, u, qvars, forall, cache):
        """Recurse to quantify variables."""
        assert level <= u.level, (level, u.level, 'u')
        # terminal ?
        if u == self.false or level == len(self.vars):
            return u
        t = (u, level)
        if t in cache:
            r = cache[t]
            assert level <= r.level, (level, r.level, 'cache')
            return r
        v, w = self._top_cofactor(u, level)
        assert level < v.level, (level, v.level, 'v')
        assert level < w.level, (level, w.level, 'w')
        p = self._quantify(level + 1, v, qvars, forall, cache)
        q = self._quantify(level + 1, w, qvars, forall, cache)
        assert level < p.level, (level, p.level, 'p')
        assert level < q.level, (level, q.level, 'q')
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
        assert min(level, u.level) <= r.level, (
            level, u.level, r.level, 'u, r')
        cache[t] = r
        assert level <= r.level, (level, r.level, 'r')
        return r

    def _quantify_optimized(
            self, level, u, qvars, forall, cache):
        """Recurse to quantify variables."""
        # terminal ?
        if u == self.false or level == len(self.vars):
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

    cpdef Function forall(self, variables, Function u):
        """Quantify `variables` in `u` universally.

        Wraps method `quantify` to be more readable.
        """
        return self.quantify(u, variables, forall=True)

    cpdef Function exist(self, variables, Function u):
        """Quantify `variables` in `u` existentially.

        Wraps method `quantify` to be more readable.
        """
        return self.quantify(u, variables, forall=False)

    cpdef assert_consistent(self):
        """Raise `AssertionError` if not consistent."""
        assert Cudd_DebugCheck(self.manager) == 0
        n = len(self.vars)
        m = len(self._var_with_index)
        k = len(self._index_of_var)
        assert n == m, (n, m)
        assert m == k, (m, k)
        assert set(self.vars) == set(self._index_of_var)
        assert set(self._var_with_index) == set(
            self._index_of_var.values())

    def add_expr(self, expr):
        """Return node for `str` expression `e`."""
        return _parser.add_expr(expr, self)

    cpdef str to_expr(self, Function u):
        """Return a Boolean expression for node `u`."""
        assert u.manager == self.manager
        cache = dict()
        level = 0
        return self._to_expr(level, u, cache)

    cpdef str _to_expr(self, level, Function u, dict cache):
        """Recursively compute an expression."""
        if u == self.false:
            return 'FALSE'
        if level == len(self.vars):
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
            s = 'ite({var}, {q}, {p})'.format(
                var=var, q=q, p=p)
        cache[u] = s
        return s

    cpdef dump(self, filename, roots, filetype=None):
        """Write ZDD as a diagram to PDF file `filename`.

        @param filename: file name.
            If `filetype is None`, then `filename` must
            end with the substring `.pdf`.
        @type filename: `str`

        @param filetype: `'pdf'` or `None`

        Only the ZDD manager nodes that are reachable from the
        ZDD references in `roots` are included in the diagram.
        Currently, `roots` must contain a single ZDD reference.

        Currently, the only `filetype` value supported
        is `'pdf`'. If `filetype` is omitted, then the
        `filename` must end with the substring `'.pdf'`.
        """
        u, = roots
        if filetype is None:
            name = filename.lower()
            if name.endswith('.pdf'):
                filetype = 'pdf'
            else:
                raise Exception((
                    'cannot infer file type '
                    'from extension of file '
                    'name "{f}"').format(
                        f=filename))
        assert filetype == 'pdf', filetype
        g = to_nx(u)
        import networkx as nx
        pd = nx.drawing.nx_pydot.to_pydot(g)
        pd.write_pdf(filename)

    cpdef load(self, filename):
        raise NotImplementedError()

    # Same with the method `dd.cudd.BDD._cube_to_dict`.
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

    @property
    def false(self):
        """`Function` for Boolean value FALSE."""
        return self._bool(False)

    @property
    def true(self):
        """`Function` for Boolean value TRUE."""
        return self._bool(True)

    @property
    def true_node(self):
        """Return the constant ZDD node for TRUE."""
        cdef DdNode *r
        r = DD_ONE(self.manager)
        return wrap(self, r)

    cdef Function _bool(self, v):
        """Return terminal node for Boolean `v`."""
        cdef DdNode *r
        if v:
            r = Cudd_ReadZddOne(self.manager, 0)
        else:
            r = Cudd_ReadZero(self.manager)
        return wrap(self, r)


cdef Function wrap(ZDD bdd, DdNode *node):
    """Return a `Function` that wraps `node`."""
    # because `@classmethod` unsupported
    f = Function()
    f.init(node, bdd)
    return f


cdef class Function(object):
    """Wrapper of ZDD `DdNode` from CUDD.

    For details, read the docstring of the
    class `dd.cudd.Function`.
    """

    cdef object __weakref__
    cdef public ZDD bdd
    cdef public ZDD zdd
    cdef DdManager *manager
    cdef DdNode *node
    cdef public int _ref

    cdef init(self, DdNode *node, ZDD bdd):
        assert node != NULL, '`DdNode *node` is `NULL` pointer.'
        self.zdd = bdd
        # TODO: rename this attribute to `zdd` in the class
        self.bdd = bdd  # keep this attribute for writing
            # common algorithms for BDDs and ZDDs where possible
        self.manager = bdd.manager
        self.node = node
        self._ref = 1  # lower bound on reference count
        Cudd_Ref(node)

    def __hash__(self):
        return int(self)

    @property
    def _index(self):
        """Index of `self.node`."""
        cdef DdNode *u
        index = Cudd_NodeReadIndex(self.node)
        return index

    @property
    def var(self):
        """Variable at level where this node is.

        If node is constant, return `None`.
        """
        if cuddIsConstant(self.node):
            return None
        return self.bdd._var_with_index[self._index]

    @property
    def level(self):
        """Level where this node currently is."""
        i = self._index
        return Cudd_ReadPermZdd(self.manager, i)

    @property
    def ref(self):
        """Reference count of node."""
        cdef DdNode *u
        return self.node.ref

    @property
    def low(self):
        """Return "else" node as `Function`."""
        cdef DdNode *u
        if cuddIsConstant(self.node):
            return None
        # See the lines:
        #
        # else if (top_var == level) {
        #     res = cuddE(P);
        #
        # inside the function `zdd_subset0_aux`,
        # in the file `cudd/cuddZddSetop.c`.
        u = cuddE(self.node)
        return wrap(self.bdd, u)

    @property
    def high(self):
        """Return "then" node as `Function`."""
        cdef DdNode *u
        if cuddIsConstant(self.node):
            return None
        # See the lines:
        #
        # } else if (top_var == level) {
    	# res = cuddT(P);
        #
        # inside the function `zdd_subset1_aux`,
        # in file `cudd/cuddZddSetop.c`.
        u = cuddT(self.node)
        return wrap(self.bdd, u)

    @property
    def negated(self):
        raise Exception(
            'No complemented edges for ZDDs in CUDD, '
            'only for BDDs.')

    @property
    def support(ZDD self):
        """Return `set` of variables in support."""
        return self.bdd.support(self)

    def __dealloc__(self):
        # when changing this method,
        # update also the function
        # `_test_call_dealloc` below
        if self._ref < 0:
            raise AssertionError((
                "The lower bound `_ref` on the node's "
                'reference count has value {_ref}, '
                'which is unexpected and should never happen. '
                'Was the value of `_ref` changed from outside '
                'this class?'
                ).format(_ref=self._ref))
        assert self._ref >= 0, self._ref
        if self._ref == 0:
            return
        # anticipate multiple calls to `__dealloc__`
        self._ref -= 1
        # deref
        Cudd_RecursiveDerefZdd(self.manager, self.node)

    def __int__(self):
        # inverse is `ZDD._add_int`
        assert sizeof(stdint.uintptr_t) == sizeof(DdNode *)
        i = <stdint.uintptr_t>self.node
        # 0, 1 are true and false in logic syntax
        if 0 <= i:
            i += 2
        assert i not in (0, 1), i
        return i

    def __repr__(self):
        return (
            'Function (ZDD DdNode) with '
            'var index: {idx}, '
            'ref count: {ref}, '
            'int repr: {i}').format(
                idx=self._index,
                ref=self.ref,
                i=int(self))

    def __str__(self):
        return '@' + str(int(self))

    def __len__(self):
        # The function `Cudd_zddDagSize`
        # is deprecated because it duplicates
        # the function `Cudd_DagSize`.
        return Cudd_zddDagSize(self.node)

    @property
    def dag_size(self):
        """Return number of ZDD nodes.

        This is the number of ZDD nodes that
        are reachable from this ZDD reference,
        i.e., with `self` as root.
        """
        return len(self)

    def __richcmp__(Function self, Function other, op):
        if other is None:
            eq = False
        else:
            # guard against mixing managers
            assert self.manager == other.manager
            eq = (self.node == other.node)
        if op == 2:  # ==
            return eq
        elif op == 3:  # !=
            return not eq
        elif op == 0:  # <
            return (other | ~ self) == self.bdd.true and not eq
        elif op == 1:  # <=
            return (other | ~ self) == self.bdd.true
        elif op == 4:  # >
            return (self | ~ other) == self.bdd.true and not eq
        elif op == 5:  # >=
            return (self | ~ other) == self.bdd.true
        else:
            raise ValueError(
                'unexpected `op` value: {op}'.format(op=op))

    def __invert__(self):
        cdef DdNode *r
        r = Cudd_zddDiff(
            self.manager,
            Cudd_ReadZddOne(self.manager, 0),
            self.node)
        return wrap(self.bdd, r)

    def __and__(Function self, Function other):
        assert self.manager == other.manager
        r = Cudd_zddIntersect(self.manager, self.node, other.node)
        return wrap(self.bdd, r)

    def __or__(Function self, Function other):
        assert self.manager == other.manager
        r = Cudd_zddUnion(self.manager, self.node, other.node)
        return wrap(self.bdd, r)

    def implies(Function self, Function other):
        assert self.manager == other.manager
        r = Cudd_zddIte(
            self.manager, self.node,
            other.node, Cudd_ReadZddOne(self.manager, 0))
        return wrap(self.bdd, r)

    def equiv(Function self, Function other):
        return self.bdd.apply('<=>', self, other)

    def let(Function self, **definitions):
        return self.bdd.let(definitions, self)

    def exist(Function self, *variables):
        return self.bdd.exist(variables, self)

    def forall(Function self, *variables):
        return self.bdd.forall(variables, self)

    def pick(Function self, care_vars=None):
        return self.bdd.pick(self, care_vars)

    def count(Function self, nvars=None):
        return self.bdd.count(self, nvars)


# Similar to the function `dd.cudd._cube_array_to_dict`
cdef dict _path_array_to_dict(int *x, dict index_of_var):
    """Return assignment from array of literals `x`."""
    d = dict()
    for var, j in index_of_var.iteritems():
        b = x[j]
        if b == 2:  # absence of ZDD node
            d[var] = False
        elif b == 1:  # "then" arc
            d[var] = True
        elif b == 0:  # "else" arc
            d[var] = False
        else:
            raise Exception(
                'unknown polarity: {b}, '
                'for variable "{var}"'.format(
                    b=b, var=var))
    return d


# Copy of the function `dd.cudd._cube_array_to_dict`
# TODO: place in a header file, if used in this module
cdef dict _cube_array_to_dict(int *x, dict index_of_var):
    """Return assignment from array of literals `x`.

    @param x: see `dd.cudd._dict_to_cube_array`
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


def to_nx(u):
    """Return graph for the ZDD rooted at `u`.

    @type u: `Function`
    @rtype: `networkx.MultiDiGraph`
    """
    import networkx as nx
    g = nx.MultiDiGraph()
    visited = set()
    umap = dict()
    _to_nx(g, u, visited, umap)
    return g


def _to_nx(g, u, visited, umap):
    """Recursively construct a ZDD graph."""
    r = int(u)
    r_nd = umap.setdefault(r, len(g))
    v, w = u.low, u.high
    if v is None:
        label = 'FALSE' if u == u.bdd.false else 'TRUE'
        g.add_node(r_nd, label=label)
        return
    assert v is not None
    assert w is not None
    if r in visited:
        return
    visited.add(r)
    g.add_node(r_nd, label=u.var)
    p = int(v)
    q = int(w)
    p_nd = umap.setdefault(p, len(g))
    g.add_edge(r_nd, p_nd, taillabel='0', style='dashed')
    q_nd = umap.setdefault(q, len(g))
    g.add_edge(r_nd, q_nd, taillabel='1', style='solid')
    _to_nx(g, v, visited, umap)
    _to_nx(g, w, visited, umap)


cpdef Function _dict_to_zdd(qvars, zdd):
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


cpdef set _cube_to_universe_root(Function cube, zdd):
    """Map the conjunction `cube` to its support."""
    qvars = set()
    _cube_to_universe(cube, qvars, zdd)
    qvars_ = zdd.support(cube)
    assert qvars == qvars_, (qvars, qvars_)
    return qvars


cpdef _cube_to_universe(Function cube, qvars, zdd):
    """Recursively map `cube` to its support."""
    if cube == zdd.false:
        return
    if cube == zdd.true_node:
        return
    if cube.low != cube.high:
        var = cube.var
        qvars.add(var)
        assert cube.low == zdd.false, len(cube.low)
    _cube_to_universe(cube.high, qvars, zdd)


cpdef Function _ith_var(var, zdd):
    """Return ZDD of variable `var`."""
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
        Function u):
    """Universally quantify `variables` in `u`."""
    cdef DdNode *r
    cube = _dict_to_zdd(variables, u.bdd)
    r = _forall_root(u.manager, u.node, cube.node)
    return wrap(u.bdd, r)


# changes to the function `_exist_root`
# are copied here
cdef DdNode *_forall_root(
        DdManager *mgr,
        DdNode *u,
        DdNode *cube):
    r"""Root of recursion for \A."""
    mgr.reordered = 1
    while mgr.reordered == 1:
        mgr.reordered = 0
        r = _forall(mgr, 0, u, cube)
    return r


# changes to the function `_exist`
# are copied here
cdef DdNode *_forall(
        DdManager *mgr,
        int level,
        DdNode *u,
        DdNode *cube):
    r"""Recursive \A."""
    index = Cudd_ReadInvPermZdd(mgr, level)
    if u == DD_ZERO(mgr) or index == -1:
        return u
    r = cuddCacheLookup2Zdd(
        mgr, _forall_root, u, cube)
    if r != NULL:
        return r
    u_index = Cudd_NodeReadIndex(u)
    u_level = Cudd_ReadPermZdd(mgr, u_index)
    cube_index = Cudd_NodeReadIndex(cube)
    cube_level = Cudd_ReadPermZdd(mgr, cube_index)
    assert level <= u_level, (level, u_level)
    assert level <= cube_level, (level, cube_level)
    # top cofactor
    if level < u_level:
        v, w = u, DD_ZERO(mgr)
    else:
        v, w = cuddE(u), cuddT(u)
    if level < cube_level:
        new_cube = cube
    else:
        assert cuddE(cube) == cuddT(cube)
        new_cube = cuddE(cube)
    p = _forall(mgr, level + 1, v, new_cube)
    if p == NULL:
        return NULL
    cuddRef(p)
    q = _forall(mgr, level + 1, w, new_cube)
    if q == NULL:
        Cudd_RecursiveDerefZdd(mgr, p)
        return NULL
    cuddRef(q)
    if level == cube_level:
        conj = _conjoin(mgr, level + 1, p, q)
        if conj == NULL:
            Cudd_RecursiveDerefZdd(mgr, p)
            Cudd_RecursiveDerefZdd(mgr, q)
            return NULL
        cuddRef(conj)
        r = _find_or_add(mgr, index, conj, conj)
        Cudd_RecursiveDerefZdd(mgr, conj)
    else:
        r = _find_or_add(mgr, index, p, q)
    if r == NULL:
        Cudd_RecursiveDerefZdd(mgr, p)
        Cudd_RecursiveDerefZdd(mgr, q)
        return NULL
    cuddRef(r)
    Cudd_RecursiveDerefZdd(mgr, p)
    Cudd_RecursiveDerefZdd(mgr, q)
    cuddCacheInsert2(
        mgr, _forall_root, u, cube, r)
    cuddDeref(r)
    return r


cpdef Function _c_exist(
        variables,
        Function u):
    """Existentially quantify `variables` in `u`."""
    cdef DdNode *r
    cdef Function cube
    cube = _dict_to_zdd(variables, u.bdd)
    r = _exist_root(u.manager, u.node, cube.node)
    return wrap(u.bdd, r)


cdef DdNode *_exist_root(
        DdManager *mgr,
        DdNode *u,
        DdNode *cube):
    r"""Root of recursion for \E."""
    mgr.reordered = 1
    while mgr.reordered == 1:
        mgr.reordered = 0
        r = _exist(mgr, 0, u, cube)
    return r


cdef DdNode *_exist(
        DdManager *mgr,
        int level,
        DdNode *u,
        DdNode *cube):
    r"""Recursive \E."""
    index = Cudd_ReadInvPermZdd(mgr, level)
    if u == DD_ZERO(mgr) or index == -1:
        return u
    r = cuddCacheLookup2Zdd(
        mgr, _exist_root, u, cube)
    if r != NULL:
        return r
    u_index = Cudd_NodeReadIndex(u)
    u_level = Cudd_ReadPermZdd(mgr, u_index)
    cube_index = Cudd_NodeReadIndex(cube)
    cube_level = Cudd_ReadPermZdd(mgr, cube_index)
    assert level <= u_level, (level, u_level)
    assert level <= cube_level, (level, cube_level)
    # top cofactor
    if level < u_level:
        v, w = u, DD_ZERO(mgr)
    else:
        v, w = cuddE(u), cuddT(u)
    if level < cube_level:
        new_cube = cube
    else:
        assert cuddE(cube) == cuddT(cube), 'E == T'
        new_cube = cuddE(cube)
    p = _exist(mgr, level + 1, v, new_cube)
    if p == NULL:
        return NULL
    cuddRef(p)
    q = _exist(mgr, level + 1, w, new_cube)
    if q == NULL:
        Cudd_RecursiveDerefZdd(mgr, p)
        return NULL
    cuddRef(q)
    assert level <= cube_level, (level, cube_level)
    if level == cube_level:
        disj = _disjoin(mgr, level + 1, p, q)
        if disj == NULL:
            Cudd_RecursiveDerefZdd(mgr, p)
            Cudd_RecursiveDerefZdd(mgr, q)
            return NULL
        cuddRef(disj)
        r = _find_or_add(mgr, index, disj, disj)
        Cudd_RecursiveDerefZdd(mgr, disj)
    else:
        r = _find_or_add(mgr, index, p, q)
    if r == NULL:
        Cudd_RecursiveDerefZdd(mgr, p)
        Cudd_RecursiveDerefZdd(mgr, q)
        return NULL
    cuddRef(r)
    Cudd_RecursiveDerefZdd(mgr, p)
    Cudd_RecursiveDerefZdd(mgr, q)
    cuddCacheInsert2(
        mgr, _exist_root, u, cube, r)
    cuddDeref(r)
    return r


cdef DdNode *_find_or_add(
        DdManager *mgr,
        int index,
        DdNode *v,
        DdNode *w):
    """Find node in table or add new node.

    Calls `cuddUniqueInterZdd` and
    ensures canonicity of ZDDs.
    """
    if w == DD_ZERO(mgr):
        return v
    return cuddUniqueInterZdd(mgr, index, w, v)


cpdef Function _c_disjoin(
        Function u,
        Function v):
    """Return the disjunction of `u` and `v`.

    @param u, v: ZDD node
    @type u, v: `Function`
    @rtype: `Function`
    """
    cdef DdNode *r
    cdef DdManager *mgr
    mgr = u.manager
    r = _disjoin_root(
        mgr, u.node, v.node)
    return wrap(u.bdd, r)


# This function is used for hash in cache.
cdef DdNode *_disjoin_root(
        DdManager *mgr,
        DdNode *u,
        DdNode *v):
    """Return the disjunction of `u` and `v`."""
    mgr.reordered = 1
    while mgr.reordered == 1:
        mgr.reordered = 0
        r = _disjoin(mgr, 0, u, v)
    return r


cdef DdNode *_disjoin(
        DdManager *mgr,
        int level,
        DdNode *u,
        DdNode *v):
    """Recursively disjoin `u` and `v`."""
    index = Cudd_ReadInvPermZdd(mgr, level)
    # TODO: review reference counting
    if u == DD_ZERO(mgr):
        return v
    if v == DD_ZERO(mgr):
        return u
    if u == DD_ONE(mgr) and index == -1:
        return u
    if v == DD_ONE(mgr) and index == -1:
        return v
    r = cuddCacheLookup2Zdd(
        mgr, _disjoin_root, u, v)
    if r != NULL:
        return r
    u_index = Cudd_NodeReadIndex(u)
    u_level = Cudd_ReadPermZdd(mgr, u_index)
    v_index = Cudd_NodeReadIndex(v)
    v_level = Cudd_ReadPermZdd(mgr, v_index)
    assert level <= u_level
    assert level <= v_level
    if level < u_level:
        pu, qu = u, DD_ZERO(mgr)
    else:
        pu, qu = cuddE(u), cuddT(u)
    if level < v_level:
        pv, qv = v, DD_ZERO(mgr)
    else:
        pv, qv = cuddE(v), cuddT(v)
    p = _disjoin(mgr, level + 1, pu, pv)
    if p == NULL:
        return NULL
    cuddRef(p)
    q = _disjoin(mgr, level + 1, qu, qv)
    if q == NULL:
        Cudd_RecursiveDerefZdd(mgr, p)
        return NULL
    cuddRef(q)
    r = _find_or_add(mgr, index, p, q)
    if r == NULL:
        Cudd_RecursiveDerefZdd(mgr, p)
        Cudd_RecursiveDerefZdd(mgr, q)
        return NULL
    cuddRef(r)
    Cudd_RecursiveDerefZdd(mgr, p)
    Cudd_RecursiveDerefZdd(mgr, q)
    cuddCacheInsert2(
        mgr, _disjoin_root, u, v, r)
    cuddDeref(r)
    return r


cpdef Function _c_conjoin(
        Function u,
        Function v):
    """Return the conjunction of `u` and `v`.

    @param u, v: ZDD node
    @type u, v: `Function`
    @rtype: `Function`
    """
    cdef DdNode *r
    cdef DdManager *mgr
    mgr = u.manager
    r = _conjoin_root(
        mgr, u.node, v.node)
    return wrap(u.bdd, r)


# This function is used for hash in cache.
cdef DdNode *_conjoin_root(
        DdManager *mgr,
        DdNode *u,
        DdNode *v):
    """Return the conjunction of `u` and `v`."""
    mgr.reordered = 1
    while mgr.reordered == 1:
        mgr.reordered = 0
        r = _conjoin(mgr, 0, u, v)
    return r


cdef DdNode *_conjoin(
        DdManager *mgr,
        int level,
        DdNode *u,
        DdNode *v):
    """Recursively conjoin `u` and `v`."""
    index = Cudd_ReadInvPermZdd(mgr, level)
    if u == DD_ZERO(mgr):
        return u
    if v == DD_ZERO(mgr):
        return v
    if u == DD_ONE(mgr) and index == -1:
        return v
    if v == DD_ONE(mgr) and index == -1:
        return u
    r = cuddCacheLookup2Zdd(
        mgr, _conjoin_root, u, v)
    if r != NULL:
        return r
    u_index = Cudd_NodeReadIndex(u)
    u_level = Cudd_ReadPermZdd(mgr, u_index)
    v_index = Cudd_NodeReadIndex(v)
    v_level = Cudd_ReadPermZdd(mgr, v_index)
    assert level <= u_level
    assert level <= v_level
    if level < u_level:
        pu, qu = u, DD_ZERO(mgr)
    else:
        pu, qu = cuddE(u), cuddT(u)
    if level < v_level:
        pv, qv = v, DD_ZERO(mgr)
    else:
        pv, qv = cuddE(v), cuddT(v)
    p = _conjoin(mgr, level + 1, pu, pv)
    if p == NULL:
        return NULL
    cuddRef(p)
    q = _conjoin(mgr, level + 1, qu, qv)
    if q == NULL:
        Cudd_RecursiveDerefZdd(mgr, p)
        return NULL
    cuddRef(q)
    r = _find_or_add(mgr, index, p, q)
    if r == NULL:
        Cudd_RecursiveDerefZdd(mgr, p)
        Cudd_RecursiveDerefZdd(mgr, q)
        return NULL
    cuddRef(r)
    Cudd_RecursiveDerefZdd(mgr, p)
    Cudd_RecursiveDerefZdd(mgr, q)
    cuddCacheInsert2(
        mgr, _conjoin_root, u, v, r)
    cuddDeref(r)
    return r


cpdef Function _c_compose(
        Function u, dict dvars):
    """Compute composition of `u` with `dvars`.

    @param u: ZDD node
    @type u: `Function`
    @param dvars: `dict` that maps variable
        names (`str`) to ZDD nodes (`Function`)
    """
    cdef DdNode *r
    cdef DdManager *mgr
    cdef Function g
    mgr = u.manager
    zdd = u.bdd
    # convert `dvars` to `DdNode **`
    n = len(zdd.vars)
    cdef DdNode **vector
    vector = <DdNode **> PyMem_Malloc(n * sizeof(DdNode *))
    for var in zdd.vars:
        i = zdd._index_of_var[var]
        if var in dvars:
            g = dvars[var]
        else:
            g = zdd.var(var)
        cuddRef(g.node)
        assert g.ref > 0, (var, g.ref)
        vector[i] = g.node
    # compose
    r = NULL
    try:
        r = _compose_root(mgr, u.node, vector)
    finally:
        if r is not NULL:
            cuddRef(r)
            assert r.ref > 0, r.ref
        for i in range(n):
            Cudd_RecursiveDerefZdd(mgr, vector[i])
        if r is not NULL:
            cuddDeref(r)
        PyMem_Free(vector)
    if r is NULL:
        raise AssertionError('r is NULL')
    return wrap(u.bdd, r)


cdef DdNode *_compose_root(
        DdManager *mgr,
        DdNode *u,
        DdNode **vector):
    """Root of recursive composition."""
    cdef DdNode *r
    level = 0
    mgr.reordered = 1
    while mgr.reordered == 1:
        mgr.reordered = 0
        table = dict()
        # table = cuddHashTableInit(mgr, 1, 2)
        # if table == NULL:
        #     return NULL
        r = _compose(mgr, level, table, u, vector)
        # if mgr.reordered == 1:
        #     assert r == NULL, r
        if r != NULL:
            cuddRef(r)
            assert r.ref > 0, r.ref
        # cuddHashTableQuitZdd(table)
        for nd in table.values():
            Cudd_RecursiveDerefZdd(mgr,
                <DdNode *><stdint.uintptr_t>nd)
        if r != NULL:
            cuddDeref(r)
    return r


cdef DdNode *_compose(
        DdManager *mgr,
        int level,
        # DdHashTable *table,
        dict table,
        DdNode *u,
        DdNode **vector):
    """Recursively compute composition.

    The composition is defined in the
    array `vector`.
    """
    if u == DD_ZERO(mgr):
        return u
    if u == DD_ONE(mgr):
        return Cudd_ReadZddOne(mgr, 0)
    t = (<stdint.uintptr_t>u, level)
    if t in table:
        return <DdNode *><stdint.uintptr_t>table[t]
    # r = cuddHashTableLookup1(table, u)
    # if r != NULL:
    #     return r
    u_index = Cudd_NodeReadIndex(u)
    u_level = Cudd_ReadPermZdd(mgr, u_index)
    assert level <= u_level, (level, u_level)
    index = Cudd_ReadInvPermZdd(mgr, level)
    g = vector[index]
    if g is NULL:
        raise AssertionError('`g is NULL`')
    assert g.ref > 0, (index, g.ref)
    if level < u_level:
        assert level + 1 <= u_level, (level, u_level)
        c = _compose(
            mgr, level + 1, table, u, vector)
        if c == NULL:
            return NULL
        cuddRef(c)
        assert c.ref > 0, c.ref
        r = cuddZddIte(mgr, g, DD_ZERO(mgr), c)
        if r == NULL:
            Cudd_RecursiveDerefZdd(mgr, c)
            return NULL
        cuddRef(r)
        assert r.ref > 0, r.ref
        Cudd_RecursiveDerefZdd(mgr, c)
    else:
        assert level == u_level, (level, u_level)
        v, w = cuddE(u), cuddT(u)
        assert v.ref > 0, v.ref
        assert w.ref > 0, w.ref
        p = _compose(
            mgr, level + 1, table, v, vector)
        if p == NULL:
            return NULL
        cuddRef(p)
        assert p.ref > 0, p.ref
        q = _compose(
            mgr, level + 1, table, w, vector)
        if q == NULL:
            Cudd_RecursiveDerefZdd(mgr, p)
            return NULL
        cuddRef(q)
        assert q.ref > 0, q.ref
        r = cuddZddIte(mgr, g, q, p)
        if r == NULL:
            Cudd_RecursiveDerefZdd(mgr, q)
            Cudd_RecursiveDerefZdd(mgr, p)
            return NULL
        cuddRef(r)
        assert r.ref > 0, r.ref
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
cdef void cuddHashTableQuitZdd(
        DdHashTable * hash):
    """Shutdown a hash table.

    This function calls `Cudd_RecursiveDerefZdd`.
    The function `cuddHashTableQuit` calls
    `Cudd_RecursiveDeref`.
    """
    cdef unsigned int i;
    cdef DdManager *dd = hash.manager;
    cdef DdHashItem *bucket;
    cdef DdHashItem **memlist
    cdef DdHashItem **nextmem;
    cdef unsigned int numBuckets = hash.numBuckets;
    for i in range(numBuckets):
        bucket = hash.bucket[i]
        while bucket != NULL:
            Cudd_RecursiveDerefZdd(dd, bucket.value)
            bucket = bucket.next
    memlist = hash.memoryList
    while (memlist != NULL):
        nextmem = <DdHashItem **> memlist[0]
        FREE(memlist)
        memlist = nextmem
    FREE(hash.bucket)
    FREE(hash)


cpdef set _c_support(Function u):
    """Compute support of `u`.

    @param u: ZDD node
    @type u: `Function`
    @rtype: `set`
    """
    zdd = u.bdd
    n = max(zdd._var_with_index) + 1
    cdef int *support
    support = <int *> PyMem_Malloc(n * sizeof(int))
    for i in range(n):
        support[i] = 0
    try:
        level = 0
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


cdef void _support(
        DdManager *mgr,
        int level,
        DdNode *u,
        int *support):
    """Recursively compute the support."""
    index = Cudd_ReadInvPermZdd(mgr, level)
    # terminal ?
    if u == DD_ZERO(mgr) or index == -1:
        return
    # visited ?
    if Cudd_IsComplement(u.next):
        return
    u_index = Cudd_NodeReadIndex(u)
    u_level = Cudd_ReadPermZdd(mgr, u_index)
    assert level <= u_level
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


cdef void _clear_markers(DdNode *u):
    """Recursively clear complementation bits."""
    if not Cudd_IsComplement(u.next):
        return
    u.next = Cudd_Regular(u.next)
    if cuddIsConstant(u):
        return
    v, w = Cudd_Regular(cuddE(u)), cuddT(u)
    _clear_markers(v)
    _clear_markers(w)


cpdef _test_call_dealloc(Function u):
    """Duplicates the code of `Function.__dealloc__`.

    For details read the docstring of the function
    `dd.cudd._test_call_dealloc`.
    """
    self = u
    # the code of `Function.__dealloc__` follows:
    if self._ref < 0:
        raise AssertionError((
            "The lower bound `_ref` on the node's "
            'reference count has value {_ref}, '
            'which is unexpected and should never happen. '
            'Was the value of `_ref` changed from outside '
            'this class?'
            ).format(_ref=self._ref))
    assert self._ref >= 0, self._ref
    if self._ref == 0:
        return
    # anticipate multiple calls to `__dealloc__`
    self._ref -= 1
    # deref
    Cudd_RecursiveDerefZdd(self.manager, self.node)
