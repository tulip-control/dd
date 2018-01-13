/**
  @file

  @ingroup cudd

  @brief Excerpts from `cudd/cuddBridge.c` and `cudd/cuddCompose.c`.

  @author Fabio Somenzi and Kavita Ravi

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
static DdNode * cuddBddTransferRecur(
    DdManager *ddS, DdManager *ddD, DdNode *f, st_table *table);

/*---------------------------------------------------------------------------*/
/* Definition of exported functions                                          */
/*---------------------------------------------------------------------------*/


/**
  @brief Convert a %BDD from a manager to another one.

  @details The orders of the variables in the two managers may be
  different.

  @return a pointer to the %BDD in the destination manager if
  successful; NULL otherwise.

  @sideeffect None

*/
DdNode *
Cudd_bddTransfer(
  DdManager * ddSource,
  DdManager * ddDestination,
  DdNode * f)
{
    DdNode *res;
    do {
	ddDestination->reordered = 0;
	res = cuddBddTransfer(ddSource, ddDestination, f);
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
cuddBddTransfer(
  DdManager * ddS,
  DdManager * ddD,
  DdNode * f)
{
    DdNode *res;
    st_table *table = NULL;
    st_generator *gen = NULL;
    DdNode *key, *value;

    table = st_init_table(st_ptrcmp,st_ptrhash);
    if (table == NULL) goto failure;
    res = cuddBddTransferRecur(ddS, ddD, f, table);
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
  @brief Performs the recursive step of Cudd_bddTransfer.

  @return a pointer to the result if successful; NULL otherwise.

  @sideeffect None
*/
static DdNode *
cuddBddTransferRecur(
  DdManager * ddS,
  DdManager * ddD,
  DdNode * f,
  st_table * table)
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
    index = f->index;
    ft = cuddT(f); fe = cuddE(f);

    t = cuddBddTransferRecur(ddS, ddD, ft, table);
    if (t == NULL) {
    	return(NULL);
    }
    cuddRef(t);

    e = cuddBddTransferRecur(ddS, ddD, fe, table);
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



/**
  @brief Permutes the variables of a %BDD.

  @details Given a permutation in array permut, creates a new %BDD
  with permuted variables. There should be an entry in array permut
  for each variable in the manager. The i-th entry of permut holds the
  index of the variable that is to substitute the i-th variable.

  @return a pointer to the resulting %BDD if successful; NULL
  otherwise.

  @sideeffect None

*/
DdNode *
Cudd_bddPermute(
  DdManager * manager,
  DdNode * node,
  int * permut)
{
    DdHashTable		*table;
    DdNode		*res;

    do {
	manager->reordered = 0;
	table = cuddHashTableInit(manager,1,2);
	if (table == NULL) return(NULL);
	res = cuddBddPermuteRecur(manager,table,node,permut);
	if (res != NULL) cuddRef(res);
	/* Dispose of local cache. */
	cuddHashTableQuit(table);

    } while (manager->reordered == 1);

    if (res != NULL) cuddDeref(res);
    if (manager->errorCode == CUDD_TIMEOUT_EXPIRED && manager->timeoutHandler) {
        manager->timeoutHandler(manager, manager->tohArg);
    }
    return(res);

}


/**
  @brief Implements the recursive step of Cudd_bddPermute.

  @details Recursively puts the %BDD in the order given in the array permut.
  Checks for trivial cases to terminate recursion, then splits on the
  children of this node.  Once the solutions for the children are
  obtained, it puts into the current position the node from the rest of
  the %BDD that should be here. Then returns this %BDD.
  The key here is that the node being visited is NOT put in its proper
  place by this instance, but rather is switched when its proper position
  is reached in the recursion tree.<p>
  The DdNode * that is returned is the same %BDD as passed in as node,
  but in the new order.

  @sideeffect None

*/
static DdNode *
cuddBddPermuteRecur(
  DdManager * manager /**< %DD manager */,
  DdHashTable * table /**< computed table */,
  DdNode * node /**< %BDD to be reordered */,
  int * permut /**< permutation array */)
{
    DdNode	*N,*T,*E;
    DdNode	*res;
    int		index;

    statLine(manager);
    N = Cudd_Regular(node);

    /* Check for terminal case of constant node. */
    if (cuddIsConstant(N)) {
	return(node);
    }

    /* If problem already solved, look up answer and return. */
    if (N->ref != 1 && (res = cuddHashTableLookup1(table,N)) != NULL) {
#ifdef DD_DEBUG
	manager->bddPermuteRecurHits++;
#endif
	return(Cudd_NotCond(res,N != node));
    }

    /* Split and recur on children of this node. */
    T = cuddBddPermuteRecur(manager,table,cuddT(N),permut);
    if (T == NULL) return(NULL);
    cuddRef(T);
    E = cuddBddPermuteRecur(manager,table,cuddE(N),permut);
    if (E == NULL) {
	Cudd_IterDerefBdd(manager, T);
	return(NULL);
    }
    cuddRef(E);

    /* Move variable that should be in this position to this position
    ** by retrieving the single var BDD for that variable, and calling
    ** cuddBddIteRecur with the T and E we just created.
    */
    index = permut[N->index];
    res = cuddBddIteRecur(manager,manager->vars[index],T,E);
    if (res == NULL) {
	Cudd_IterDerefBdd(manager, T);
	Cudd_IterDerefBdd(manager, E);
	return(NULL);
    }
    cuddRef(res);
    Cudd_IterDerefBdd(manager, T);
    Cudd_IterDerefBdd(manager, E);

    /* Do not keep the result if the reference count is only 1, since
    ** it will not be visited again.
    */
    if (N->ref != 1) {
	ptrint fanout = (ptrint) N->ref;
	cuddSatDec(fanout);
	if (!cuddHashTableInsert1(table,N,res,fanout)) {
	    Cudd_IterDerefBdd(manager, res);
	    return(NULL);
	}
    }
    cuddDeref(res);
    return(Cudd_NotCond(res,N != node));

}
