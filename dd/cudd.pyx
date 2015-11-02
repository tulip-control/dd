# cython: profile=True
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
import pprint
import sys
from dd import _parser
from libcpp cimport bool
from libc.stdio cimport FILE, fdopen, fopen, fclose
from cpython.mem cimport PyMem_Malloc, PyMem_Free


cdef extern from 'cudd.h':
    # node
    ctypedef unsigned int DdHalfWord
    cdef struct DdNode:
        DdHalfWord index
        DdHalfWord ref
    ctypedef DdNode DdNode
    # manager
    cdef struct DdManager:
        pass
    ctypedef DdManager DdManager
    cdef DdManager *Cudd_Init(
        unsigned int numVars,
        unsigned int numVarsZ,
        unsigned int numSlots,
        unsigned int cacheSize,
        unsigned long maxMemory)
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
    cdef DdNode *Cudd_T(DdNode *u)
    cdef DdNode *Cudd_E(DdNode *u)
    cdef bool Cudd_IsComplement(DdNode *u)
    cdef int Cudd_DagSize(DdNode *node)
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
    # reordering
    cdef int Cudd_ShuffleHeap(DdManager *table, int *permutation)
    cdef unsigned int Cudd_ReadReorderings(DdManager *dd)
    cdef long Cudd_ReadReorderingTime(DdManager *dd)
    cdef int Cudd_ReadPerm(DdManager *dd, int i)
    cdef int Cudd_ReadInvPerm(DdManager *dd, int i)
    # manager config
    cdef unsigned long Cudd_ReadMaxMemory(DdManager *dd)
    cdef void Cudd_SetMaxMemory(DdManager *dd, unsigned long maxMemory)
    cdef unsigned int Cudd_ReadMaxCacheHard(DdManager *dd)
    cdef void Cudd_SetMaxCacheHard(DdManager *dd, unsigned int mc)
    cdef void Cudd_AutodynEnable(DdManager *unique,
                                 Cudd_ReorderingType method)
    cdef double Cudd_ReadMaxGrowth(DdManager *dd)
    cdef void Cudd_SetMaxGrowth(DdManager *dd, double mg)
    cdef unsigned int Cudd_ReadMinHit(DdManager *dd)
    cdef void Cudd_SetMinHit(DdManager *dd, unsigned int hr)
    cdef void Cudd_EnableGarbageCollection(DdManager *dd)
    cdef void Cudd_DisableGarbageCollection(DdManager *dd)
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
cdef CUDD_UNIQUE_SLOTS = 256
cdef CUDD_CACHE_SLOTS = 262144
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
cdef DDDMP_MODE_TEXT = <int>'A'
cdef DDDMP_VARIDS = 0
cdef DDDMP_VARNAMES = 3
cdef DDDMP_VAR_MATCHNAMES = 3
cdef DDDMP_SUCCESS = 1


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

    def __cinit__(self, memory=None):
        """Initialize BDD manager.

        @param memory: maximum allowed memory, in GB.
        """
        if memory is None:
            memory = 2 * 1024**3
        mgr = Cudd_Init(0, 0, CUDD_UNIQUE_SLOTS,
                        CUDD_CACHE_SLOTS, memory)
        assert mgr != NULL, 'failed to init CUDD DdManager'
        Cudd_SetMaxCacheHard(mgr, MAX_CACHE)
        Cudd_AutodynEnable(mgr, CUDD_REORDER_GROUP_SIFT)
        Cudd_SetMaxGrowth(mgr, 1.5)
        Cudd_SetMinHit(mgr, 20)
        self.manager = mgr
        self.vars = set()
        self._index_of_var = dict()  # map: str -> unique fixed int
        self._var_with_index = dict()

    def __dealloc__(self):
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
            self.apply('not', u)
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
                peak=d['peak_n_nodes'],
                n_vars=d['n_vars'],
                reorder_time=d['reordering_time'],
                n_reorderings=d['n_reorderings'],
                mem=d['mem'])
        return s

    def statistics(self):
        """Return `dict` with CUDD node counts and times."""
        n_vars = Cudd_ReadSize(self.manager)
        n_nodes = Cudd_ReadNodeCount(self.manager)
        peak_n_nodes = Cudd_ReadPeakLiveNodeCount(self.manager)
        t = Cudd_ReadReorderingTime(self.manager)
        reordering_time = t / 1000.0
        n_reorderings = Cudd_ReadReorderings(self.manager)
        m = Cudd_ReadMemoryInUse(self.manager)
        mem = float(m) / 10**6
        d = dict(
            n_vars=n_vars,
            n_nodes=n_nodes,
            peak_n_nodes=peak_n_nodes,
            reordering_time=reordering_time,
            n_reorderings=n_reorderings,
            mem=mem)
        return d

    def configure(BDD self, d=None):
        """Apply and return parameter values.

        Available keys:

          - `'max_memory'`: in bytes
          - `'loose_up_to'`: unique table fast growth upper bound
          - `'max_cache_hard'`: cache entries upper bound
          - `'min_hit'`: hit ratio for resizing cache
          - `'max_growth'`: intermediate growth during sifting

        For more details, see `cuddAPI.c`.
        Example usage:

        ```
        d = dict(
            max_memory=12 * 1024**3,
            loose_up_to=5 * 10**6,
            max_cache_hard=MAX_CACHE,
            min_hit=20,
            max_growth=1.5)
        bdd.config(d)
        ```
        """
        cdef DdManager *mgr
        mgr = self.manager
        if d is None:
            d = dict()
        # set
        for k, v in d.items():
            if k == 'max_memory':
                Cudd_SetMaxMemory(mgr, v)
            elif k == 'loose_up_to':
                Cudd_SetLooseUpTo(mgr, v)
            elif k == 'max_cache_hard':
                Cudd_SetMaxCacheHard(mgr, v)
            elif k == 'min_hit':
                Cudd_SetMinHit(mgr, v)
            elif k == 'max_growth':
                Cudd_SetMaxGrowth(mgr, v)
            else:
                raise Exception('Unknown parameter "{k}"'.format(k=k))
        # read
        max_memory = Cudd_ReadMaxMemory(mgr)
        loose_up_to = Cudd_ReadLooseUpTo(mgr)
        max_cache_hard = Cudd_ReadMaxCacheHard(mgr)
        min_hit = Cudd_ReadMinHit(mgr)
        max_growth = Cudd_ReadMaxGrowth(mgr)
        return dict(
            max_memory=max_memory,
            loose_up_to=loose_up_to,
            max_cache_hard=max_cache_hard,
            min_hit=min_hit,
            max_growth=max_growth)

    cpdef garbage_collection(self, on):
        """Enable or disable garbage collection."""
        if on:
            Cudd_EnableGarbageCollection(self.manager);
        else:
            Cudd_DisableGarbageCollection(self.manager);

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
            assert j == index, (j, index)
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
        assert set(supp.itervalues()) == {True}, supp
        return set(supp)

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

    cpdef Function apply(self, op, Function u, Function v=None):
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
            assert u.manager == v.manager
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
        if r == NULL:
            raise Exception(
                'unknown operator: "{op}"'.format(op=op))
        f = Function()
        f.init(mgr, r)
        return f

    cpdef Function cube(self, dvars):
        """Return node for cube over `dvars`.

        @param dvars: `dict` that maps each variable to a `bool`
        """
        n = len(self._index_of_var)
        # make cube
        cdef DdNode *cube
        cdef int *x
        x = <int *> PyMem_Malloc(n * sizeof(int))
        for var, j in self._index_of_var.iteritems():
            if var not in dvars:
                x[j] = 2
                continue
            # var in dvars
            if isinstance(dvars, dict):
                b = dvars[var]
            else:
                b = True
            if b == False:
                x[j] = 0
            elif b == True:
                x[j] = 1
            else:
                raise Exception('unknown value: {b}'.format(b=b))
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
        n = len(self.vars)
        cdef int *x
        x = <int *> PyMem_Malloc(n * sizeof(DdNode *))
        try:
            Cudd_BddToCubeArray(self.manager, f.node, x)
            d = dict()
            for var, index in self._index_of_var.iteritems():
                b = x[index]
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
        finally:
            PyMem_Free(x)
        return d

    cpdef Function quantify(self, Function u,
                            qvars, forall=False):
        """Abstract variables `qvars` from node `u`."""
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

    cpdef dump(self, Function u, fname):
        """Dump BDD as DDDMP file `fname`."""
        n = len(self._index_of_var)
        cdef FILE *f
        cdef char **names
        names = <char **> PyMem_Malloc(n * sizeof(char *))
        for index, var in self._var_with_index.iteritems():
            names[index] = var
        try:
            f = fopen(fname, 'w')
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
        names = <char **> PyMem_Malloc(n * sizeof(char *))
        for index, var in self._var_with_index.iteritems():
            names[index] = var
        try:
            f = fopen(fname, 'r')
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
            print(
                'A malformed DDDMP file can cause '
                'segmentation faults to `dddmp`.')
        finally:
            fclose(f)
            PyMem_Free(names)
        assert r != NULL, 'failed to load DDDMP file.'
        h = Function()
        h.init(self.manager, r)
        # `Dddmp_cuddBddArrayLoad` references `r`
        Cudd_RecursiveDeref(self.manager, r)
        return h

    property false:

        """`Function` for Boolean value false."""

        def __get__(self):
            return self._bool(False)

    property true:

        """`Function` for Boolean value true."""

        def __get__(self):
            return self._bool(True)

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


cpdef Function and_exists(Function u, Function v, qvars, BDD bdd):
    """Return `? qvars. u & v`."""
    assert u.manager == v.manager
    mgr = u.manager
    cube = bdd.cube(qvars)
    r = Cudd_bddAndAbstract(u.manager, u.node, v.node, cube.node)
    f = Function()
    f.init(mgr, r)
    return f


cpdef Function or_forall(Function u, Function v, qvars, BDD bdd):
    """Return `! qvars. u | v`."""
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


cpdef Function rename(Function u, bdd, dvars):
    """Return node `u` after renaming variables in `dvars`."""
    common = set(dvars).intersection(dvars.itervalues())
    assert not common, common
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


cpdef reorder(BDD bdd, dict dvars):
    """Reorder `bdd` to order in `dvars`."""
    # partial reorderings not supported for now
    assert len(dvars) == len(bdd.vars)
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

    @type u: `Function` with `u in source`
    @type source, target: `BDD`
    """
    logger.debug('++ transfer bdd')
    assert u.manager == source.manager
    assert u.manager != target.manager
    # target missing vars ?
    supp = source.support(u)
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

    property index:

        """Index of `self.node`."""

        def __get__(self):
            cdef DdNode *u
            u = Cudd_Regular(self.node)
            return u.index

    property ref:

        """Sum of reference counts of node and its negation."""

        def __get__(self):
            cdef DdNode *u
            u = Cudd_Regular(self.node)
            return u.ref

    property low:

        """Return "else" node as `Function`."""

        def __get__(self):
            cdef DdNode *u
            u = Cudd_E(self.node)
            f = Function()
            f.init(self.manager, u)
            return f

    property high:

        """Return "then" node as `Function`."""

        def __get__(self):
            cdef DdNode *u
            u = Cudd_T(self.node)
            f = Function()
            f.init(self.manager, u)
            return f

    property negated:

        """Return `True` if `self` is a complemented edge."""

        def __get__(self):
            return Cudd_IsComplement(self.node)

    def __dealloc__(self):
        Cudd_RecursiveDeref(self.manager, self.node)

    def __str__(self):
        cdef DdNode *u
        u = Cudd_Regular(self.node)
        return (
            'Function(DdNode with: '
            'var_index={idx}, '
            'ref_count={ref})').format(
                idx=u.index,
                ref=u.ref)

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
    assert i == 2, i
    bdd.incref(f.node)
    i = f.ref
    assert i == 3, i
    bdd.decref(f.node)
    j = f.ref
    assert j == i - 1, (j, i)
    del f
