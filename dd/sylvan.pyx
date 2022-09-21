"""Cython interface to Sylvan.


Reference
=========
    Tom van Dijk, Alfons Laarman, Jaco van de Pol
    "Multi-Core BDD Operations for
     Symbolic Reachability"
    PDMC 2012
    <https://doi.org/10.1016/j.entcs.2013.07.009>
    <https://github.com/utwente-fmt/sylvan>
"""
# Copyright 2016 by California Institute of Technology
# All rights reserved. Licensed under BSD-3.
#
import collections.abc as _abc
import logging
import pickle
import signal
import time
import typing as _ty

from cpython cimport bool as _py_bool
from libcpp cimport bool

import dd._abc as _dd_abc
from dd import _parser
from dd import bdd as _bdd
from dd cimport c_sylvan as sy


logger = logging.getLogger(__name__)


_Yes: _ty.TypeAlias = _py_bool
_Nat: _ty.TypeAlias = _dd_abc.Nat
_Cardinality: _ty.TypeAlias = _dd_abc.Cardinality
_VariableName: _ty.TypeAlias = _dd_abc.VariableName
_Level: _ty.TypeAlias = _dd_abc.Level
_VariableLevels: _ty.TypeAlias = _dd_abc.VariableLevels
_Assignment: _ty.TypeAlias = _dd_abc.Assignment
_Renaming: _ty.TypeAlias = _dd_abc.Renaming
_Formula: _ty.TypeAlias = _dd_abc.Formula


# TODO: check for invalid nodes returned by sylvan calls


cdef class BDD:
    """Wrapper of Sylvan manager.

    Interface similar to `dd.bdd.BDD`.
    Variable names are strings.
    Attributes:

      - `vars`: `set` of bit names as strings
    """

    cdef public object vars
    cdef public object _index_of_var
    cdef public object _var_with_index

    def __cinit__(
            self
            ) -> None:
        """Initialize BDD manager.

        Due to the architecture of `sylvan`,
        there is a single unique table,
        so you can create only one `BDD` instance at
        any given time.

        If the current `BDD` instance is `del`eted,
        then a new `BDD` instance can be created.
        But two `BDD` instances cannot coexist in
        the same process.
        """
        sy.lace_init(0, 10**6)
        sy.lace_startup(0, NULL, NULL)
        sy.LACE_ME_WRAP
        sy.sylvan_init_package(1LL<<25, 1LL<<26, 1LL<<24, 1LL<<25)
        sy.sylvan_init_bdd(1)

    def __init__(
            self,
            memory_estimate=None,
            initial_cache_size=None
            ) -> None:
        # self.configure(reordering=True, max_cache_hard=MAX_CACHE)
        self.vars = set()
        self._index_of_var = dict()  # map: str -> unique fixed int
        self._var_with_index = dict()

    def __dealloc__(
            self
            ) -> None:
        # n = len(self)
        # if n != 0:
        #     raise AssertionError(
        #         f'Still {n} nodes '
        #         'referenced upon shutdown.')
        sy.LACE_ME_WRAP
        sy.sylvan_quit()
        sy.lace_exit()

    def __eq__(
            self:
                BDD,
            other:
                BDD |
                None
            ) -> _Yes:
        """Return `True` if `other` has same manager.

        If `other is None`, then return `False`.
        """
        if other is None:
            return False
        # `sylvan` supports one manager only
        return True

    def __ne__(
            self:
                BDD,
            other:
                BDD |
                None
            ) -> _Yes:
        """Return `True` if `other` has different manager.

        If `other is None`, then return `True`.
        """
        if other is None:
            return True
        # `sylvan` supports one manager only
        return False

    def __len__(
            self
            ) -> _Cardinality:
        """Return number of nodes with non-zero references."""
        sy.LACE_ME_WRAP
        return sy.sylvan_count_refs()

    def __contains__(
            self,
            u:
                Function
            ) -> _Yes:
        if self is not u.bdd:
            raise ValueError(u)
        try:
            self.apply('not', u)
            return True
        except:
            return False

    def __str__(
            self
            ) -> str:
        return 'Binary decision diagram (Sylvan wrapper)'

    def configure(
            self,
            **kw
            ) -> dict[
                str,
                _ty.Any]:
        """Has no effect, present for compatibility only.

        Compatibility here refers to `BDD` classes in
        other modules of the package `dd`.
        """
        # TODO: use `sy.gc_enabled == 1` when not `static`
        garbage_collection = None
        d = dict(
            reordering=False,
            garbage_collection=garbage_collection,
            max_memory=None,
            loose_up_to=None,
            max_cache_soft=None,
            max_cache_hard=None,
            min_hit=None,
            max_growth=None,
            max_swaps=None,
            max_vars=None)
        return d

    cpdef tuple succ(
            self,
            u:
                Function):
        """Return `(level, low, high)` for `u`."""
        i = u._index  # level, assuming
            # static variable order
        v = u.low
        w = u.high
        # account for complement bit propagation
        if u.negated:
            v, w = ~ v, ~ w
        return i, v, w

    cdef incref(
            self,
            u:
                sy.BDD):
        sy.sylvan_ref(u)

    cdef decref(
            self,
            u:
                sy.BDD):
        sy.sylvan_deref(u)

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
                int |
                None=None):
        """Return index of variable named `var`.

        If a variable named `var` exists,
        the assert that it has `index`.
        Otherwise, create a variable named `var`
        with `index` (if given).

        If no reordering has yet occurred,
        then the returned index equals the level,
        provided `add_var` has been used so far.
        """
        sy.LACE_ME_WRAP
        # var already exists ?
        j = self._index_of_var.get(var)
        if j is not None:
            if not (j == index or index is None):
                raise AssertionError(j, index)
            return j
        # new var
        if index is None:
            index = len(self._index_of_var)
        j = index
        u = sy.sylvan_ithvar(j)
        if u == sy.sylvan_invalid:
            raise RuntimeError(
                f'failed to add var "{var}"')
        self._add_var(var, j)
        return j

    cpdef insert_var(
            self,
            var:
                _VariableName,
            level:
                _Level):
        """Create a new variable named `var`, at `level`."""
        raise Exception(
            'in `sylvan`, variable indices equal levels.\n'
            'Call method `BDD.add_var` instead.')

    cdef _add_var(
            self,
            var:
                _VariableName,
            index:
                int):
        """Add to `self` a *new* variable named `var`."""
        if var in self.vars:
            raise ValueError((var, self.vars))
        if var in self._index_of_var:
            raise ValueError((var, self._index_of_var))
        if index in self._var_with_index:
            raise ValueError((index, self._var_with_index))
        self.vars.add(var)
        self._index_of_var[var] = index
        self._var_with_index[index] = var
        if (len(self._index_of_var) !=
                len(self._var_with_index)):
            raise AssertionError((
                len(self._index_of_var),
                len(self._var_with_index),
                self._index_of_var,
                self._var_with_index))

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
        sy.LACE_ME_WRAP
        j = self._index_of_var[var]
        r = sy.sylvan_ithvar(j)
        return wrap(self, r)

    def var_at_level(
            self,
            level:
                _Level
            ) -> _VariableName:
        """Return name of variable at `level`."""
        j = level  # indices equal levels in `sylvan`
        if j not in self._var_with_index:
            levels = {
                var: self.level_of_var(var)
                for var in self._index_of_var}
            raise ValueError(
                f'no variable has level:  {level}, '
                'the current levels of all variables '
                f'are:  {levels}')
        var = self._var_with_index[j]
        return var

    def level_of_var(
            self,
            var:
                _VariableName
            ) -> _Level:
        """Return level of variable named `var`."""
        if var not in self._index_of_var:
            raise ValueError(
                f'undeclared variable "{var}", '
                'the declared variables are:'
                f'\n{self._index_of_var}')
        j = self._index_of_var[var]
        level = j
        return level

    cpdef set support(
            self,
            f:
                Function):
        """Return the variables that node `f` depends on."""
        if self is not f.bdd:
            raise ValueError(f)
        sy.LACE_ME_WRAP
        cube: sy.BDD
        cube = sy.sylvan_support(f.node)
        ids = set()
        while cube != sy.sylvan_true:
            # get var
            j = sy.sylvan_var(cube)
            ids.add(j)
            # descend
            u = sy.sylvan_low(cube)
            v = sy.sylvan_high(cube)
            if u != sy.sylvan_false:
                raise AssertionError(u)
            cube = v
        support = {self._var_with_index[j] for j in ids}
        return support

    cpdef Function let(
            self,
            definitions:
                _Renaming |
                _Assignment |
                dict[_VariableName, Function],
            u:
                Function):
        """Replace variables with `definitions` in `u`."""
        d = definitions
        if not d:
            logger.warning(
                'Call to `BDD.let` with no effect: '
                '`defs` is empty.')
            return u
        var = next(iter(d))
        value = d[var]
        if isinstance(value, _py_bool):
            return self._cofactor(u, d)
        elif isinstance(value, Function):
            return self._compose(u, d)
        try:
            value + 's'
        except TypeError:
            raise ValueError(
                'Key must be variable name as `str`, '
                'or Boolean value as `bool`, '
                f'or BDD node as `int`. Got: {value}')
        return self._rename(u, d)

    cpdef Function _compose(
            self,
            u:
                Function,
            var_sub:
                dict[_VariableName, Function]):
        if self is not u.bdd:
            raise ValueError(u)
        sy.LACE_ME_WRAP
        map: sy.BDDMAP
        j: sy.BDDVAR
        r: sy.BDD
        g: Function
        map = sy.sylvan_map_empty()
        for var, g in var_sub.items():
            j = self._index_of_var[var]
            map = sy.sylvan_map_add(map, j, g.node)
        r = sy.sylvan_compose(u.node, map)
        return wrap(self, r)

    cpdef Function _cofactor(
            self,
            u:
                Function,
            values:
                _Assignment):
        """Return the cofactor f|_g."""
        var_sub = {
            var: self.true if value else self.false
            for var, value in values.items()}
        return self._compose(u, var_sub)

    cpdef Function _rename(
            self,
            u:
                Function,
            dvars:
                _Renaming):
        """Return node `u` after renaming variables in `dvars`."""
        if self is not u.bdd:
            raise ValueError(u)
        var_sub = {
            var: self.var(sub) for var, sub in dvars.items()}
        r = self._compose(u, var_sub)
        return r

    def pick(
            self,
            u:
                Function,
            care_vars:
                _abc.Collection[
                    _VariableName] |
                None=None
            ) -> _Assignment:
        """Return a single assignment as `dict`."""
        return next(self.pick_iter(u, care_vars), None)

    def pick_iter(
            self,
            u:
                Function,
            care_vars:
                _abc.Collection[
                    _VariableName] |
                None=None
            ) -> _abc.Iterable[
                _Assignment]:
        """Return generator over assignments."""
        support = self.support(u)
        if care_vars is None:
            care_vars = support
        missing = {v for v in support if v not in care_vars}
        if missing:
            logger.warning(
                'Missing bits:  '
                f'support - care_vars = {missing}')
        cube = dict()
        value = True
        config = self.configure(reordering=False)
        for cube in self._sat_iter(u, cube, value, support):
            for m in _bdd._enumerate_minterms(cube, care_vars):
                yield m
        self.configure(reordering=config['reordering'])

    def _sat_iter(
            self,
            u:
                Function,
            cube:
                _Assignment,
            value:
                _py_bool,
            support:
                set[_VariableName]
            ) -> _Assignment:
        """Recurse to enumerate models."""
        if u.negated:
            value = not value
        # terminal ?
        if u.var is None:
            # high nodes are negated
            # the constant node is 0
            if not value:
                if not set(cube).issubset(support):
                    raise AssertionError(
                        set(cube).difference(support))
                yield cube
            return
        # non-terminal
        _, v, w = self.succ(u)
        var = u.var
        d0 = dict(cube)
        d0[var] = False
        d1 = dict(cube)
        d1[var] = True
        for x in self._sat_iter(v, d0, value, support):
            yield x
        for x in self._sat_iter(w, d1, value, support):
            yield x

    cpdef Function ite(
            self,
            g:
                Function,
            u:
                Function,
            v:
                Function):
        if self is not g.bdd:
            raise ValueError(g)
        if self is not u.bdd:
            raise ValueError(u)
        if self is not v.bdd:
            raise ValueError(v)
        sy.LACE_ME_WRAP
        r: sy.BDD
        r = sy.sylvan_ite(g.node, u.node, v.node)
        return wrap(self, r)

    cpdef Function apply(
            self,
            op:
                _dd_abc.OperatorSymbol,
            u:
                Function,
            v:
                _ty.Optional[Function]
                =None):
        """Return as `Function` the result of applying `op`."""
        if self is not u.bdd:
            raise ValueError(u)
        r: sy.BDD
        sy.LACE_ME_WRAP
        # unary
        if op in ('~', 'not', '!'):
            if v is not None:
                raise ValueError(v)
            r = sy.sylvan_not(u.node)
        elif v is None:
            raise ValueError(v)
        elif v.bdd is not self:
            raise ValueError(v)
        # binary
        if op in ('and', '/\\', '&', '&&'):
            r = sy.sylvan_and(u.node, v.node)
        elif op in ('or', r'\/', '|', '||'):
            r = sy.sylvan_or(u.node, v.node)
        elif op in ('#', 'xor', '^'):
            r = sy.sylvan_xor(u.node, v.node)
        elif op in ('=>', '->', 'implies'):
            r = sy.sylvan_imp(u.node, v.node)
        elif op in ('<=>', '<->', 'equiv'):
            r = sy.sylvan_biimp(u.node, v.node)
        elif op in ('diff', '-'):
            r = sy.sylvan_diff(u.node, v.node)
        elif op in (r'\A', 'forall'):
            r = sy.sylvan_forall(u.node, v.node)
        elif op in (r'\E', 'exists'):
            r = sy.sylvan_exists(u.node, v.node)
        if r == sy.sylvan_invalid:
            raise ValueError(
                f'unknown operator: "{op}"')
        return wrap(self, r)

    cpdef Function cube(
            self,
            dvars:
                _Assignment |
                set[_VariableName]):
        """Return node for cube over `dvars`.

        @param dvars:
            maps each variable to a `bool`.
            If `set` given, then all values assumed `True`.
        """
        # TODO: call sylvan cube function
        u = self.true
        if isinstance(dvars, set):
            for var in dvars:
                u &= self.var(var)
            return u
        for var, sign in dvars.items():
            v = self.var(var)
            if sign is False:
                v = ~v
            u &= v
        return u

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
        if self is not u.bdd:
            raise ValueError(u)
        sy.LACE_ME_WRAP
        c = set(qvars)
        cube = self.cube(c)
        # quantify
        if forall:
            r = sy.sylvan_forall(u.node, cube.node)
        else:
            r = sy.sylvan_exists(u.node, cube.node)
        return wrap(self, r)

    cpdef Function forall(
            self,
            qvars:
                _abc.Iterable[
                    _VariableName],
            u:
                Function):
        """Quantify `qvars` in `u` universally.

        Wraps method `quantify` to be more readable.
        """
        return self.quantify(u, qvars, forall=True)

    cpdef Function exist(
            self,
            qvars:
                _abc.Iterable[
                    _VariableName],
            u:
                Function):
        """Quantify `qvars` in `u` existentially.

        Wraps method `quantify` to be more readable.
        """
        return self.quantify(u, qvars, forall=False)

    cpdef assert_consistent(
            self):
        """Raise `AssertionError` if not consistent."""
        # c = Cudd_DebugCheck(self.manager)
        # if c != 0:
        #     raise AssertionError(c)
        n = len(self.vars)
        m = len(self._var_with_index)
        k = len(self._index_of_var)
        if n != m:
            raise AssertionError((n, m))
        if m != k:
            raise AssertionError((m, k))

    def add_expr(
            self,
            expr:
                _Formula
            ) -> Function:
        """Return node for `str` expression `e`."""
        return _parser.add_expr(expr, self)

    def to_expr(
            self,
            u:
                Function
            ) -> _Formula:
        if self is not u.bdd:
            raise ValueError(u)
        raise NotImplementedError()

    cpdef dump(
            self,
            u:
                Function,
            fname:
                str):
        """Dump BDD as DDDMP file `fname`."""
        if self is not u.bdd:
            raise ValueError(u)
        raise NotImplementedError()

    cpdef load(
            self,
            fname:
                str):
        """Return `Function` loaded from file `fname`."""
        raise NotImplementedError()

    @property
    def false(
            self
            ) -> Function:
        """`Function` for Boolean value false."""
        return self._bool(False)

    @property
    def true(
            self
            ) -> Function:
        """`Function` for Boolean value true."""
        return self._bool(True)

    cdef Function _bool(
            self,
            v:
                _py_bool):
        """Return terminal node for Boolean `v`."""
        r: sy.BDD
        if v:
            r = sy.sylvan_true
        else:
            r = sy.sylvan_false
        return wrap(self, r)


cpdef Function restrict(
        u:
            Function,
        care_set:
            Function):
    if u.bdd is not care_set.bdd:
        raise ValueError((u, care_set))
    sy.LACE_ME_WRAP
    r: sy.BDD
    r = sy.sylvan_restrict(u.node, care_set.node)
    return wrap(u.bdd, r)


cpdef Function and_exists(
        u:
            Function,
        v:
            Function,
        qvars:
            set[_VariableName]):
    r"""Return `\E qvars:  u /\ v`."""
    if u.bdd is not v.bdd:
        raise ValueError((u, v))
    bdd = u.bdd
    sy.LACE_ME_WRAP
    cube = bdd.cube(qvars)
    r = sy.sylvan_and_exists(u.node, v.node, cube.node)
    return wrap(u.bdd, r)


cpdef Function or_forall(
        u:
            Function,
        v:
            Function,
        qvars:
            set[_VariableName]):
    r"""Return `\A qvars:  u \/ v`."""
    if u.bdd is not v.bdd:
        raise ValueError((u, v))
    bdd = u.bdd
    sy.LACE_ME_WRAP
    cube = bdd.cube(qvars)
    r = sy.sylvan_and_exists(
        sy.sylvan_not(u.node),
        sy.sylvan_not(v.node),
        cube.node)
    r = sy.sylvan_not(r)
    return wrap(u.bdd, r)


cpdef reorder(
        bdd:
            BDD,
        dvars:
            _VariableLevels |
            None=None):
    """Reorder `bdd` to order in `dvars`.

    If `dvars` is `None`, then invoke group sifting.
    """
    raise NotImplementedError


def copy_vars(
        source:
            BDD,
        target:
            BDD
        ) -> None:
    """Copy variables, preserving Sylvan indices."""
    for var, index in source._index_of_var.items():
        target.add_var(var, index=index)


cdef Function wrap(
        bdd:
            BDD,
        node:
            sy.BDD):
    """Return a `Function` that wraps `node`."""
    f = Function()
    f.init(node, bdd)
    return f


cdef class Function:
    """Wrapper of `BDD` from Sylvan.

    Attributes (those that are properties are
    described in their docstrings):

      - `_index`
      - `var`
      - `low`
      - `high`
      - `negated`
      - `support`
      - `dag_size`

    In Python, use as:

    ```python
    from dd import sylvan

    bdd = sylvan.BDD()
    u = bdd.true
    v = bdd.false
    w = u | ~ v
    ```

    In Cython, use as:

    ```cython
    bdd = BDD()
    u: sy.BDD
    u = sylvan_true
    f = Function()
    f.init(u)
    ```
    """

    __weakref__: object
    cdef public BDD bdd
    node: sy.BDD

    cdef init(
            self,
            u:
                sy.BDD,
            bdd:
                BDD):
        if u == sy.sylvan_invalid:
            raise ValueError(
                '`sy.BDD u` is `NULL` pointer.')
        self.bdd = bdd
        self.node = u
        sy.sylvan_ref(u)

    def __hash__(
            self
            ) -> int:
        return int(self)

    @property
    def _index(
            self
            ) -> _Nat:
        """Index of `self.node`."""
        return sy.sylvan_var(self.node)

    @property
    def var(
            self
            ) -> _VariableName:
        """Variable at level where this node is."""
        if sy.sylvan_isconst(self.node):
            return None
        return self.bdd._var_with_index[self._index]

    @property
    def level(
            self
            ) -> _Level:
        """Level where this node is."""
        raise NotImplementedError

    @property
    def ref(
            self
            ) -> _Cardinality:
        """Sum of reference counts of node and its negation."""
        # u = Cudd_Regular(self.node)
        # return u.ref
        raise NotImplementedError

    @property
    def low(
            self
            ) -> Function:
        """Return "else" node as `Function`."""
        # propagates complement bit
        u = sy.sylvan_low(self.node)
        return wrap(self.bdd, u)

    @property
    def high(
            self
            ) -> Function:
        """Return "then" node as `Function`."""
        u = sy.sylvan_high(self.node)
        return wrap(self.bdd, u)

    @property
    def negated(
            self
            ) -> _Yes:
        """Return `True` if `self` is a complemented edge."""
        # read the definition of `BDD_HASMARK`
        # in `sylvan_bdd`
        if self.node & sy.sylvan_complement:
            return True
        else:
            return False

    @property
    def support(
            self
            ) -> set[_VariableName]:
        """Return `set` of variables in support."""
        return self.bdd.support(self)

    def __dealloc__(
            self
            ) -> None:
        sy.sylvan_deref(self.node)
        self.node = 0

    def __str__(
            self
            ) -> str:
        return (
            'Function(DdNode with: '
            f'node={self.node}, '
            f'var_index={self._index}, '
            f'ref_count={None})')

    def __len__(
            self
            ) -> _Cardinality:
        return sy.sylvan_nodecount(self.node)

    @property
    def dag_size(
            self
            ) -> _Cardinality:
        """Return number of BDD nodes.

        This is the number of BDD nodes that
        are reachable from this BDD reference,
        i.e., with `self` as root.
        """
        return len(self)

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
        if self.bdd is not other_.bdd:
            raise ValueError((self, other_))
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
        if self.bdd is not other_.bdd:
            raise ValueError((self, other_))
        return self.node != other_.node

    def __invert__(
            self:
                Function
            ) -> Function:
        r = sy.sylvan_not(self.node)
        return wrap(self.bdd, r)

    def __and__(
            self:
                Function,
            other:
                Function
            ) -> Function:
        if self.bdd is not other.bdd:
            raise ValueError((self, other))
        sy.LACE_ME_WRAP
        r = sy.sylvan_and(self.node, other.node)
        return wrap(self.bdd, r)

    def __or__(
            self:
                Function,
            other:
                Function
            ) -> Function:
        if self.bdd is not other.bdd:
            raise ValueError((self, other))
        sy.LACE_ME_WRAP
        r = sy.sylvan_or(self.node, other.node)
        return wrap(self.bdd, r)
