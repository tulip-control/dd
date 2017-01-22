"""Cython extern declarations from Sylvan.


Reference
=========
    Tom van Dijk, Alfons Laarman, Jaco van de Pol
    "Multi-Core BDD Operations for
     Symbolic Reachability"
    PDMC 2012
    doi:10.1016/j.entcs.2013.07.009
"""
# Copyright 2016 by California Institute of Technology
# All rights reserved. Licensed under BSD-3.
#
from libcpp cimport bool
from libc cimport stdint


cdef extern from 'sylvan.h':
    ctypedef stdint.uint64_t BDD
    ctypedef stdint.uint64_t BDDSET
    ctypedef stdint.uint32_t BDDVAR
    ctypedef stdint.uint64_t BDDMAP
    #
    cdef stdint.uint64_t sylvan_complement
    cdef stdint.uint64_t sylvan_false
    cdef stdint.uint64_t sylvan_true
    cdef BDD sylvan_invalid
    # cdef int gc_enabled  # should not be `static`
    #
    ctypedef struct WorkerP
    ctypedef struct Task
    ctypedef void (*lace_startup_cb)(
        WorkerP*, Task*, void*)
    # node elements
    cdef BDD sylvan_ithvar(BDDVAR var)
    cdef BDD sylvan_nithvar(BDD var)
    cdef BDDVAR sylvan_var(BDD bdd)
    cdef BDD sylvan_low(BDD bdd)
    cdef BDD sylvan_high(BDD bdd)
    cdef bool sylvan_isconst(BDD bdd)
    cdef bool sylvan_isnode(BDD bdd)
    cdef size_t sylvan_nodecount(BDD a)
    cdef size_t sylvan_count_refs()
    # main Boolean operators
    cdef BDD sylvan_not(BDD a)
    cdef BDD sylvan_and(BDD a, BDD b)
    cdef BDD sylvan_xor(BDD a, BDD b)
    cdef BDD sylvan_ite(BDD a, BDD b, BDD c)
    # derived operators
    cdef BDD sylvan_equiv(BDD a, BDD b)
    cdef BDD sylvan_or(BDD a, BDD b)
    cdef BDD sylvan_imp(BDD a, BDD b)
    cdef BDD sylvan_biimp(BDD a, BDD b)
    cdef BDD sylvan_diff(BDD a, BDD b)
    # compose
    cdef BDD sylvan_support(BDD bdd)
    cdef BDD sylvan_constrain(BDD f, BDD c)
    cdef BDD sylvan_restrict(BDD f, BDD c)
    cdef BDD sylvan_compose(BDD f, BDDMAP m)
    cdef BDDMAP sylvan_map_empty()
    cdef BDDMAP sylvan_map_add(BDDMAP map, BDDVAR key, BDD value)
    # enumeration
    cdef double sylvan_satcount(BDD bdd,
                                BDDSET variables)
    cdef BDD sylvan_pick_cube(BDD bdd)
    cdef double sylvan_pathcount(BDD bdd)
    # refs
    cdef BDD sylvan_ref(BDD a)
    cdef void sylvan_deref(BDD a)
    # logistics
    cdef void LACE_ME()
    cdef void lace_exit()
    cdef void lace_init(int n_workers, size_t dqsize)
    cdef void lace_startup(
        size_t stacksize,
        lace_startup_cb cb,
        void* arg)
    cdef void sylvan_init_package(
        size_t initial_tablesize,
        size_t max_tablesize,
        size_t initial_cachesize,
        size_t max_cachesize)
    cdef void sylvan_init_bdd(int granularity)
    cdef void sylvan_quit()
    # quantification
    cdef BDD sylvan_exists(BDD a, BDD qvars)
    cdef BDD sylvan_forall(BDD a, BDD qvars)
    cdef BDD sylvan_and_exists(BDD a, BDD b,
                               BDD qvars)
    cdef BDD sylvan_relprev(BDD a, BDD b, BDD qvars)
    cdef BDD sylvan_relnext(BDD a, BDD b, BDD qvars)
    cdef BDD sylvan_closure(BDD a)
    # TODO: `stats.h`
