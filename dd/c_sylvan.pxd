"""Cython extern declarations from Sylvan.


Reference
=========
    Tom van Dijk, Alfons Laarman, Jaco van de Pol
    "Multi-Core BDD Operations for
     Symbolic Reachability"
    PDMC 2012
    <https://doi.org/10.1016/j.entcs.2013.07.009>
"""
# Copyright 2016 by California Institute of Technology
# All rights reserved. Licensed under BSD-3.
#
from libcpp cimport bool
cimport libc.stdint as stdint


cdef extern from 'lace.h':
    """
    #define LACE_ME_WRAP 0); LACE_ME (0
    """
    void LACE_ME_WRAP()
    ctypedef struct WorkerP
    ctypedef struct Task
cdef extern from 'sylvan.h':
    ctypedef stdint.uint64_t BDD
    ctypedef stdint.uint64_t BDDSET
    ctypedef stdint.uint32_t BDDVAR
    ctypedef stdint.uint64_t BDDMAP
    #
    stdint.uint64_t sylvan_complement
    stdint.uint64_t sylvan_false
    stdint.uint64_t sylvan_true
    BDD sylvan_invalid
    # int gc_enabled  # should not be `static`
    #
    ctypedef void (*lace_startup_cb)(
        WorkerP*, Task*, void*)
    # node elements
    BDD sylvan_ithvar(BDDVAR var)
    BDD sylvan_nithvar(BDD var)
    BDDVAR sylvan_var(BDD bdd)
    BDD sylvan_low(BDD bdd)
    BDD sylvan_high(BDD bdd)
    bool sylvan_isconst(BDD bdd)
    bool sylvan_isnode(BDD bdd)
    size_t sylvan_nodecount(BDD a)
    size_t sylvan_count_refs()
    # main Boolean operators
    BDD sylvan_not(BDD a)
    BDD sylvan_and(BDD a, BDD b)
    BDD sylvan_xor(BDD a, BDD b)
    BDD sylvan_ite(BDD a, BDD b, BDD c)
    # derived operators
    BDD sylvan_equiv(BDD a, BDD b)
    BDD sylvan_or(BDD a, BDD b)
    BDD sylvan_imp(BDD a, BDD b)
    BDD sylvan_biimp(BDD a, BDD b)
    BDD sylvan_diff(BDD a, BDD b)
    # compose
    BDD sylvan_support(BDD bdd)
    BDD sylvan_constrain(BDD f, BDD c)
    BDD sylvan_restrict(BDD f, BDD c)
    BDD sylvan_compose(BDD f, BDDMAP m)
    BDDMAP sylvan_map_empty()
    BDDMAP sylvan_map_add(
        BDDMAP map, BDDVAR key, BDD value)
    # enumeration
    double sylvan_satcount(
        BDD bdd, BDDSET variables)
    BDD sylvan_pick_cube(BDD bdd)
    double sylvan_pathcount(BDD bdd)
    # refs
    BDD sylvan_ref(BDD a)
    void sylvan_deref(BDD a)
    # logistics
    void lace_exit()
    void lace_init(int n_workers, size_t dqsize)
    void lace_startup(
        size_t stacksize,
        lace_startup_cb cb,
        void* arg)
    void sylvan_init_package(
        size_t initial_tablesize,
        size_t max_tablesize,
        size_t initial_cachesize,
        size_t max_cachesize)
    void sylvan_init_bdd(int granularity)
    void sylvan_quit()
    # quantification
    BDD sylvan_exists(BDD a, BDD qvars)
    BDD sylvan_forall(BDD a, BDD qvars)
    BDD sylvan_and_exists(
        BDD a, BDD b, BDD qvars)
    BDD sylvan_relprev(BDD a, BDD b, BDD qvars)
    BDD sylvan_relnext(BDD a, BDD b, BDD qvars)
    BDD sylvan_closure(BDD a)
    # TODO: `stats.h`
