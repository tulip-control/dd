"""Cython interface to ADD implementation in CUDD.

"ADD" abbreviates "algebraic decision diagrams".
Variable `__version__` equals CUDD's version string.

`agd` is used throughout as lowercase
Python variable name for algebraic
decision diagrams, because "add"
could be read as related to "addition".


Reference
=========
    Fabio Somenzi
    "CUDD: CU Decision Diagram Package"
    University of Colorado at Boulder
    v2.5.1, 2015
    <http://vlsi.colorado.edu/~fabio/>
"""
# This file has been released into the public domain.
#
import collections.abc as _abc
import itertools as _itr
import logging
import typing as _ty
import warnings

from cpython cimport bool as _py_bool
from cpython.mem cimport PyMem_Malloc, PyMem_Free
from libcpp cimport bool as _c_bool
from libc cimport stdint
from libc.stdio cimport FILE, fdopen, fopen, fclose

import dd._abc as _dd_abc
import dd._copy as _copy
import dd._parser as _parser
import dd._utils as _utils
import dd.bdd as _bdd


_Yes: _ty.TypeAlias = _py_bool
_Nat: _ty.TypeAlias = _dd_abc.Nat
_Cardinality: _ty.TypeAlias = _dd_abc.Cardinality
_NumberOfBytes: _ty.TypeAlias = _dd_abc.NumberOfBytes
_VariableName: _ty.TypeAlias = _dd_abc.VariableName
_Level: _ty.TypeAlias = _dd_abc.Level
_VariableLevels: _ty.TypeAlias = _dd_abc.VariableLevels
_Assignment: _ty.TypeAlias = _dd_abc.Assignment
_Renaming: _ty.TypeAlias = _dd_abc.Renaming
_Formula: _ty.TypeAlias = _dd_abc.Formula
_OPERATOR_SYMBOLS: _ty.Final = _dd_abc.ADD_OPERATOR_SYMBOLS
_OperatorSymbol: _ty.TypeAlias = _dd_abc.AgdOperatorSymbol
_UNARY_OPERATORS: _ty.Final[
    set[str]] = {
        '~', 'not', '!', 'log'}


cdef extern from 'cuddInt.h':
    cdef char* CUDD_VERSION
    cdef int CUDD_CONST_INDEX
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
    cdef void cuddHashTableQuit(
        DdHashTable *hash)
    cdef int cuddHashTableInsert1(
        DdHashTable *hash, DdNode *f,
        DdNode *value, ptrint count)
    cdef DdNode * cuddHashTableLookup1(
        DdHashTable *hash, DdNode *f)
    # cache
    cdef DdNode * cuddCacheLookup2(
        DdManager *table,
        DdNode * (*)(
            DdManager *, DdNode *, DdNode *),
        DdNode *f,
        DdNode *g)
    cdef void cuddCacheInsert2(
        DdManager *table,
        DdNode * (*)(
            DdManager *, DdNode *, DdNode *),
        DdNode *f,
        DdNode *g,
        DdNode *data)
    # node elements
    cdef DdNode *cuddUniqueInter(
        DdManager *unique,
        int index, DdNode *T, DdNode *E)
    cdef DdNode * cuddUniqueInter(
        DdManager *unique,
        int index, DdNode *T, DdNode *E)
    cdef _c_bool cuddIsConstant(
        DdNode *u)
    cdef DdNode *DD_ZERO(
        DdManager *mgr)
    cdef DdNode *DD_ONE(
        DdManager *mgr)
    cdef DdNode *cuddT(
        DdNode *u)  # top cofactors
    cdef DdNode *cuddE(
        DdNode *u)
    # BDD node elements
    cdef DdNode *Cudd_Not(
        DdNode *dd)
    cdef DdNode *Cudd_Regular(
        DdNode *u)
    cdef _c_bool Cudd_IsComplement(
        DdNode *u)
    # reference-counting
    cdef void cuddRef(
        DdNode *u)
    cdef void cuddDeref(
        DdNode *u)
    # realignment
    cdef int Cudd_RealignmentEnabled(
        DdManager *unique)
    cdef void Cudd_RealignEnable(
        DdManager *unique)
    cdef void Cudd_RealignDisable(
        DdManager *unique)
    cdef int Cudd_bddRealignmentEnabled(
        DdManager *unique)
    cdef void Cudd_bddRealignEnable(
        DdManager *unique)
    cdef void Cudd_bddRealignDisable(
        DdManager *unique)
cdef extern from 'cudd.h':
    # node
    ctypedef unsigned int DdHalfWord
    ctypedef double CUDD_VALUE_TYPE
    cdef struct DdNode:
        DdHalfWord index
        DdHalfWord ref
        DdNode *next
        CUDD_VALUE_TYPE value
    ctypedef DdNode *(*DD_AOP)(
        DdManager *, DdNode **, DdNode **)
    ctypedef DdNode *(*DD_MAOP)(
        DdManager *, DdNode *)
    # manager
    cdef DdManager *Cudd_Init(
        unsigned int numVars,
        unsigned int numVarsZ,
        unsigned int numSlots,
        unsigned int cacheSize,
        size_t maxMemory)
    # generator
    cdef struct DdGen
    # constants
    cdef DdNode *Cudd_ReadZero(
        DdManager *dd)
    cdef DdNode *Cudd_ReadOne(
        DdManager *dd)
    cdef DdNode *Cudd_addConst(
        DdManager *dd,
        CUDD_VALUE_TYPE c)
    cdef CUDD_VALUE_TYPE Cudd_V(
        DdNode *node)
    # variables
    cdef DdNode *Cudd_addNewVar(
        DdManager *dd)
    cdef DdNode *Cudd_addNewVarAtLevel(
        DdManager *dd, int level)
    cdef DdNode *Cudd_addIthVar(
        DdManager *dd, int index)
    cdef DdNode *Cudd_Support(
        DdManager *dd, DdNode *f)
    cdef int Cudd_ReadPerm(
        DdManager *dd, int index)
    cdef int Cudd_ReadInvPerm(
        DdManager *dd, int level)
    cdef unsigned int Cudd_NodeReadIndex(
        DdNode *u)
    cdef DdNode *Cudd_addComputeCube(
        )
    # substitution
    cdef DdNode *Cudd_addCompose(
        DdManager *dd,
        DdNode *f, DdNode *g, int v)
    cdef DdNode *Cudd_addVectorCompose(
        DdManager *dd,
        DdNode *f, DdNode **vector)
    cdef DdNode *Cudd_addGeneralVectorCompose(
        DdManager *dd,
        DdNode *f,
        DdNode **vector_on,
        DdNode **vector_off)
    cdef DdNode *Cudd_addNonSimCompose(
        DdManager *dd,
        DdNode *f, DdNode **vector)
    cdef DdNode *Cudd_addSwapVariables(
        DdManager *dd,
        DdNode *f,
        DdNode **x_vars, DdNode **y_vars,
        int n_vars)
    cdef DdNode *Cudd_addPermute(
        DdManager *dd,
        DdNode *f,
        int *permutation)
    # conversions between BDDs and ADDs
    cdef DdNode *Cudd_BddToAdd(
        DdManager *dd,
        DdNode *bdd_node)
    cdef DdNode *Cudd_addBddThreshold(
        DdManager *dd,
        DdNode *f,
        CUDD_VALUE_TYPE value)
    cdef DdNode *Cudd_addBddStrictThreshold(
        DdManager *dd,
        DdNode *f,
        CUDD_VALUE_TYPE value)
    cdef DdNode *Cudd_addBddInterval(
        DdManager *dd,
        DdNode *f,
        CUDD_VALUE_TYPE lower,
        CUDD_VALUE_TYPE upper)
    cdef DdNode *Cudd_addBddIthBit(
        DdManager *dd,
        DdNode *f, int bit)
    # ternary conditional
    cdef DdNode *Cudd_addIte(
        DdManager *dd,
        DdNode *f, DdNode *g, DdNode *h)
    cdef DdNode *Cudd_addIteConstant(
        DdManager *dd,
        DdNode *f, DdNode *g, DdNode *h)
        # The function `IteConstant` is defined in
        # Section 6.3.5 on page 240--243 of the book
        # "Logic synthesis and verification algorithms"
        # by Gary D. Hachtel and Fabio Somenzi
    # propositional operators for leaf nodes
    #
    # For conjunction, use `Cudd_addTimes`.
    cdef DdNode *Cudd_addOr(
        DdManager *dd,
        DdNode **f, DdNode **g)
    cdef DdNode *Cudd_addNor(
        DdManager *dd,
        DdNode **f, DdNode **g)
    cdef DdNode *Cudd_addXor(
        DdManager *dd,
        DdNode **f, DdNode **g)
    cdef DdNode *Cudd_addXnor(
        DdManager *dd,
        DdNode **f, DdNode **g)
    cdef DdNode *Cudd_addNand(
        DdManager *dd,
        DdNode **f, DdNode **g)
    # complementation
    cdef DdNode *Cudd_addCmpl(
        DdManager *dd, DdNode *f)
        # lambda x: 1 if f[x] == 0 else 0
    cdef DdNode *Cudd_addNegate(
        DdManager *dd, DdNode *f)
    # quantifiers
    cdef DdNode *Cudd_addExistAbstract(
        DdManager *dd,
        DdNode *f, DdNode *cube)
    cdef DdNode *Cudd_addUnivAbstract(
        DdManager *dd,
        DdNode *f, DdNode *cube)
    cdef DdNode *Cudd_addOrAbstract(
        DdManager *dd,
        DdNode *f, DdNode *cube)
    # operator application
    cdef DdNode *Cudd_addApply(
        DdManager *dd, DD_AOP op,
        DdNode *f, DdNode *g)
    cdef DdNode *Cudd_addMonadicApply(
        DdManager *dd, DD_MAOP op,
        DdNode *f)
    # arithmetic operators
    cdef int Cudd_addLeq(
        DdManager *dd,
        DdNode *f, DdNode *g)
    cdef DdNode *Cudd_addLog(
        DdManager *dd,
        DdNode *f)
    cdef DdNode *Cudd_addEvalConst(
        DdManager *dd,
        DdNode *f, DdNode *g)
    cdef DdNode *Cudd_addScalarInverse(
        DdManager *dd,
        DdNode *f, DdNode *epsilon)
    cdef DdNode *Cudd_addResidue(
        DdManager *dd,
        int n_bits, int modulus,
        int options, int top_var)
    cdef DdNode *Cudd_addHamming(
        DdManager *dd,
        DdNode **x_vars, DdNode *y_vars,
        int n_vars)
    cdef DdNode *Cudd_addPlus(
        DdManager *dd,
        DdNode **f, DdNode **g)
    cdef DdNode *Cudd_addMinus(
        DdManager *dd,
        DdNode **f, DdNode **g)
    cdef DdNode *Cudd_addTimes(
        DdManager *dd,
        DdNode **f, DdNode **g)
    cdef DdNode *Cudd_addDivide(
        DdManager *dd,
        DdNode **f, DdNode **g)
    cdef DdNode *Cudd_addMinimum(
        DdManager *dd,
        DdNode **f, DdNode **g)
    cdef DdNode *Cudd_addMaximum(
        DdManager *dd,
        DdNode **f, DdNode **g)
    cdef DdNode *Cudd_addFindMin(
        DdManager *dd,
        DdNode *f)
    cdef DdNode *Cudd_addFindMax(
        DdManager *dd,
        DdNode *f)
    cdef DdNode *Cudd_addDiff(
        DdManager *dd,
        DdNode **f, DdNode **g)
    cdef DdNode *Cudd_addThreshold(
        DdManager *dd,
        DdNode **f, DdNode **g)
    cdef DdNode *Cudd_addSetNZ(
        DdManager *dd,
        DdNode **f, DdNode **g)
    cdef DdNode *Cudd_addAgreement(
        DdManager *dd,
        DdNode **f, DdNode **g)
    cdef DdNode *Cudd_addOneZeroMaximum(
        DdManager *dd,
        DdNode **f, DdNode **g)
    cdef DdNode *Cudd_addXeqy(
        DdManager *dd,
        int n,
        DdNode **x, DdNode **y)
    cdef DdNode *Cudd_addRoundOff(
        DdManager *dd,
        DdNode *f, int n_digits)
    # matrix I/O
    cdef DdNode *Cudd_addHarwell(
        FILE *fp, DdManager *dd,
        DdNode **e,
        DdNode ***row_vars,
        DdNode ***column_vars,
        DdNode ***compl_row_vars,
        DdNode ***compl_col_vars,
        int *n_row_vars,
        int *n_column_vars,
        int n_rows,
        int n_columns,
        int row_start,
        int row_step,
        int column_start,
        int column_step,
        int verbosity_level)
    cdef DdNode *Cudd_addRead(
        FILE *fp, DdManager *dd,
        DdNode **e,
        DdNode ***row_vars,
        DdNode ***column_vars,
        DdNode ***compl_row_vars,
        DdNode ***compl_col_vars,
        int *n_row_vars,
        int *n_column_vars,
        int n_rows,
        int n_columns,
        int row_start,
        int row_step,
        int column_start,
        int column_step)
    # matrix multiplication
    cdef DdNode *Cudd_addMatrixMultiply(
        DdManager *dd,
        DdNode *a_matrix, DdNode *b_matrix,
        DdNode *z_vars, int nz)
    cdef DdNode *Cudd_addTimesPlus(
        DdManager *dd,
        DdNode *a_matrix, DdNode *b_matrix,
        DdNode *z_vars, int nz)
    cdef DdNode *Cudd_addWalsh(
        DdManager *dd,
        DdNode **x, DdNode **y,
        int n)
    # shortest-path computation
    cdef DdNode *Cudd_addTriangle(
        DdManager *dd,
        DdNode *f, DdNode *g,
        DdNode **z, int nz)
    cdef DdNode *Cudd_addOuterSum(
        DdManager *dd,
        DdNode *matrix,
        DdNode *a_vector,
        DdNode *b_vector)
    # other operators
    cdef DdNode *Cudd_addConstrain(
        DdManager *dd,
        DdNode *f, DdNode *c)
    cdef DdNode *Cudd_addRestrict(
        DdManager *dd,
        DdNode *f, DdNode *c)
    # counting
    cdef int Cudd_DagSize(
        DdNode *p_node)
    cdef double Cudd_CountMinterm(
        DdManager *dd,
        DdNode *node, int nvars)
    cdef int Cudd_Count(
        DdManager *dd, DdNode *P)
    cdef int Cudd_BddToCubeArray(
        DdManager *dd,
        DdNode *cube, int *array)
    # pick
    cdef DdGen *Cudd_FirstCube(
        DdManager *dd,
        DdNode *f, int **cube,
        CUDD_VALUE_TYPE *value)
    cdef int Cudd_NextCube(
        DdGen *gen, int **cube,
        CUDD_VALUE_TYPE *value)
    cdef int Cudd_IsGenEmpty(
        DdGen *gen)
    cdef int Cudd_GenFree(
        DdGen *gen)
    # info
    cdef int Cudd_PrintInfo(
        DdManager *dd, FILE *fp)
    cdef int Cudd_ReadSize(
        DdManager *dd)
    cdef long Cudd_ReadNodeCount(
        DdManager *dd)
    cdef long Cudd_ReadPeakNodeCount(
        DdManager *dd)
    cdef int Cudd_ReadPeakLiveNodeCount(
        DdManager *dd)
    cdef size_t Cudd_ReadMemoryInUse(
        DdManager *dd)
    cdef unsigned int Cudd_ReadSlots(
        DdManager *dd)
    cdef double Cudd_ReadUsedSlots(
        DdManager *dd)
    cdef double Cudd_ExpectedUsedSlots(
        DdManager *dd)
    cdef unsigned int Cudd_ReadCacheSlots(
        DdManager *dd)
    cdef double Cudd_ReadCacheUsedSlots(
        DdManager *dd)
    cdef double Cudd_ReadCacheLookUps(
        DdManager *dd)
    cdef double Cudd_ReadCacheHits(
        DdManager *dd)
    # reordering
    ctypedef enum Cudd_ReorderingType:
        pass
    cdef void Cudd_AutodynEnable(
        DdManager *unique,
        Cudd_ReorderingType method)
    cdef void Cudd_AutodynDisable(
        DdManager *unique)
    cdef int Cudd_ReorderingStatus(
        DdManager *unique,
        Cudd_ReorderingType *method)
    cdef int Cudd_ReduceHeap(
        DdManager *table,
        Cudd_ReorderingType heuristic,
        int minsize)
    cdef int Cudd_ShuffleHeap(
        DdManager *table, int *permutation)
    cdef void Cudd_SetSiftMaxSwap(
        DdManager *dd, int sms)
    cdef int Cudd_ReadSiftMaxSwap(
        DdManager *dd)
    cdef void Cudd_SetSiftMaxVar(
        DdManager *dd, int smv)
    cdef int Cudd_ReadSiftMaxVar(
        DdManager *dd)
    # The function `Cudd_ReduceHeap`
    # increments the counter `dd->reorderings`.
    # The function `Cudd_ReadReorderings`
    # reads this counter.
    cdef unsigned int Cudd_ReadReorderings(
        DdManager *dd)
    # The function `Cudd_ReduceHeap` adds
    # to the attribute `dd->reordTime`.
    # The function `Cudd_ReadReorderingTime`
    # reads this attribute.
    cdef long Cudd_ReadReorderingTime(
        DdManager *dd)
    # manager config
    cdef size_t Cudd_ReadMaxMemory(
        DdManager *dd)
    cdef size_t Cudd_SetMaxMemory(
        DdManager *dd, size_t maxMemory)
    cdef unsigned int Cudd_ReadMaxCacheHard(
        DdManager *dd)
    cdef unsigned int Cudd_ReadMaxCache(
        DdManager *dd)
    cdef void Cudd_SetMaxCacheHard(
        DdManager *dd, unsigned int mc)
    cdef double Cudd_ReadMaxGrowth(
        DdManager *dd)
    cdef void Cudd_SetMaxGrowth(
        DdManager *dd, double mg)
    cdef unsigned int Cudd_ReadMinHit(
        DdManager *dd)
    cdef void Cudd_SetMinHit(
        DdManager *dd, unsigned int hr)
    cdef void Cudd_EnableGarbageCollection(
        DdManager *dd)
    cdef void Cudd_DisableGarbageCollection(
        DdManager *dd)
    cdef int Cudd_GarbageCollectionEnabled(
        DdManager * dd)
    cdef unsigned int Cudd_ReadLooseUpTo(
        DdManager *dd)
    cdef void Cudd_SetLooseUpTo(
        DdManager *dd, unsigned int lut)
    # reference-counting
    cdef void Cudd_Ref(
        DdNode *n)
    cdef void Cudd_Deref(
        DdNode *n)
    cdef void Cudd_RecursiveDeref(
        DdManager *table, DdNode *n)
    cdef int Cudd_CheckZeroRef(
        DdManager *manager)
    # checks
    cdef int Cudd_DebugCheck(
        DdManager *table)
    cdef void Cudd_Quit(
        DdManager *unique)
    # manager config
    cdef void Cudd_EnableGarbageCollection(
        DdManager *dd)
    cdef void Cudd_DisableGarbageCollection(
        DdManager *dd)
    cdef int Cudd_GarbageCollectionEnabled(
        DdManager * dd)
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


class CouldNotCreateNode(
        Exception):
    pass


cdef class ADD:
    """Wrapper of CUDD manager.

    This CUDD manager stores algebraic decision diagrams.
    An algebraic decision diagram represents a function
    that maps Boolean-valued inputs to a floating-point
    value.

    Interface similar to `dd._abc.BDD` and `dd.cudd.BDD`.
    Variable names are strings.
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
        """Initialize ADD manager.

        @param memory_estimate: maximum allowed memory, in bytes.
        """
        self.manager = NULL  # prepare for `__dealloc__`
        total_memory = _utils.total_memory()
        default_memory = DEFAULT_MEMORY
        if memory_estimate is None:
            memory_estimate = default_memory
        if total_memory is None:
            pass
        elif memory_estimate >= total_memory:
            msg = (
                'Error in `dd.cudd_add.ADD`: '
                f'total physical memory is {total_memory} bytes, '
                f'but requested {memory_estimate} bytes. '
                'Please pass an amount of memory to '
                'the `ADD` constructor to avoid this error. '
                'For example, by instantiating '
                'the `ADD` manager as '
                f'`ADD({round(total_memory / 2)})`.\n'
                'If this error is raised when you run '
                'the tests of the package `dd`, '
                'then the tests can be run with '
                'a different initial memory by '
                'passing the command-line option '
                '`--default-memory` to the `pytest` '
                'test-runner. ')
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
                'failed to initialize CUDD `DdManager`')
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
        self.vars: set[_VariableName
            ] = set()
        self._index_of_var: dict[
            _VariableName,
            _Nat
            ] = dict()
        # `_var_with_index` is a bijection
        # and the inverse of `_index_of_var`
        self._var_with_index: dict[
            _Nat,
            _VariableName
            ] = dict()

    def __dealloc__(
            self
            ) -> None:
        if self.manager is NULL:
            raise RuntimeError(
                '`self.manager` is `NULL`, which suggests that '
                'an exception was raised inside the method '
                '`dd.cudd_add.ADD.__cinit__`.')
        # check reference counts
        n = Cudd_CheckZeroRef(self.manager)
        if n != 0:
            raise AssertionError(
                f'Still {n} nodes '
                'referenced upon shutdown.')
        # deallocate memory
        Cudd_Quit(self.manager)

    def __eq__(
            self:
                ADD,
            other:
                ADD |
                None
            ) -> _Yes:
        """Return `True` if `other` has same manager.

        If `other is None`, then return `False`.
        """
        if other is None:
            return False
        other_: ADD = other
        return self.manager == other_.manager

    def __ne__(
            self:
                ADD,
            other:
                ADD |
                None
            ) -> _Yes:
        """Return `True` if `other` has different manager.

        If `other is None`, then return `True`.
        """
        if other is None:
            return True
        other_: ADD = other
        return self.manager != other_.manager

    def __len__(
            self
            ) -> _Cardinality:
        """Return number of nodes with non-zero references."""
        return Cudd_CheckZeroRef(self.manager)

    def __contains__(
            self,
            u:
                Function
            ) -> _Yes:
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
            self
            ) -> str:
        d = self.statistics()
        s = (
            'Algebraic decision diagram (CUDD wrapper).\n'
            '\t {n} live nodes now\n'
            '\t {peak} live nodes at peak\n'
            '\t {n_vars} ADD variables\n'
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
                ADD,
            exact_node_count:
                _Yes=False
            ) -> dict[
                str,
                _ty.Any]:
        """Return `dict` with CUDD node counts and times.

        For details read the docstring of the method
        `dd.cudd.BDD.statistics`.
        """
        warnings.warn(
            "Changed in `dd` version 0.5.7: "
            "In the `dict` returned by the method "
            "`dd.cudd_add.ADD.statistics`, the value of the key `'mem'` "
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
            **kw
            ) -> dict[
                str,
                _ty.Any]:
        """Read and apply parameter values.

        For details read the docstring of the method
        `dd.cudd.BDD.configure`.
        """
        cdef int method
        cdef DdManager *mgr
        mgr = self.manager
        # read
        reordering = Cudd_ReorderingStatus(
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

    cpdef tuple succ(
            self,
            u:
                Function):
        """Return `(level, low, high)` for `u`."""
        if u.manager != self.manager:
            raise ValueError('`u.manager != self.manager`')
        level = u.level
        low = u.low
        high = u.high
        if low is not None and level >= low.level:
            raise AssertionError('low.level')
        if high is not None and level >= high.level:
            raise AssertionError('high.level')
        return level, low, high

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
                u._ref, 'method `dd.cudd_add.ADD.incref`',
                '`dd.cudd_add.Function`')
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

        For details read the docstring of the
        method `dd.cudd.BDD.decref`.

        @param recursive:
            if `True`, then call
            `Cudd_RecursiveDeref`,
            else call `Cudd_Deref`
        @param _direct:
            use this parameter only after
            reading the source code of the
            Cython file `dd/cudd_add.pyx`.
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
                u._ref, 'method `dd.cudd_add.ADD.decref`',
                '`dd.cudd_add.Function`')
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
        u = Cudd_addIthVar(self.manager, j)
        if u is NULL:
            raise RuntimeError(
                f'failed to add var "{var}"')
        Cudd_Ref(u)
        Cudd_RecursiveDeref(self.manager, u)
        self._add_var(var, j)
        return j

    cdef _add_var(
            self,
            var:
                _VariableName,
            index:
                _Nat):
        """Add to `self` a *new* variable named `var`."""
        if var in self.vars:
            raise ValueError(
                f'existing variable: {var}')
        if var in self._index_of_var:
            raise ValueError(
                f'variable already has '
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
            var:
                _VariableName):
        """Return node for variable named `var`."""
        if var not in self._index_of_var:
            raise ValueError(
                f'undeclared variable "{var}", '
                'the declared variables are:\n'
                f'{self._index_of_var}')
        index = self._index_of_var[var]
        r = Cudd_addIthVar(self.manager, index)
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
            _utils._raise_errors_about_var_at_level(
                self, level, j, CUDD_CONST_INDEX)
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
        """Return `dict` that maps variables to levels."""
        return {var: self.level_of_var(var)
                for var in self.vars}

    def _index_at_level(
            self,
            level:
                _Level
            ) -> (
                int |
                None):
        """Return index of CUDD variable at `level`."""
        j = Cudd_ReadInvPerm(self.manager, level)
        if j == -1:
            return None
        if j < 0:
            raise RuntimeError(
                f'unexpected value: {j}, '
                'returned from CUDD function '
                '`Cudd_ReadInvPerm`')
        return j

    cpdef _py_bool _gt_var_levels(
            self,
            level:
                _Level):
        """Return `True` if `level` > any variable level.

        This function calls the CUDD function
        `Cudd_ReadSize`. The way it works is
        similar to how the CUDD function
        `Cudd_ReadInvPerm` works.

        Note that the constant nodes are below
        all variable levels, so:

        ```python
        import dd.cudd_add

        agd = dd.cudd_add.ADD()
        assert agd._gt_var_levels(agd.zero.level)
        ```

        Read also the docstring of the method
        `_index_at_level` for more details.

        Raise `ValueError` if `level < 0`.

        @return:
            `True` if any CUDD variable has
            level < of given `level`
        """
        if level < 0:
            raise ValueError(
                'requires `level >= 0`, '
                f'got:  {level}')
        n_cudd_vars = Cudd_ReadSize(self.manager)
        if (n_cudd_vars < 0 or
                n_cudd_vars > CUDD_CONST_INDEX):
            self._assert_about_read_agd_size(n_cudd_vars)
        return level >= n_cudd_vars

    cpdef int _number_of_cudd_vars(
            self):
        """Return number of CUDD indices.

        This number can be larger than the
        `len(self.vars)`, because CUDD creates
        variable indices also for levels in
        between the declared variables,
        in case there are any gaps in the
        levels given when declaring the
        variables.

        Read also the docstring of the
        method `_index_at_level`.

        @rtype:
            `int` >= 0
        """
        n_cudd_vars = Cudd_ReadSize(self.manager)
        # this conditional avoids the method call
        # whenever unnecessary (an optimization)
        if (n_cudd_vars < 0 or
                n_cudd_vars > CUDD_CONST_INDEX):
            self._assert_about_read_agd_size(n_cudd_vars)
        return n_cudd_vars

    cpdef _assert_about_read_agd_size(
            self,
            n_cudd_vars:
                int):
        """Raise `RuntimeError`, depending on `n`.

        This method checks the value `n` returned
        by the CUDD function `Cudd_ReadSize`.
        """
        if n_cudd_vars < 0:
            raise RuntimeError(
                f'unexpected value: {n_cudd_vars}, '
                'returned from CUDD function '
                '`Cudd_ReadSize` '
                '(expected >= 0)')
        if n_cudd_vars > CUDD_CONST_INDEX:
            raise RuntimeError(
                f'unexpected value: {n_cudd_vars}, '
                'returned from CUDD function '
                '`Cudd_ReadSize` '
                '(expected <= CUDD_CONST_INDEX = '
                f'{CUDD_CONST_INDEX})')

    def reorder(
            self,
            var_order:
                _VariableLevels |
                None=None
            ) -> None:
        """Reorder variables to `var_order`.

        If `var_order` is `None`, then invoke sifting.
        """
        if var_order is None:
            Cudd_ReduceHeap(self.manager, CUDD_REORDER_SIFT, 1)
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
            r = Cudd_ShuffleHeap(self.manager, p)
        finally:
            PyMem_Free(p)
        if r != 1:
            raise RuntimeError('Failed to reorder.')

    def _enable_reordering(
            self
            ) -> None:
        """Enable dynamic reordering of ADDs."""
        Cudd_AutodynEnable(self.manager, CUDD_REORDER_SIFT)

    def _disable_reordering(
            self
            ) -> None:
        """Disable dynamic reordering of ADDs."""
        Cudd_AutodynDisable(self.manager)

    cpdef set support(
            self,
            u:
                Function):
        """Return `set` of variables that `u` depends on.

        These are the variables that the function
        represented by the ADD with root `u` depends on.
        """
        if self.manager != u.manager:
            raise ValueError(
                '`u.manager != self.manager`')
        r = Cudd_Support(self.manager, u.node)
        cube = wrap(self, r)
        support = self._cube_to_dict(cube)
        # constant ?
        if not support:
            return set()
        # must be a conjunction of variables
        for value in support.values():
            if value is True:
                continue
            raise AssertionError(support)
        return set(support)

    def _copy_bdd_vars(
            self,
            bdd
            ) -> None:
        """Copy BDD to ADD variables."""
        raise NotImplementedError()
        Cudd_VarsFromBddVars(self.manager, 1)

    def _bdd_to_agd(
            self,
            u
            ) -> Function:
        """Copy BDD `u` to a ADD in `self`.

        @param u:
            node in a `dd.cudd.BDD` manager
        @type u:
            `dd.cudd.Function`
        """
        raise NotImplementedError()
        r: DdRef
        bdd = u.bdd
        u_ = bdd.copy(u, self)
        r = <DdRef>u_.node
        r = Cudd_BddToAdd(self.manager, r)
        return wrap(self, r)

    def copy(
            self,
            u:
                Function,
            other):
        """Transfer ADD with root `u` to `other`.

        If `other` is a BDD manager,
        then `u` must have leaf nodes in
        the set `{0, 1}`.

        @param other: `ADD` or `BDD` manager
        @type other:
            | `dd.cudd_add.ADD`
            | `dd.cudd.BDD`
            | `dd.autoref.BDD`
        @rtype:
            | `dd.cudd_add.Function`
            | `dd.cudd.Function`
            | `dd.autoref.Function`
        """
        raise NotImplementedError()
        return _copy.copy_agd(u, other)

    cpdef Function let(
            self,
            definitions:
                _Renaming |
                _Assignment |
                dict[
                    _VariableName,
                    Function],
            u:
                Function):
        """Replace variables with `definitions` in `u`.

        @param definitions:
            maps variable names
            to either:
            - Boolean values, or
            - variable names, or
            - references to ADD nodes
        """
        if self.manager != u.manager:
            raise ValueError(
                '`u.manager != self.manager`')
        if not definitions:
            logger.warning(
                'Call to `ADD.let` with no effect, '
                'because the dictionary `definitions` '
                'is empty.')
            return u
        var = next(iter(definitions))
        value = definitions[var]
        if isinstance(value, _py_bool):
            return self._cofactor(u, definitions)
        elif isinstance(value, Function):
            return self._compose(u, definitions)
        try:
            value + 's'
        except TypeError:
            raise ValueError(
                'Value must be variable name as `str`, '
                'or Boolean value as `bool`, '
                f'or ADD node as `int`. Got: {value}')
        return self._rename(u, definitions)

    cpdef Function _cofactor(
            self,
            u:
                Function,
            var_values:
                _Assignment):
        """Substitute constants for variables."""
        if self.manager != u.manager:
            raise ValueError(u)
        let = dict()
        for var, value in var_values.items():
            p = self.constant(value)
            let[var] = p
        return self._compose(u, let)

    cpdef Function _rename(
            self,
            u:
                Function,
            var_renames:
                _Renaming):
        """Return node from renaming variables in `u`.

        The renaming is defined by the
        `dict`-valued argument `var_renames`.
        Each variable `name` that is a key of
        `var_renames` and in the support of `u`
        is substituted by the variable
        `var_renames[name]`.

        @param var_renames:
            maps variable names to variable names
        """
        if self.manager != u.manager:
            raise ValueError(
                '`u.manager != self.manager`')
        rename = {
            k: self.var(v)
            for k, v in var_renames.items()}
        return self._compose(u, rename)

    cpdef Function _compose(
            self,
            u:
                Function,
            var_sub:
                dict[
                    _VariableName,
                    Function]):
        """Substitute ADDs for variables."""
        n = len(var_sub)
        if n == 0:
            logger.warning(
                '`ADD._compose` call without '
                'any effect')
            return u
        if n > 1:
            return self._multi_compose(
                u, var_sub)
        if n != 1:
            raise ValueError(n)
        var, g = next(iter(var_sub.items()))
        return self._unary_compose(
            u, var, g)

    cdef Function _unary_compose(
            self,
            u:
                Function,
            var:
                _VariableName,
            g:
                Function):
        """Substitution of one variable."""
        if u.manager != self.manager:
            raise ValueError(
                '`u.manager != self.manager`')
        if g.manager != self.manager:
            raise ValueError(
                '`g.manager != self.manager`')
        index = self._index_of_var[var]
        r = Cudd_addCompose(
            self.manager,
            u.node, g.node, index)
        if r is NULL:
            raise RuntimeError(
                'compose falied')
        return wrap(self, r)

    cdef Function _multi_compose(
            self,
            u:
                Function,
            var_sub:
                dict[
                    _VariableName,
                    Function]):
        """Substitution of multiple variables."""
        if u.manager != self.manager:
            raise ValueError(
                '`u.manager != self.manager')
        n_cudd_vars = self._number_of_cudd_vars()
        if n_cudd_vars <= 0:
            raise AssertionError(n_cudd_vars)
        x = <DdRef *> PyMem_Malloc(
            n_cudd_vars *sizeof(DdRef))
        g: Function
        for var in self.vars:
            index = self._index_of_var[var]
            if var in var_sub:
                g = var_sub[var]
                if g.manager != self.manager:
                    raise ValueError(
                        'value given for '
                        f'variable `{var}` '
                        'is not in an ADD '
                        'in this manager')
                x[index] = g.node
            else:
                x[index] = Cudd_addIthVar(
                    self.manager, index)
        try:
            r = Cudd_addVectorCompose(
                self.manager, u.node, x)
        finally:
            PyMem_Free(x)
        return wrap(self, r)

    cpdef Function ite(
            self,
            g:
                Function,
            u:
                Function,
            v:
                Function):
        """Ternary conditional `IF g THEN u ELSE v`.

        Calls the C function `Cudd_addIte`.
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
        r = Cudd_addIte(
            self.manager, g.node, u.node, v.node)
        if r is NULL:
            raise CouldNotCreateNode()
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
                f'not in: {self.vars}')
        level = self.level_of_var(var)
        if level >= low.level:
            raise ValueError(
                level, low.level, 'low.level')
        if level >= high.level:
            raise ValueError(
                level, high.level, 'high.level')
        r: DdRef
        index = self._index_of_var[var]
        if high == self.zero:
            r = low.node
        else:
            r = cuddUniqueInter(
                self.manager, index,
                high.node, low.node)
            if r is NULL:
                raise CouldNotCreateNode()
        f = wrap(self, r)
        if level > f.level:
            raise AssertionError(
                level, f.level, 'f.level')
        return f

    cdef DdRef _find_or_add(
            self,
            index:
                _Nat,
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
        r = cuddUniqueInter(
            self.manager, index, high, low)
        if r is NULL:
            raise AssertionError('r is NULL')
        return r

    cpdef tuple _top_cofactor(
            self,
            u:
                Function,
            level:
                _Level):
        """Return cofactor at `level`."""
        u_level = u.level
        if level > u_level:
            raise ValueError(
                (level, u_level))
        if level < u_level:
            return (u, self.zero)
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
            nvars:
                _Cardinality |
                None=None
            ) -> _Cardinality:
        """CUDD implementation of `self.count`."""
        # returns different results
        if u.manager != self.manager:
            raise ValueError(
                'node `u` is from a different manager')
        n = len(self.support(u))
        if nvars is None:
            nvars = n
        if nvars < n:
            raise ValueError(
                (nvars, n))
        r = Cudd_CountMinterm(
            self.manager, u.node, nvars)
        if r == CUDD_OUT_OF_MEM:
            raise RuntimeError(
                'CUDD out of memory')
        if r == float('inf'):
            raise RuntimeError(
                'overflow of integer type double')
        return r

    def pick(
            self,
            u:
                Function,
            care_vars:
                _abc.Iterable[
                    _VariableName] |
                None=None,
            with_values:
                _Yes=False
            ) -> (
                _Assignment |
                None):
        """Return a single satisfying assignment as `dict`.

        For details, read the docstrings of
        the methods:
        - `dd.autoref.BDD.pick`
        - `dd.autoref.BDD.pick_iter`

        @param with_values:
            if `True`,
            then return a tuple `(assignment, value)`,
            where:
            - `value` is the number that the
              algebraic decision diagram maps
              the assignment `var_values` to.
        """
        # TODO: with_values
        return next(self.pick_iter(u, care_vars), None)

    def pick_iter(
            self,
            u:
                Function,
            care_vars:
                _abc.Iterable[
                    _VariableName] |
                None=None,
            with_values:
                _Yes=False
            ) -> _abc.Iterator[
                _Assignment]:
        """Return iterator over satisfying assignments.

        The returned iterator is generator-based.

        For details, read the docstrings of
        the methods:
        - `dd.cudd_add.ADD.pick`
        - `dd.autoref.BDD.pick`
        - `dd.autoref.BDD.pick_iter`
        """
        if self.manager != u.manager:
            raise ValueError(
                '`u` is from a different manager')
        support = self.support(u)
        if care_vars is None:
            care_vars = support
        missing = support.difference(care_vars)
        if missing:
            logger.warning(
                'Missing bits:  '
                rf'support \ care_vars = {missing}')
        config = self.configure(reordering=False)
        cdef int *cube
        cdef double value
        gen = Cudd_FirstCube(
            self.manager, u.node, &cube, &value)
        if gen is NULL:
            raise RuntimeError(
                'enumeration of ADD assignments '
                'failed: the C function '
                '`Cudd_FirstCube` returned `NULL` ')
        try:
            r = 1
            while Cudd_IsGenEmpty(gen) == 0:
                if r != 1:
                    raise RuntimeError(
                        'C function `Cudd_IsGenEmpty` '
                        'indicates that gen is '
                        'nonempty, but no next cube')
                var_values = _cube_array_to_dict(
                    cube, self._index_of_var)
                if not set(var_values).issubset(support):
                    raise AssertionError(
                        set(var_values).difference(support))
                for m in _bdd._enumerate_minterms(
                        var_values, care_vars):
                    yield m
                r = Cudd_NextCube(gen, &cube, &value)
        finally:
            Cudd_GenFree(gen)
        self.configure(reordering=config['reordering'])

    cpdef Function apply(
            self,
            op:
                _OperatorSymbol,
            u:
                Function,
            v:
                _ty.Optional[Function]
                =None,
            w:
                _ty.Optional[Function]
                =None):
        r"""Return as `Function` the result of applying `op`.

        @type op:
            `str` in
            - `'~'`, `'not'`, `'!'`
              (C-style complementation)
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
            - `'nand'`
            - `r'\A'`, `'forall'`
              (universal quantification)
            - `r'\E'`, `'exists'`
              (existential quantification)
            - `'ite'`
              (ternary conditional: if-then-else)
            - `'+'`
              (addition of numbers)
            - `'-'`
              (subtraction of numbers)
            - `'*'`
              (multiplication of numbers)
            - `'/'`
              (division of numbers)
            - `'log'`
              (natural logarithm)
        """
        _utils.assert_operator_arity(op, v, w, 'agd')
        if self.manager != u.manager:
            raise ValueError(
                'node `u` is from different ADD manager')
        if v is not None and self.manager != v.manager:
            raise ValueError(
                'node `v` is from different ADD manager')
        if w is not None and self.manager != w.manager:
            raise ValueError(
                'node `w` is from different ADD manager')
        r: DdRef
        neg_node: DdRef
        t: Function
        cdef DdManager *mgr
        mgr = u.manager
        # unary
        r = NULL
        if op in ('~', 'not', '!'):
            r = Cudd_addCmpl(mgr, u.node)
        elif op == 'log':
            r = Cudd_addLog(mgr, u.node)
        # binary
        elif op in ('and', '/\\', '&', '&&'):
            r = Cudd_addApply(
                mgr, Cudd_addTimes,
                u.node, v.node)
        elif op in ('or', r'\/', '|', '||'):
            r = Cudd_addApply(
                mgr, Cudd_addOr,
                u.node, v.node)
        elif op in ('#', 'xor', '^'):
            r = Cudd_addApply(
                mgr, Cudd_addXor,
                u.node, v.node)
        elif op == 'xnor':
            r = Cudd_addApply(
                mgr, Cudd_addXnor,
                u.node, v.node)
        elif op == 'nand':
            r = Cudd_addApply(
                mgr, Cudd_addNand,
                u.node, v.node)
        elif op in ('=>', 'implies', '->'):
            r = Cudd_addIte(
                mgr, u.node, v.node,
                Cudd_ReadOne(mgr))
        elif op in ('<=>', 'equiv', '<->'):
            r = Cudd_addApply(
                mgr, Cudd_addXnor,
                u.node, v.node)
        elif op in (r'\A', 'forall'):
            r = Cudd_addUnivAbstract(
                mgr, v.node, u.node)
        elif op in (r'\E', 'exists'):
            r = Cudd_addExistAbstract(
                mgr, v.node, u.node)
        elif op == '+':
            r = Cudd_addApply(
                mgr, Cudd_addPlus,
                u.node, v.node)
        elif op == '-':
            r = Cudd_addApply(
                mgr, Cudd_addMinus,
                u.node, v.node)
        elif op == '*':
            r = Cudd_addApply(
                mgr, Cudd_addTimes,
                u.node, v.node)
        elif op == '/':
            r = Cudd_addApply(
                mgr, Cudd_addDivide,
                u.node, v.node)
        elif op == '<':
            # TODO: is there any better function
            # for this available in CUDD ?
            raise NotImplementedError('<')
        elif op == '<=':
            raise NotImplementedError('<=')
        elif op == '>':
            raise NotImplementedError('>')
        elif op == '>=':
            raise NotImplementedError('>=')
        elif op == '==':
            raise NotImplementedError('==')
        elif op == '=':
            raise NotImplementedError('=')
        elif op == 'min':
            r = Cudd_addApply(
                mgr, Cudd_addMinimum,
                u.node, v.node)
        elif op == 'max':
            r = Cudd_addApply(
                mgr, Cudd_addMaximum,
                u.node, v.node)
        elif op == 'threshold':
            r = Cudd_addApply(
                mgr, Cudd_addThreshold,
                u.node, v.node)
        elif op == 'diff':
            raise ValueError(
                'To avoid confusion between '
                'subtraction of numbers, '
                '`Cudd_addDiff`, '
                'and logical difference as '
                'in `dd.cudd.BDD`, '
                "`'diff'` is not an operator "
                'name for the method '
                '`dd.cudd_add.ADD.apply` '
                '(i.e., not a value of '
                'the argument `op`)')
        elif op == '01_max':
            raise NotImplementedError('01_max')
        elif op == 'agreement':
            raise NotImplementedError('agreement')
        elif op == 'set_nz':
            raise NotImplementedError('set_nz')
        elif op == 'x_eq_y':
            raise NotImplementedError('x_eq_y')
        elif op == '@':
            raise NotImplementedError('@')
            # Cudd_addMatrixMultiply
        elif op == 'matmul_2':
            raise NotImplementedError('matmul_2')
            # Cudd_addTimesPlus
        # ternary
        elif op == 'ite':
            r = Cudd_addIte(
                mgr, u.node, v.node, w.node)
        else:
            raise AssertionError(op)
        # TODO: consider whether and how to
        # provide an interface to additional CUDD functions
        if r is NULL:
            config = self.configure()
            raise RuntimeError(
                'CUDD appears to have run out of memory.\n'
                f'Computing the operator {op}\n.'
                'Current settings for upper bounds:\n'
                f'    max memory = {config["max_memory"]} bytes\n'
                f'    max cache = {config["max_cache_hard"]} entries')
        res = wrap(self, r)
        if op in (r'\A', 'forall', r'\E', 'exist'):
            Cudd_RecursiveDeref(mgr, r)
        return res

    cpdef Function _add_int(
            self,
            i:
                int):
        """Return node from integer `i`."""
        u: DdRef
        if i in (0, 1):
            raise ValueError(
                rf'{i} \in {{0, 1}}')
        # invert `Function.__int__`
        if 2 <= i:
            i -= 2
        u = <DdRef><stdint.uintptr_t>i
        return wrap(self, u)

    cpdef Function cube(
            self,
            dvars:
                _abc.Iterable[_VariableName] |
                _Assignment):
        """Return conjunction of variables in `dvars`.

        If `dvars` is a `dict`, then a Boolean value
        `False` results in a negated variable.
        """
        r = self.one
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
        cube = self.cube(set(qvars))
        if forall:
            r = Cudd_addUnivAbstract(
                self.manager, u.node, cube.node)
        else:
            r = Cudd_addExistAbstract(
                self.manager, u.node, cube.node)
        return wrap(self, r)

    cpdef Function forall(
            self,
            variables:
                _abc.Iterable[
                    _VariableName],
            u:
                Function):
        """Quantify `variables` in `u` universally.

        Wraps method `quantify`.
        """
        return self.quantify(u, variables, forall=True)

    cpdef Function exist(
            self,
            variables:
                _abc.Iterable[
                    _VariableName],
            u:
                Function):
        """Quantify `variables` in `u` existentially.

        Wraps method `quantify`.
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
                f'`len(self.vars) == {n}` '
                'but '
                f'`len(self._var_with_index) == {m}`\n'
                'self.vars = '
                f'{self.vars}\n'
                'self._var_with_index = '
                f'{self._var_with_index}')
        if m != k:
            raise AssertionError(
                f'`len(self._var_with_index) == {m}` '
                'but '
                f'`len(self._index_of_var) == {k}`\n'
                'self._var_with_index = '
                f'{self._var_with_index}\n'
                'self._index_of_var = '
                f'{self._index_of_var}')
        if set(self.vars) != set(self._index_of_var):
            raise AssertionError(
                '`set(self.vars) != '
                'set(self._index_of_var)`\n'
                'self.vars = '
                f'{self.vars}\n'
                'self._index_of_var = '
                f'{self._index_of_var}')
        if set(self._var_with_index) != set(
                self._index_of_var.values()):
            raise AssertionError(
                '`set(self._var_with_index) != '
                'set(self._index_of_var.values())`\n'
                'self._var_with_index = '
                f'{self._var_with_index}\n'
                'self._index_of_var = '
                f'{self._index_of_var}')

    def add_expr(
            self,
            expr:
                _Formula
            ) -> Function:
        """Return node for `str` expression `e`."""
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
                dict[int, _Formula]):
        """Recursively compute expression of `u`.

        This is the C implementation.
        The method `_to_expr_py` is
        a Python implementation used
        for testing this method.
        """
        if cuddIsConstant(u):
            value = Cudd_V(u)
            return str(value)
        uid = _ddnode_to_int(u)
        if uid in cache:
            return cache[uid]
        v = cuddE(u)
        w = cuddT(u)
        p = self._to_expr(v, cache)
        q = self._to_expr(w, cache)
        index = u.index
        var = self.var_at_level(index)
        if p == '0.0' and q == '1.0':
            expr = var
        else:
            expr = f'ite({var}, {q}, {p})'
        cache[uid] = expr
        return expr

    cpdef str _to_expr_py(
            self,
            u:
                Function,
            cache:
                dict[int, _Formula]):
        """Recursively compute an expression.

        This method is a Python implementation,
        which is used for testing.
        A C implementation is in the method
        `_to_expr`.
        """
        if u.var is None:
            value = self.value_of(u)
            return str(value)
        uid = int(u)
        if uid in cache:
            return cache[uid]
        v, w = u.low, u.high
        p = self._to_expr_py(v, cache)
        q = self._to_expr_py(w, cache)
        var = self.var_at_level(u.level)
        if p == '0.0' and q == '1.0':
            expr = var
        else:
            expr = f'ite({var}, {q}, {p})'
        cache[uid] = expr
        return expr

    cpdef dump(
            self,
            filename:
                str,
            roots:
                list[Function],
            filetype:
                _dd_abc.ImageFileType |
                None=None):
        """Write ADD as a diagram to file `filename`.

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

        Only the ADD manager nodes that are reachable from the
        ADD references in `roots` are included in the diagram.

        @param filename:
            file name,
            e.g., `"diagram.pdf"`
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
                'unknown file type "{filetype}", '
                'the method `dd.cudd_add.ADD.dump` '
                'supports writing diagrams as '
                'PDF, PNG, or SVG files.')

    def _dump_figure(
            self,
            roots:
                list[Function],
            filename:
                str,
            filetype:
                _dd_abc.ImageFileType,
            **kw
            ) -> None:
        """Write BDDs to `filename` as figure."""
        raise NotImplementedError()
        g = _to_dot(roots)
        g.dump(
            filename,
            filetype=filetype,
            **kw)

    cpdef load(
            self,
            filename:
                str):
        raise NotImplementedError()

    # Same with the method `dd.cudd.BDD._cube_to_dict`.
    # TODO: create a `pxd` and move the common
    # functions to a shared `pyx` file ?
    cpdef dict _cube_to_dict(
            self,
            f:
                Function):
        """Recurse to collect indices of support variables."""
        if f.manager != self.manager:
            raise ValueError(
                '`f.manager != self.manager`')
        n = self._number_of_cudd_vars()
        cdef int *x
        x = <int *> PyMem_Malloc(n * sizeof(DdRef))
        try:
            Cudd_BddToCubeArray(self.manager, f.node, x)
            d = _cube_array_to_dict(x, self._index_of_var)
        finally:
            PyMem_Free(x)
        return d

    def constant(
            self,
            number:
                float
            ) -> Function:
        """Return leaf node for `number`.

        Relevant method: `ADD.value_of`.

        @param number:
            a number that can be represented by
            `double` in C, within CUDD
        @return:
            ADD node that represents `number`
        """
        r = Cudd_addConst(
            self.manager, number)
        return wrap(self, r)

    def value_of(
            self,
            u:
                Function
            ) -> float:
        """Return value of leaf `node`.

        Relevant method `ADD.constant`.

        Raise `ValueError` if `node`
        is nonleaf.
        """
        if cuddIsConstant(u.node) != 1:
            raise ValueError(
                '`u` is nonleaf.'
                f'specifically: `u = {u!r}`')
        return Cudd_V(u.node)

    @property
    def zero(
            self
            ) -> Function:
        """Boolean value FALSE.

        Relevant property: `ADD.one`.
        Relevant method: `ADD.constant`.
        """
        r = Cudd_ReadZero(self.manager)
        return wrap(self, r)

    @property
    def one(
            self
            ) -> Function:
        """Boolean value TRUE.

        Relevant property: `ADD.zero`.
        Relevant method: `ADD.constant`.
        """
        r = Cudd_ReadOne(self.manager)
        return wrap(self, r)


cdef Function wrap(
        bdd:
            ADD,
        node:
            DdRef):
    """Return a `Function` that wraps `node`."""
    # because `@classmethod` unsupported
    f = Function()
    f.init(node, bdd)
    return f


cdef class Function:
    """Wrapper of ADD `DdNode` from CUDD.

    For details, read the docstring of the
    class `dd.cudd.Function`.
    """

    __weakref__: object
    # cdef public ADD bdd
    cdef public ADD agd
    cdef DdManager *manager
    node: DdRef
    cdef public int _ref

    cdef init(
            self,
            node:
                DdRef,
            agd:
                ADD):
        if node is NULL:
            raise ValueError(
                '`DdNode *node` is `NULL` pointer.')
        self.agd = agd
        # self.bdd = agd  # Keep this attribute
            # for writing common algorithms for
            # BDDs and ADDs, where possible.
        self.manager = agd.manager
        self.node = node
        self._ref = 1  # lower bound on reference count
        Cudd_Ref(node)

    def __hash__(
            self
            ) -> int:
        return int(self)

    @property
    def _index(
            self
            ) -> int:
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
        if cuddIsConstant(self.node):
            return None
        return self.agd._var_with_index[self._index]

    @property
    def level(
            self
            ) -> _Level:
        """Level where this node currently is."""
        index = self._index
        return Cudd_ReadPerm(self.manager, index)

    @property
    def ref(
            self
            ) -> _Cardinality:
        """Reference count of node."""
        return self.node.ref

    @property
    def low(
            self
            ) -> (
                Function |
                None):
        """Return "else" node as `Function`."""
        if cuddIsConstant(self.node):
            return None
        u: DdRef
        u = cuddE(self.node)
        return wrap(self.agd, u)

    @property
    def high(
            self
            ) -> (
                Function |
                None):
        """Return "then" node as `Function`."""
        if cuddIsConstant(self.node):
            return None
        u: DdRef
        u = cuddT(self.node)
        return wrap(self.agd, u)

    @property
    def negated(
            self
            ) -> _Yes:
        raise Exception(
            'No complemented edges for ADDs in CUDD, '
            'only for BDDs.')

    @property
    def support(
            self:
                ADD
            ) -> set[_VariableName]:
        """Return `set` of variables in support."""
        return self.agd.support(self)

    def __dealloc__(
            self
            ) -> None:
        # when changing this method,
        # update also the function
        # `_test_call_dealloc` below
        if self._ref < 0:
            raise AssertionError(
                "The lower bound `_ref` on the node's "
                f'reference count has value {self._ref}, '
                'which is unexpected and should never happen. '
                'Was the value of `_ref` changed from outside '
                'this class?')
        assert self._ref >= 0, self._ref
        if self._ref == 0:
            return
        if self.node is NULL:
            raise AssertionError(
                'The attribute `node` is a `NULL` pointer. '
                'This is unexpected and should never happen. '
                'Was the value of `_ref` changed from outside '
                'this class?')
        # anticipate multiple calls to `__dealloc__`
        self._ref -= 1
        # deref
        Cudd_RecursiveDeref(self.manager, self.node)
        # avoid future access to deallocated memory
        self.node = NULL

    def __int__(
            self
            ) -> int:
        # inverse is `ADD._add_int`
        if sizeof(stdint.uintptr_t) != sizeof(DdRef):
            raise RuntimeError(
                'expected `sizeof(stdint.uintptr_t) == '
                'sizeof(DdNode *)`')
        i = <stdint.uintptr_t>self.node
        # 0, 1 are true and false in logic syntax
        if 0 <= i:
            i += 2
        if i in (0, 1):
            raise AssertionError(i)
        return i

    def __repr__(
            self
            ) -> str:
        return (
            f'<dd.cudd_add.Function at {hex(id(self))}, '
            'wrapping a (ADD) DdNode with '
            f'var index: {self._index}, '
            f'ref count: {self.ref}, '
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
        """Return number of ADD nodes.

        This is the number of ADD nodes that
        are reachable from this ADD reference,
        i.e., with `self` as root.
        """
        return len(self)

    def __matmul__(
            self:
                Function,
            other:
                Function
            ) -> Function:
        supp_self = self.support
        supp_other = other.support
        vrs = supp_self & supp_other
        raise NotImplementedError()
        vrs_u = vars_to_ddnode(vrs)  # TODO
        r = Cudd_addMatrixMultiply(
            self.manager,
            self.node, other.node,
            vrs_u, len(vrs))
        return _wrap(self.agd, r)

    def __eq__(
            self:
                Function,
            other:
                Function |
                None
            ) -> _Yes:
        if other is None:
            return False
        other_: Function = other
        if self.manager != other_.manager:
            raise ValueError(
                '`self.manager != other_.manager`')
        return self.node == other_.node

    def __ne__(
            self:
                Function,
            other:
                Function |
                None
            ) -> _Yes:
        if other is None:
            return True
        other_: Function = other
        if self.manager != other_.manager:
            raise ValueError(
                '`self.manager != other_.manager`')
        return self.node != other_.node

    # TODO: check that the below are correct,
    # and that they raise the intended
    # exceptions when any argument
    # is not a 0-1 ADD

    def __le__(
            self:
                Function,
            other:
                Function
            ) -> _Yes:
        if self.manager != other.manager:
            raise ValueError(
                '`self.manager != other.manager`')
        return (other | ~ self) == self.agd.one

    def __lt__(
            self:
                Function,
            other:
                Function
            ) -> _Yes:
        if self.manager != other.manager:
            raise ValueError(
                '`self.manager != other.manager`')
        return (
            self.node != other.node and
            (other | ~ self) == self.agd.one)

    def __ge__(
            self:
                Function,
            other:
                Function
            ) -> _Yes:
        if self.manager != other.manager:
            raise ValueError(
                '`self.manager != other.manager`')
        return (self | ~ other) == self.agd.one

    def __gt__(
            self:
                Function,
            other:
                Function
            ) -> _Yes:
        if self.manager != other.manager:
            raise ValueError(
                '`self.manager != other.manager`')
        return (
            self.node != other.node and
            (self | ~ other) == self.agd.one)

    def __invert__(
            self
            ) -> _Yes:
        r: DdRef
        r = Cudd_addCmpl(
            self.manager, self.node)
        return wrap(self.agd, r)

    def __and__(
            self:
                Function,
            other:
                Function
            ) -> Function:
        if self.manager != other.manager:
            raise ValueError(
                '`self.manager != other.manager`')
        r = Cudd_addApply(
            self.manager, Cudd_addTimes,
            self.node, other.node)
        return wrap(self.agd, r)

    def __or__(
            self:
                Function,
            other:
                Function
            ) -> Function:
        if self.manager != other.manager:
            raise ValueError(
                '`self.manager != other.manager`')
        r = Cudd_addApply(
            self.manager, Cudd_addOr,
            self.node, other.node)
        return wrap(self.agd, r)

    def implies(
            self:
                Function,
            other:
                Function
            ) -> Function:
        if self.manager != other.manager:
            raise ValueError(
                '`self.manager != other.manager`')
        r = Cudd_addIte(
            self.manager,
            self.node, other.node,
            Cudd_ReadOne(self.manager))
        return wrap(self.agd, r)

    def equiv(
            self:
                Function,
            other:
                Function
            ) -> Function:
        return self.agd.apply('<=>', self, other)

    def let(
            self:
                Function,
            **definitions:
                _VariableName |
                int |
                Function
            ) -> Function:
        return self.agd.let(definitions, self)

    def exist(
            self:
                Function,
            *variables:
                _VariableName
            ) -> Function:
        return self.agd.exist(variables, self)

    def forall(
            self:
                Function,
            *variables:
                _VariableName
            ) -> Function:
        return self.agd.forall(variables, self)

    def pick(
            self:
                Function,
            care_vars:
                _abc.Iterable[
                    _VariableName] |
                None=None
            ) -> (
                _Assignment |
                None):
        return self.agd.pick(self, care_vars)

    def count(
            self:
                Function,
            nvars:
                _Cardinality |
                None=None
            ) -> _Assignment:
        return self.agd.count(self, nvars)


# Similar to the function `dd.cudd._cube_array_to_dict`
cdef dict _path_array_to_dict(
        int *x,
        index_of_var:
            dict[
                _VariableName,
                _Nat]):
    """Return assignment from array of literals `x`."""
    d = dict()
    for var, j in index_of_var.items():
        b = x[j]
        if b == 2:  # absence of ADD node
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
            dict[
                _VariableName,
                _Nat]):
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
    """Return graph for the ADD rooted at `u`.

    Calling this function requires first installing `networkx`.
    """
    _utils._assert_networkx()
    import networkx as nx
    g = nx.MultiDiGraph()
    _to_nx(g, u, umap=dict())
    return g


def _to_nx(
        g:
            '_utils.MultiDiGraph',
        u:
            Function,
        umap:
            dict[
                int,
                _Nat]
        ) -> None:
    """Recursively construct a ADD graph."""
    u_int = int(u)
    # visited ?
    if u_int in umap:
        return
    u_nd = umap.setdefault(
        u_int, len(umap))
    if u.var is None:
        label = 'FALSE' if u == u.agd.zero else 'TRUE'
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


def _to_dot(
        roots:
            _abc.Collection[Function]
        ) -> _utils.DotGraph:
    """Return graph for the ADD rooted at `u`."""
    if not roots:
        raise ValueError(
            f'No `roots` given:  {roots}')
    assert roots, roots
    g = _utils.DotGraph(
        graph_type='digraph')
    # construct graphs
    subgraphs = _add_nodes_for_algebraic_dd_levels(g, roots)
    # mapping CUDD ADD node ID -> node name in DOT graph
    umap = dict()
    for u in roots:
        _to_dot_recurse(
            g, u, umap, subgraphs)
    _add_nodes_for_external_references(
        roots, umap, g, subgraphs[-1])
    return g


def _add_nodes_for_algebraic_dd_levels(
        g:
            _utils.DotGraph,
        roots:
            list[Function]
        ) -> dict[
            int | _Level,
            _utils.DotGraph]:
    """Create nodes and subgraphs for ADD levels.

    For each level of any ADD node reachable from `roots`,
    a new node `u_level` and a new subgraph `h_level` are created.
    The node `u_level` is labeled with the level (as numeral),
    and added to the subgraph `h_level`.

    For each pair of consecutive levels in
    `sorted(set of levels of nodes reachable from roots)`,
    an edge is added to graph `g`, pointing from
    the node labeled with the smaller level,
    to the node labeled with the larger level.

    Level `-1` is considered to represent external references
    to ADD nodes, i.e., instances of the class `Function`.

    The collection of subgraphs (`h_level` above) is returned.

    @return:
        subgraphs for the ADD levels of
        nodes reachable from `roots`
    """
    # mapping level -> var
    level_to_var = _collect_var_levels(roots)
    # add layer for external ADD references
    level_to_var[-1] = None
    subgraphs = dict()
    level_node_names = list()
    for level in sorted(level_to_var):
        h = _utils.DotGraph(
            rank='same')
        g.subgraphs.append(h)
        subgraphs[level] = h
        # add phantom node
        u = f'L{level}'
        level_node_names.append(u)
        if level == -1:
            # layer for external ADD references
            label = 'ref'
        else:
            # ADD level
            label = str(level)
        h.add_node(
            u,
            label=label,
            shape='none')
    # auxiliary edges for ranking of levels
    a, a1 = _itr.tee(level_node_names)
    next(a1, None)
    for u, v in zip(a, a1):
        g.add_edge(
            u, v,
            style='invis')
    return subgraphs


def _to_dot_recurse(
        g:
            _utils.DotGraph,
        u:
            Function,
        umap:
            dict[int, _Nat],
        subgraphs:
            dict[
                _Level,
                _utils.DotGraph]
        ) -> None:
    """Recursively construct an ADD graph."""
    u_int = int(u)
    # visited ?
    if u_int in umap:
        return
    u_nd = umap.setdefault(u_int, len(umap))
    if u.var is None:
        label = 'FALSE' if u == u.agd.zero else 'TRUE'
    else:
        label = u.var
    h = subgraphs[u.level]
    h.add_node(
        u_nd,
        label=label)
    if u.var is None:
        return
    v, w = u.low, u.high
    if v is None:
        raise AssertionError(v)
    if w is None:
        raise AssertionError(w)
    v_int = int(v)
    w_int = int(w)
    _to_dot_recurse(g, v, umap, subgraphs)
    _to_dot_recurse(g, w, umap, subgraphs)
    v_nd = umap[v_int]
    w_nd = umap[w_int]
    g.add_edge(
        u_nd, v_nd,
        taillabel='0',
        style='dashed')
    g.add_edge(
        u_nd, w_nd,
        taillabel='1',
        style='solid')


def _add_nodes_for_external_references(
        roots:
            list[Function],
        umap:
            dict[int, int],
        g:
            _utils.DotGraph,
        h:
            _utils.DotGraph
        ) -> None:
    """Add nodes to `g` that represent the references in `roots`.

    @param roots:
        external references to ADD nodes
    @param g:
        ADD graph
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
        h.add_node(
            ref_nd,
            label=label)
        # add edge from external reference to ADD node
        g.add_edge(
            ref_nd, u_nd,
            style='dashed')


def _collect_var_levels(
        roots:
            list[Function]
        ) -> dict[
            _Level,
            _VariableName]:
    """Add variables and levels reachable from `roots`.

    @return:
        maps each level to a variable,
        only for levels of nodes that are
        reachable from the ADD node `u`
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
            dict[
                _Level,
                _VariableName],
        visited:
            set[int]
        ) -> None:
    """Recursively collect variables and levels.

    @param level_to_var:
        maps each level to a variable,
        only for levels of nodes that are
        reachable from the ADD node `u`
    @param visited:
        those ADD nodes that have already been visited
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


cpdef Function _dict_to_add(
        qvars:
            _abc.Iterable[
                _VariableName],
        agd:
            ADD):
    """Return a ADD that is TRUE over `qvars`.

    This ADD has nodes at levels of variables in
    `qvars`. Each such node has same low and high.
    """
    levels = {agd.level_of_var(var) for var in qvars}
    r = agd.one
    for level in sorted(levels, reverse=True):
        var = agd.var_at_level(level)
        r = agd.find_or_add(var, r, r)
    return r


cpdef set _cube_to_universe_root(
        cube:
            Function,
        agd:
            ADD):
    """Map the conjunction `cube` to its support."""
    qvars = set()
    _cube_to_universe(cube, qvars, agd)
    qvars_ = agd.support(cube)
    if qvars != qvars_:
        raise AssertionError((qvars, qvars_))
    return qvars


cpdef _cube_to_universe(
        cube:
            Function,
        qvars:
            set[_VariableName],
        agd:
            ADD):
    """Recursively map `cube` to its support."""
    if cube == agd.zero:
        return
    if cube == agd.one:
        return
    if cube.low != cube.high:
        var = cube.var
        qvars.add(var)
        if cube.low != agd.zero:
            raise ValueError((cube, cube.low, len(cube.low)))
    _cube_to_universe(cube.high, qvars, agd)


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
            'this class?')
    assert self._ref >= 0, self._ref
    if self._ref == 0:
        return
    if self.node is NULL:
        raise AssertionError(
            'The attribute `node` is a `NULL` pointer. '
            'This is unexpected and should never happen. '
            'Was the value of `_ref` changed from outside '
            'this class?')
    # anticipate multiple calls to `__dealloc__`
    self._ref -= 1
    # deref
    Cudd_RecursiveDeref(self.manager, self.node)
    # avoid future access to deallocated memory
    self.node = NULL


cdef stdint.uintptr_t _ddnode_to_int(
        u:
            DdRef):
    i = <stdint.uintptr_t>u
    if 0 <= i:
        i += 2
    if i in (0, 1):
        raise AssertionError(f'{i}')
    return i
