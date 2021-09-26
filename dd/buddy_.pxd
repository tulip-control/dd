# cython: profile=True
"""Cython extern declarations from BuDDy.


Reference
=========
    Jorn Lind-Nielsen
    "BuDDy: Binary Decision Diagram package"
    IT-University of Copenhagen (ITU)
    v2.4, 2002
    https://sourceforge.net/projects/buddy/
"""
# Copyright 2015 by California Institute of Technology
# All rights reserved. Licensed under BSD-3.
#
from libc.stdio cimport FILE


cdef extern from 'bdd.h':
    int BDD_VAR
    # BDD
    ctypedef int BDD
    # renaming pair
    struct s_bddPair:
        pass
    ctypedef s_bddPair bddPair
    int bdd_init(int BDDsize, int cachesize)
    int bdd_isrunning()
    void bdd_done()
    int bdd_setacheratio(int r)
    # variable creation
    BDD bdd_ithvar(int var)
    BDD bdd_nithvar(int var)
    int bdd_var2level(int var)
    int bdd_level2var(int level)
    int bdd_setvarnum(int num)
    int bdd_extvarnum(int num)
    int bdd_varnum()
    # variable manipulation
    int bdd_var(BDD r)
    BDD bdd_makeset(int *varset, int varnum)
    int bdd_scanset(BDD a, int **varset, int *varnum)
    BDD bdd_ibuildcube(int value, int width, int *var)
    BDD bdd_buildcube(int value, int width, BDD *var)
    # BDD elements
    BDD bdd_true()
    BDD bdd_false()
    BDD bdd_low(BDD r)
    BDD bdd_high(BDD r)
    BDD bdd_support(BDD r)
    BDD bdd_satone(BDD r)  # cube
    BDD bdd_fullsatone(BDD r)  # minterm
    double bdd_satcount(BDD r)
    int bdd_nodecount(BDD r)
    # refs
    BDD bdd_addref(BDD r)
    BDD bdd_delref(BDD r)
    void bdd_gbc()
    # basic Boolean operators
    BDD bdd_ite(BDD u, BDD v, BDD w)
    BDD bdd_apply(BDD u, BDD w, int op)
    BDD bdd_not(BDD u)
    BDD bdd_and(BDD u, BDD v)
    BDD bdd_or(BDD u, BDD v)
    BDD bdd_xor(BDD u, BDD v)
    BDD bdd_imp(BDD u, BDD v)
    BDD bdd_biimp(BDD u, BDD v)
    # composition operators
    BDD bdd_restrict(BDD r, BDD var)
    BDD bdd_constrain(BDD f, BDD c)
    BDD bdd_compose(BDD f, BDD g, BDD v)
    BDD bdd_simplify(BDD f, BDD d)
    # quantification
    BDD bdd_exist(BDD r, BDD var)
    BDD bdd_forall(BDD r, BDD var)
    BDD bdd_appex(BDD u, BDD v, int op, BDD var)
    BDD bdd_appall(BDD u, BDD v, int op, BDD var)
    # renaming
    BDD bdd_replace(BDD r, bddPair *pair)
    bddPair * bdd_newpair()
    void bdd_freepair(bddPair *p)
    int bdd_setpair(bddPair *pair, int oldvar, int newvar)
    int bdd_setpairs(
        bddPair *pair, int *oldvar,
        int *newvar, int size)
    void bdd_resetpair(bddPair *pair)
    void bdd_freepair(bddPair *p)
    # manager config
    int bdd_setmaxBDDnum(int size)
    int bdd_setmaxincrease(int size)
    int bdd_setminfreeBDDs(int mf)
    int bdd_getnodenum()
    int bdd_getallocnum()  # both dead and active
    # reordering
    int bdd_addvarblock(BDD b, int fixed)
    int bdd_intaddvarblock(int first, int last, int fixed)
    void bdd_varblockall()
    void bdd_reorder(int method)
    int bdd_autoreorder(int method)
    int bdd_autoreorder_times(int method, int num)
    void bdd_enable_reorder()
    void bdd_disable_reorder()
    int bdd_reorder_gain()
    void bdd_setcacheratio(int r)
    # I/O
    int bdd_save(FILE *ofile, BDD r)
    int bdd_load(FILE *ifile, BDD r)
    # info
    int bdd_reorder_verbose(int value)
    void bdd_printorder()
    void bdd_fprintorder(FILE *ofile)
    # void bdd_stats(bddStat *stat)
    # void bdd_cachestats(bddCacheStat *s)
    void bdd_fprintstat(FILE *f)
    void bdd_printstat()
