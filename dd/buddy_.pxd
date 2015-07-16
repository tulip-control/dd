# cython: profile=True
"""Cython extern declarations from BuDDy.


Reference
=========
    Jorn Lind-Nielsen
    "BuDDy: Binary Decision Diagram package"
    IT-University of Copenhagen (ITU)
    v2.4, 2002
    http://buddy.sourceforge.net
"""
from libc.stdio cimport FILE


cdef extern from 'bdd.h':
    # BDD
    ctypedef int BDD
    # renaming pair
    cdef struct s_bddPair:
        pass
    ctypedef s_bddPair bddPair
    cdef int bdd_init(int BDDsize, int cachesize)
    cdef int bdd_isrunning()
    cdef void bdd_done()
    cdef int bdd_setacheratio(int r)
    # variable creation
    cdef BDD bdd_ithvar(int var)
    cdef BDD bdd_nithvar(int var)
    cdef int bdd_var2level(int var)
    cdef int bdd_level2var(int level)
    cdef int bdd_setvarnum(int num)
    cdef int bdd_extvarnum(int num)
    cdef int bdd_varnum()
    # variable manipulation
    cdef int bdd_var(BDD r)
    cdef BDD bdd_makeset(int *varset, int varnum)
    cdef int bdd_scanset(BDD a, int **varset, int *varnum)
    cdef BDD bdd_ibuildcube(int value, int width, int *var)
    cdef BDD bdd_buildcube(int value, int width, BDD *var)
    # BDD elements
    cdef BDD bdd_true()
    cdef BDD bdd_false()
    cdef BDD bdd_low(BDD r)
    cdef BDD bdd_high(BDD r)
    cdef BDD bdd_support(BDD r)
    cdef BDD bdd_satone(BDD r)  # cube
    cdef BDD bdd_fullsatone(BDD r)  # minterm
    cdef double bdd_satcount(BDD r)
    cdef int bdd_nodecount(BDD r)
    # refs
    cdef BDD bdd_addref(BDD r)
    cdef BDD bdd_delref(BDD r)
    cdef void bdd_gbc()
    # basic Boolean operators
    cdef bdd_ite(BDD u, BDD v, BDD w)
    cdef bdd_apply(BDD u, BDD w, int op)
    cdef BDD bdd_not(BDD u)
    cdef BDD bdd_and(BDD u, BDD v)
    cdef BDD bdd_or(BDD u, BDD v)
    cdef BDD bdd_xor(BDD u, BDD v)
    cdef BDD bdd_imp(BDD u, BDD v)
    cdef BDD bdd_biimp(BDD u, BDD v)
    # composition operators
    cdef BDD bdd_restrict(BDD r, BDD var)
    cdef BDD bdd_constrain(BDD f, BDD c)
    cdef BDD bdd_compose(BDD f, BDD g, BDD v)
    cdef bdd_simplify(BDD f, BDD d)
    # quantification
    cdef BDD bdd_exist(BDD r, BDD var)
    cdef BDD bdd_forall(BDD r, BDD var)
    cdef BDD bdd_appex(BDD u, BDD v, int op, BDD var)
    cdef BDD bdd_appall(BDD u, BDD v, int op, BDD var)
    # renaming
    cdef BDD bdd_replace(BDD r, bddPair *pair)
    cdef bddPair * bdd_newpair()
    cdef void bdd_freepair(bddPair *p)
    cdef int bdd_setpair(bddPair *pair, int oldvar, int newvar)
    cdef int bdd_setpairs(bddPair *pair, int *oldvar,
                          int *newvar, int size)
    cdef void bdd_resetpair(bddPair *pair)
    cdef void bdd_freepair(bddPair *p)
    # manager config
    cdef int bdd_setmaxBDDnum(int size)
    cdef int bdd_setmaxincrease(int size)
    cdef int bdd_setminfreeBDDs(int mf)
    cdef int bdd_getnodenum()
    cdef int bdd_getallocnum()  # both dead and active
    # reordering
    cdef int bdd_addvarblock(BDD b, int fixed)
    cdef int bdd_intaddvarblock(int first, int last, int fixed)
    cdef void bdd_varblockall()
    cdef void bdd_reorder(int method)
    cdef int bdd_autoreorder(int method)
    cdef int bdd_autoreorder_times(int method, int num)
    cdef void bdd_enable_reorder()
    cdef void bdd_disable_reorder()
    cdef int bdd_reorder_gain()
    cdef void bdd_setcacheratio(int r)
    # I/O
    cdef int bdd_save(FILE *ofile, BDD r)
    cdef int bdd_load(FILE *ifile, BDD r)
    # info
    cdef int bdd_reorder_verbose(int value)
    cdef void bdd_printorder()
    cdef void bdd_fprintorder(FILE *ofile)
    # cdef void bdd_stats(bddStat *stat)
    # cdef void bdd_cachestats(bddCacheStat *s)
    cdef void bdd_fprintstat(FILE *f)
    cdef void bdd_printstat()
