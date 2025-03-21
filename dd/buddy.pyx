# cython: profile=True
"""Cython interface to BuDDy.


Reference
=========
    Jorn Lind-Nielsen
    "BuDDy: Binary Decision Diagram package"
    IT-University of Copenhagen (ITU)
    v2.4, 2002
    <https://sourceforge.net/projects/buddy/>
"""
# Copyright 2015 by California Institute of Technology
# All rights reserved. Licensed under BSD-3.
#
import collections.abc as _abc
import logging
import pprint
import sys
import typing as _ty

from cpython cimport bool as _py_bool
from cpython.mem cimport PyMem_Malloc, PyMem_Free
import cython
from libc.stdio cimport fdopen, fopen

import dd._abc as _dd_abc
cimport dd.buddy_ as buddy


ctypedef cython.int _c_int
_Yes: _ty.TypeAlias = _py_bool
_Cardinality: _ty.TypeAlias = _dd_abc.Cardinality
_VariableName: _ty.TypeAlias = _dd_abc.VariableName
_Level: _ty.TypeAlias = _dd_abc.Level
_Renaming: _ty.TypeAlias = _dd_abc.Renaming
_OperatorSymbol: _ty.TypeAlias = _ty.Literal[
    '!',
    'not',
    '&',
    'and',
    '|',
    'or',
    '#',
    '^',
    'xor']
_OPERATOR_SYMBOLS: _ty.Final = set(_ty.get_args(
    _OperatorSymbol))


APPLY_MAP = {
    'and':
        0,
    'xor':
        1,
    'or':
        2,
    'nand':
        3,
    'nor':
        4,
    'imp':
        5,
    'biimp':
        6,
    'diff':
        7,
    'less':
        8,
    'invimp':
        9}
BDD_REORDER_NONE = 0
BDD_REORDER_WIN2 = 1
BDD_REORDER_WIN2ITE = 2
    # "ite" = iteratively
BDD_REORDER_SIFT = 3
BDD_REORDER_SIFTITE = 4
BDD_REORDER_WIN3 = 5
BDD_REORDER_WIN3ITE = 6
BDD_REORDER_RANDOM = 7
BDD_REORDER_FREE = 0
BDD_REORDER_FIXED = 1


logger = logging.getLogger(__name__)


cdef class BDD:
    """Wrapper of BuDDy.

    Interface similar to `dd.bdd.BDD`.
    There is only a single global shared BDD,
    so use only one instance.
    """

    cdef public object var_to_index

    def __cinit__(
            self
            ) -> None:
        self.var_to_index = dict()
        if buddy.bdd_isrunning():
            return
        n_nodes = 10**2
        cache = 10**4
        n_vars = 150
        buddy.bdd_init(n_nodes, cache)
        buddy.bdd_setvarnum(n_vars)
        buddy.bdd_setcacheratio(64)
        buddy.bdd_autoreorder(BDD_REORDER_SIFT)
        buddy.bdd_reorder_verbose(1)

    def __dealloc__(
            self
            ) -> None:
        buddy.bdd_done()

    def __str__(
            self
            ) -> str:
        n = buddy.bdd_getnodenum()
        n_alloc = buddy.bdd_getallocnum()
        n_vars = buddy.bdd_varnum()
        s = (
            'Binary decision diagram (BuDDy wrapper) with:\n'
            f'\t {n} live nodes now\n'
            f'\t {n_alloc} total nodes allocated\n'
            f'\t {n_vars} BDD variables\n')
        return s

    def __len__(
            self
            ) -> _Cardinality:
        return buddy.bdd_getnodenum()

    cdef incref(
            self,
            u:
                _c_int):
        buddy.bdd_addref(u)

    cdef decref(
            self,
            u:
                _c_int):
        buddy.bdd_delref(u)

    property false:

        def __get__(
                self
                ) -> Function:
            return self._bool(False)

    property true:

        def __get__(
                self
                ) -> Function:
            return self._bool(True)

    cdef Function _bool(
            self,
            b:
                _py_bool):
        if b:
            r = buddy.bdd_true()
        else:
            r = buddy.bdd_false()
        return Function(r)

    cpdef int add_var(
            self,
            var:
                _VariableName):
        """Return index for variable `var`."""
        j = self.var_to_index.get(var)
        if j is not None:
            return j
        j = len(self.var_to_index)
        self.var_to_index[var] = j
        # new block for reordering
        buddy.bdd_intaddvarblock(j, j, 0)
        return j

    cpdef Function var(
            self,
            var:
                _VariableName):
        """Return BDD for variable `var`."""
        if var not in self.var_to_index:
            raise ValueError(
                f'"{var}" is not a variable (key) in '
                f'{self.var_to_index = }')
        j = self.var_to_index[var]
        r = buddy.bdd_ithvar(j)
        if r == self.false.node:
            raise RuntimeError('failed')
        buddy.bdd_intaddvarblock(j, j, 0)
        return Function(r)

    cpdef int level_of_var(
            self,
            var:
                _VariableName):
        """Return level of variable `var`."""
        if var not in self.var_to_index:
            raise ValueError(
                f'undeclared variable "{var}", '
                'known variables are:\n'
                f'{self.var_to_index}')
        j = self.var_to_index[var]
        level = buddy.bdd_var2level(j)
        return level

    cpdef str var_at_level(
            self,
            level:
                _Level):
        """Return variable at `level`."""
        index = buddy.bdd_level2var(level)
        # unknown variable error ?
        if index == buddy.BDD_VAR:
            levels = {
                var: self.level_of_var(var)
                for var in self.var_to_index}
            raise ValueError(
                f'no variable has level:  {level}, '
                'the current levels of all variables '
                f'are:  {levels}')
        index_to_var = {
            v: k for k, v in self.var_to_index.items()}
        var = index_to_var[index]
        return var

    cpdef Function apply(
            self,
            op:
                _OperatorSymbol,
            u:
                Function,
            v:
                Function |
                None=None):
        """Return as `Function` the result of applying `op`."""
        if op not in _OPERATOR_SYMBOLS:
            raise ValueError(
                f'unknown operator: "{op}"')
        # unary
        if op in ('!', 'not'):
            if v is not None:
                raise ValueError((op, u, v))
            r = buddy.bdd_not(u.node)
        elif v is None:
            raise ValueError((op, u, v))
        # binary
        if op in ('&', 'and'):
            r = buddy.bdd_and(u.node, v.node)
        elif op in ('|', 'or'):
            r = buddy.bdd_or(u.node, v.node)
        elif op in ('#', '^', 'xor'):
            r = buddy.bdd_xor(u.node, v.node)
        return Function(r)

    cpdef Function quantify(
            self,
            u:
                Function,
            qvars:
                _abc.Iterable[
                    _VariableName],
            forall:
                _Yes=False):
        cube = self.cube(qvars)
        if forall:
            r = buddy.bdd_forall(u, cube)
        else:
            r = buddy.bdd_exist(u, cube)
        return Function(r)

    cpdef Function cube(
            self,
            dvars:
                _abc.Iterable[
                    _VariableName]):
        """Return a positive unate cube for `dvars`."""
        n = len(dvars)
        cdef int *x
        x = <int *> PyMem_Malloc(n * sizeof(int))
        for i, var in enumerate(dvars):
            j = self.add_var(var)
            x[i] = j
        try:
            r = buddy.bdd_makeset(x, n)
        finally:
            PyMem_Free(x)
        return Function(r)

    cpdef assert_consistent(
            self):
        raise NotImplementedError('TODO')


cpdef Function and_abstract(
        u:
            Function,
        v:
            Function,
        qvars:
            _abc.Iterable[
                _VariableName],
        bdd:
            BDD):
    """Return `? qvars. u & v`."""
    cube = bdd.cube(qvars)
    op = APPLY_MAP['and']
    r = buddy.bdd_appex(u.node, v.node, op, cube.node)
    return Function(r)


cpdef Function or_abstract(
        u:
            Function,
        v:
            Function,
        qvars:
            _abc.Iterable[
                _VariableName],
        bdd:
            BDD):
    """Return `! qvars. u | v`."""
    cube = bdd.cube(qvars)
    op = APPLY_MAP['or']
    r = buddy.bdd_appall(u.node, v.node, op, cube.node)
    return Function(r)


def rename(
        u:
            Function,
        bdd:
            BDD,
        dvars:
            _Renaming
        ) -> Function:
    n = len(dvars)
    cdef int *oldvars
    cdef int *newvars
    oldvars = <int *> PyMem_Malloc(n * sizeof(int))
    newvars = <int *> PyMem_Malloc(n * sizeof(int))
    for i, (a, b) in enumerate(dvars.items()):
        ja = bdd.add_var(a)
        jb = bdd.add_var(b)
        oldvars[i] = ja
        newvars[i] = jb
    cdef buddy.bddPair *pair = buddy.bdd_newpair()
    try:
        buddy.bdd_setpairs(pair, oldvars, newvars, n)
        r = buddy.bdd_replace(u.node, pair)
    finally:
        buddy.bdd_freepair(pair)
        PyMem_Free(oldvars)
        PyMem_Free(newvars)
    return Function(r)


cdef class Function:
    """Wrapper for nodes of `BDD`.

    Takes care of reference counting,
    using the `weakref`s.

    Use as:

    ```cython
    bdd = BDD()
    u = bdd_true()
    f = Function(u)
    h = g | ~ f
    ```
    """

    __weakref__: object
    cdef public int node

    def __cinit__(
            self,
            node:
                _c_int
            ) -> None:
        self.node = node
        buddy.bdd_addref(node)

    def __dealloc__(
            self
            ) -> None:
        buddy.bdd_delref(self.node)
        self.node = -1

    def __str__(
            self
            ) -> str:
        n = len(self)
        return f'Function({self.node}, {n})'

    def __len__(
            self
            ) -> _Cardinality:
        return buddy.bdd_nodecount(self.node)

    def __eq__(
            self,
            other:
                Function |
                None
            ) -> _Yes:
        if other is None:
            return False
        other_: Function = other
        return self.node == other_.node

    def __ne__(
            self,
            other:
                Function |
                None
            ) -> _Yes:
        if other is None:
            return True
        other_: Function = other
        return self.node != other_.node

    def __invert__(
            self
            ) -> Function:
        r = buddy.bdd_not(self.node)
        return Function(r)

    def __and__(
            self,
            other:
                Function
            ) -> Function:
        r = buddy.bdd_and(self.node, other.node)
        return Function(r)

    def __or__(
            self,
            other:
                Function
            ) -> Function:
        r = buddy.bdd_or(self.node, other.node)
        return Function(r)

    def __xor__(
            self,
            other:
                Function
            ) -> Function:
        r = buddy.bdd_xor(self.node, other.node)
        return Function(r)
