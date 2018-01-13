/**

  @ingroup cudd

  @brief Transfer between different managers, with renaming.

  Based on `cudd/cuddBridge.c` and `cudd/cuddCompose.c` by
  Fabio Somenzi and Kavita Ravi.

  @copyright@parblock
  Copyright (c) 1995-2015, Regents of the University of Colorado

  All rights reserved.

  Redistribution and use in source and binary forms, with or without
  modification, are permitted provided that the following conditions
  are met:

  Redistributions of source code must retain the above copyright
  notice, this list of conditions and the following disclaimer.

  Redistributions in binary form must reproduce the above copyright
  notice, this list of conditions and the following disclaimer in the
  documentation and/or other materials provided with the distribution.

  Neither the name of the University of Colorado nor the names of its
  contributors may be used to endorse or promote products derived from
  this software without specific prior written permission.

  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
  FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
  COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
  INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
  BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
  LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
  CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
  LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
  ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
  POSSIBILITY OF SUCH DAMAGE.
  @endparblock

*/
#include "util.h"
#include "cuddInt.h"


/*---------------------------------------------------------------------------*/
/* Static function prototypes                                                */
/*---------------------------------------------------------------------------*/
static DdNode * cuddBddTransferRecurRename(
    DdManager *ddS, DdManager *ddD, DdNode *f, st_table *table, int *renaming);
extern DdNode * cuddBddTransferRename(
    DdManager * ddS, DdManager * ddD, DdNode * f, int * renaming);
/*---------------------------------------------------------------------------*/
/* Definition of exported functions                                          */
/*---------------------------------------------------------------------------*/


/**
  @brief Convert a %BDD from a manager to another one.

  @details The orders of the variables in the two managers may be
  different. The array `renaming` is a mapping from variable indices
  in `ddSource` to variable indices in `ddDestination`.

  @return a pointer to the %BDD in the destination manager if
  successful; NULL otherwise.

  @sideeffect None
*/
DdNode *
Cudd_bddTransferRename(
  DdManager * ddSource,
  DdManager * ddDestination,
  DdNode * f,
  int * renaming)
{
    DdNode *res;
    do {
	ddDestination->reordered = 0;
	res = cuddBddTransferRename(ddSource, ddDestination, f, renaming);
    } while (ddDestination->reordered == 1);
    if (ddDestination->errorCode == CUDD_TIMEOUT_EXPIRED &&
        ddDestination->timeoutHandler) {
        ddDestination->timeoutHandler(ddDestination, ddDestination->tohArg);
    }
    return(res);

}


/*---------------------------------------------------------------------------*/
/* Definition of internal functions                                          */
/*---------------------------------------------------------------------------*/


/**
  @brief Convert a %BDD from a manager to another one.

  @return a pointer to the %BDD in the destination manager if
  successful; NULL otherwise.

  @sideeffect None
*/
DdNode *
cuddBddTransferRename(
  DdManager * ddS,
  DdManager * ddD,
  DdNode * f,
  int * renaming)
{
    DdNode *res;
    st_table *table = NULL;
    st_generator *gen = NULL;
    DdNode *key, *value;

    table = st_init_table(st_ptrcmp,st_ptrhash);
    if (table == NULL) goto failure;
    res = cuddBddTransferRecurRename(ddS, ddD, f, table, renaming);
    if (res != NULL) cuddRef(res);

    /* Dereference all elements in the table and dispose of the table.
    ** This must be done also if res is NULL to avoid leaks in case of
    ** reordering. */
    gen = st_init_gen(table);
    if (gen == NULL) goto failure;
    while (st_gen(gen, (void **) &key, (void **) &value)) {
	Cudd_RecursiveDeref(ddD, value);
    }
    st_free_gen(gen); gen = NULL;
    st_free_table(table); table = NULL;

    if (res != NULL) cuddDeref(res);
    return(res);

failure:
    /* No need to free gen because it is always NULL here. */
    if (table != NULL) st_free_table(table);
    return(NULL);

}


/**
  @brief Performs the recursive step of Cudd_bddTransferRename.

  @return a pointer to the result if successful; NULL otherwise.

  @sideeffect None
*/
static DdNode *
cuddBddTransferRecurRename(
  DdManager * ddS,
  DdManager * ddD,
  DdNode * f,
  st_table * table,
  int * renaming)
{
    DdNode *ft, *fe, *t, *e, *var, *res;
    DdNode *one, *zero;
    unsigned int index;
    int comple = 0;

    statLine(ddD);
    one = DD_ONE(ddD);
    comple = Cudd_IsComplement(f);

    /* Trivial cases. */
    if (Cudd_IsConstantInt(f)) return(Cudd_NotCond(one, comple));

    /* Make canonical to increase the utilization of the cache. */
    f = Cudd_NotCond(f,comple);
    /* Now f is a regular pointer to a non-constant node. */

    /* Check the cache. */
    if (st_lookup(table, f, (void **) &res))
	return(Cudd_NotCond(res,comple));

    /* Recursive step. */
    index = renaming[f->index];
    ft = cuddT(f); fe = cuddE(f);

    t = cuddBddTransferRecurRename(ddS, ddD, ft, table, renaming);
    if (t == NULL) {
    	return(NULL);
    }
    cuddRef(t);

    e = cuddBddTransferRecurRename(ddS, ddD, fe, table, renaming);
    if (e == NULL) {
    	Cudd_RecursiveDeref(ddD, t);
    	return(NULL);
    }
    cuddRef(e);

    zero = Cudd_Not(one);
    var = cuddUniqueInter(ddD,index,one,zero);
    if (var == NULL) {
	Cudd_RecursiveDeref(ddD, t);
	Cudd_RecursiveDeref(ddD, e);
    	return(NULL);
    }
    res = cuddBddIteRecur(ddD,var,t,e);
    if (res == NULL) {
	Cudd_RecursiveDeref(ddD, t);
	Cudd_RecursiveDeref(ddD, e);
	return(NULL);
    }
    cuddRef(res);
    Cudd_RecursiveDeref(ddD, t);
    Cudd_RecursiveDeref(ddD, e);

    if (st_add_direct(table, f, res) == ST_OUT_OF_MEM) {
	Cudd_RecursiveDeref(ddD, res);
	return(NULL);
    }
    return(Cudd_NotCond(res,comple));
}
