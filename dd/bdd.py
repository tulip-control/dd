"""Ordered binary decision diagrams.


References
==========

Randal E. Bryant
    "Graph-based algorithms for Boolean function manipulation"
    IEEE Transactions on Computers
    Volume C-35, No. 8, August, 1986, pages 677--690

Karl S. Brace, Richard L. Rudell, Randal E. Bryant
    "Efficient implementation of a BDD package"
    27th ACM/IEEE Design Automation Conference (DAC), 1990
    pages 40--45

Richard Rudell
    "Dynamic variable ordering for
    ordered binary decision diagrams"
    IEEE/ACM International Conference on
    Computer-Aided Design (ICCAD), 1993
    pages 42--47

Christel Baier and Joost-Pieter Katoen
    "Principles of model checking"
    MIT Press, 2008
    Section 6.7, pages 381--421

Fabio Somenzi
    "Binary decision diagrams"
    Calculational system design, Vol.173
    NATO Science Series F: Computer and systems sciences
    pages 303--366, IOS Press, 1999

Henrik R. Andersen
    "An introduction to binary decision diagrams"
    Lecture notes for "Efficient Algorithms and Programs", 1999
    The IT University of Copenhagen
"""
# Copyright 2014 by California Institute of Technology
# All rights reserved. Licensed under BSD-3.
#
import collections.abc as _abc
import functools as _ft
import inspect
import logging
import pickle
import pprint as _pp
import sys
import typing as _ty
import warnings

import dd._abc
import dd._parser as _parser
import dd._utils as _utils


logger = logging.getLogger(__name__)
REORDER_STARTS = 100
REORDER_FACTOR = 2
GROWTH_FACTOR = 2


def _request_reordering(
        bdd:
            'BDD'
        ) -> None:
    """Raise `NeedsReordering` if `len(bdd)` >= threshold."""
    if bdd._last_len is None:
        return
    if len(bdd) >= REORDER_FACTOR * bdd._last_len:
        raise _NeedsReordering()


_Ret = _ty.TypeVar('_Ret')
_CallablePR: _ty.TypeAlias = _abc.Callable[..., _Ret]


def _try_to_reorder(
        func:
            _CallablePR
        ) -> _CallablePR:
    """Decorator that serves reordering requests."""
    @_ft.wraps(func)
    def _wrapper(
            bdd:
                'BDD',
            *args,
            **kwargs
            ) -> _Ret:
        with _ReorderingContext(bdd):
            return func(
                bdd,
                *args,
                **kwargs)
        logger.info('Reordering needed...')
        # disable reordering requests while swapping
        bdd._last_len = None
        reorder(bdd)
        len_after = len(bdd)
        # try again,
        # reordering disabled to avoid livelock
        with _ReorderingContext(bdd):
            r = func(
                bdd,
                *args, **kwargs)
        # enable reordering requests
        bdd._last_len = GROWTH_FACTOR * len_after
        return r
    return _wrapper


class _ReorderingContext:
    """Context manager that tracks decorator nesting."""

    def __init__(
            self,
            bdd:
                'BDD'
            ) -> None:
        self.bdd = bdd
        self.nested = None

    def __enter__(
            self):
        self.nested = self.bdd._reordering_context
        self.bdd._reordering_context = True

    def __exit__(
            self,
            ex_type,
            ex_value,
            tb):
        self.bdd._reordering_context = self.nested
        not_nested = (
            ex_type is _NeedsReordering and
            not self.nested)
        if not_nested:
            return True


class _NeedsReordering(Exception):
    """Raise this to request reordering."""


_Yes: _ty.TypeAlias = dd._abc.Yes
_Nat: _ty.TypeAlias = dd._abc.Nat
_Cardinality: _ty.TypeAlias = dd._abc.Cardinality
_VariableName: _ty.TypeAlias = dd._abc.VariableName
_Level: _ty.TypeAlias = dd._abc.Level
_VariableLevels: _ty.TypeAlias = dd._abc.VariableLevels
_Assignment: _ty.TypeAlias = dd._abc.Assignment
_Renaming: _ty.TypeAlias = dd._abc.Renaming
_Node: _ty.TypeAlias = _Nat
_Ref: _ty.TypeAlias = int
    # ```tla
    # ASSUME
    #     _Ref \neq 0
    # ```
_Fork: _ty.TypeAlias = tuple[
    _Level,
    _Ref | None,
    _Node | None]
_Formula: _ty.TypeAlias = dd._abc.Formula


class BDD(dd._abc.BDD[_Ref]):
    """Shared ordered binary decision diagram.

    The terminal node is 1.
    Nodes are positive integers,
    edges signed integers.
    Complemented edges are represented as
    negative integers.
    Values returned by methods are edges,
    possibly complemented.

    Attributes:
      - `vars`:
        `dict` mapping `variables` to `int` levels
      - `roots`:
        (optional) edges
      - `max_nodes`:
        raise `Exception` if this limit is reached.
        The default value is `sys.maxsize` in Python 3.
        Increase it if needed.

    To ensure that the target node of a returned edge
    is not garbage collected during reordering,
    increment its reference counter:

    `bdd.incref(edge)`

    To ensure that `ite` maintains reducedness add new
    nodes using `find_or_add` to keep the table updated,
    or call `update_predecessors` prior to calling `ite`.
    """
    # omitted docstrings are inheritted from `super()`

    def __init__(
            self,
            levels:
                _VariableLevels |
                None=None
            ) -> None:
        if levels is None:
            levels = dict()
        _assert_valid_ordering(levels)
        self._pred: dict[
            _Fork,
            _Node
            ] = dict()
        self._succ: dict[
            _Node,
            _Fork
            ] = dict()
        self._ref: dict[
            _Node,
            _Nat
            ] = dict()
        # all smaller positive integers
        # are used as node indices, and
        # no larger integers are used
        # as node indices
        self._min_free: _Nat = 2
            # minimum number unused as BDD index
        self._ite_table: dict[
            tuple[_Ref, _Ref, _Ref],
            _Ref
            ] = dict()
            # `(predicate, then, else) |-> edge`
            # cache for ternary conditional
            # ("ite" means "if-then-else")
        self.vars: _VariableLevels = dict()
        self._level_to_var: dict[
            _Level,
            _VariableName
            ] = dict()
            # inverse of `self.vars`
        # handle no vars
        self._init_terminal(len(self.vars))
        # for decorator nesting
        self._reordering_context: _Yes = False
        # after last reordering
        self._last_len: _Nat | None = None
        for var, level in levels.items():
            self.add_var(var, level)
        # set of edges
        # optional
        self.roots: set = set()
        self.max_nodes: _Nat = sys.maxsize

    def __copy__(
            self
            ) -> 'BDD':
        bdd = BDD(self.vars)
        bdd._pred = dict(self._pred)
        bdd._succ = dict(self._succ)
        bdd._ref = dict(self._ref)
        bdd._min_free = self._min_free
        bdd.roots = set(self.roots)
        bdd.max_nodes = self.max_nodes
        return bdd

    def __del__(
            self
            ) -> None:
        """Assert that all remaining nodes are garbage."""
        if self._ref[1] > 0:
            self.decref(1)
                # free ref from `self._init_terminal()`
        self.collect_garbage()
        refs_exist = any(
            v != 0
            for v in self._ref.values())
        if not refs_exist:
            return
        stack = inspect.stack()
        stack_str = _pp.pformat(stack)
        raise AssertionError(
            'There are nodes still referenced '
            'upon shutdown. Details:\n'
            f'{self._ref}\n'
            f'{self._succ}\n'
            f'{self.vars}\n'
            f'{self._ite_table}\n'
            f'{type(self)}\n'
            f'{stack_str}')

    def __len__(
            self
            ) -> _Cardinality:
        return len(self._succ)

    def __contains__(
            self,
            u:
                _Ref
            ) -> _Yes:
        return abs(u) in self._succ

    def __iter__(
            self):
        return iter(self._succ)

    def __str__(
            self
            ) -> str:
        return (
            'Binary decision diagram:\n'
            '------------------------\n'
            f'var levels: {self.vars}\n'
            f'roots: {self.roots}\n')

    def configure(
            self,
            **kw
            ) -> dict[
                str,
                _ty.Any]:
        """Read and apply parameter values.

        First read parameter values (returned as `dict`),
        then apply `kw`. Available keyword arguments:

        - `'reordering'`:
          if `True` then enable, else disable
        """
        d = dict(
            reordering=(self._last_len is not None))
        for k, v in kw.items():
            if k == 'reordering':
                if v:
                    self._last_len = max(
                        REORDER_STARTS, len(self))
                else:
                    self._last_len = None
            else:
                raise ValueError(
                    f'Unknown parameter "{k}"')
        return d

    @property
    def ordering(
            self):
        raise DeprecationWarning(
            'use `dd.bdd.BDD.vars` '
            'instead of `.ordering`')

    def _init_terminal(
            self,
            level:
                _Level
            ) -> None:
        """Place constant node `1`.

        Used for initialization and to shift node `1` to
        lower levels, as fresh variables are being added.
        """
        u = 1
        t = (level, None, None)
        told = self._succ.setdefault(u, t)
        self._pred.pop(told, None)
        self._succ[u] = t
        self._pred[t] = u
        self._ref.setdefault(u, 1)

    def succ(
            self,
            u:
                _Ref
            ) -> _Fork:
        """Return `(level, low, high)` for `abs(u)`."""
        return self._succ[abs(u)]

    def incref(
            self,
            u:
                _Ref
            ) -> None:
        """Increment reference count of node `u`."""
        self._ref[abs(u)] += 1

    def decref(
            self,
            u:
                _Ref
            ) -> None:
        """Decrement reference count of node `u`,

        with 0 as minimum value.
        """
        if self._ref[abs(u)] <= 0:
            n = self._ref[abs(u)]
            warnings.warn(
                'The method `dd.bdd.BDD.decref` was called '
                f'for BDD node {u} with reference count {n}. '
                'This call has no effect. Calling `decref` '
                'for a node with nonpositive reference count '
                'may indicate a programming error.',
                UserWarning)
            return
        self._ref[abs(u)] -= 1

    def ref(
            self,
            u:
                _Ref
            ) -> _Nat:
        """Return reference count of edge `u`."""
        return self._ref[abs(u)]

    def declare(
            self,
            *variables:
                _VariableName
            ) -> None:
        for var in variables:
            self.add_var(var)

    def add_var(
            self,
            var:
                _VariableName,
            level:
                _Level |
                None=None
            ) -> _Level:
        """Declare a variable named `var` at `level`.

        The new variable is Boolean-valued.

        If `level` is absent, then add the new variable
        at the bottom level.

        Raise `ValueError` if:
        - `var` already exists at a level
          different than the given `level`, or
        - the given `level` is already used by
          another variable
        - `level` is not given and `var` does not exist,
          and the next level larger than the
          current bottom level is already used by
          another variable.

        If `var` already exists, and either `level`
        is not given, or `var` has `level`,
        then return without raising exceptions.

        @param var:
            name of new variable to declare
        @param level:
            level of new variable to declare
        @return:
            level of variable `var`
        """
        # var already exists ?
        if var in self.vars:
            return self._check_var(var, level)
        # level already used ?
        level = self._next_free_level(var, level)
        # update the mappings between
        # vars and levels
        self.vars[var] = level
        self._level_to_var[level] = var
        # move the leaf node to
        # the new bottom level
        self._init_terminal(len(self.vars))
        return level

    def _check_var(
            self,
            var:
                _VariableName,
            level:
                _Level |
                None
            ) -> _Level:
        """Assert that `var` has `level`.

        Return the level of `var`.

        Exceptions:
        - raise `ValueError` if:
          - `var` is not a declared variable, or
          - `level is not None` and
            `level` is not the level of variable `var`
        - raise `RuntimeError` if an unexpected
          value of level is found in `self.vars[var]`

        @param var:
            name of variable
        @param level:
            level of variable
        """
        if var not in self.vars:
            raise ValueError(
                f'"{var}" is not the name of '
                'a declared variable')
        var_level = self.vars[var]
        if var_level is None or var_level < 0:
            raise RuntimeError(
                f'`{self.vars[var] = }` '
                '(expected integer >= 0)')
        if level is None or level == var_level:
            return var_level
        raise ValueError(
            f'for variable "{var}": '
            f'{level} = level != '
            f'level of "{var}" = {var_level}')

    def _next_free_level(
            self,
            var,
            level:
                _Level |
                None
            ) -> _Nat:
        """Return a free level.

        Raise `ValueError`:
        - if the given `level` is already used by
          a variable, or
        - if `level is None` and the next level is
          used by a variable.

        If `level is None`, then return the
        next level after the current largest level.
        Otherwise, return the given `level`.

        @param var:
            name of intended new variable,
            used only to form the `ValueError` message
        @param level:
            level of intended new variable
        """
        # assume next level is unoccupied
        if level is None:
            level = len(self.vars)
        if level < 0:
            raise AssertionError(
                f'`{level = } < 0')
        # level already used ?
        other = self._level_to_var.get(level)
        if other is None:
            return level
        raise ValueError(
            f'level {level} is already '
            f'used by variable "{other}", '
            'choose another level for the '
            f'new variable "{var}"')

    @_try_to_reorder
    def var(
            self,
            var:
                _VariableName
            ) -> _Ref:
        if var not in self.vars:
            raise ValueError(
                f'undeclared variable "{var}", '
                'the declared variables are:\n'
                f' {self.vars}')
        j = self.vars[var]
        u = self.find_or_add(j, -1, 1)
        return u

    def var_at_level(
            self,
            level:
                _Level
            ) -> _VariableName:
        if level not in self._level_to_var:
            raise ValueError(
                f'no variable has level:  {level}, '
                'the current levels of all variables '
                f'are:  {self.vars}')
        return self._level_to_var[level]

    def level_of_var(
            self,
            var:
                _VariableName
            ) -> _Level:
        if var not in self.vars:
            raise ValueError(
                f'name "{var}" is not '
                'a declared variable, '
                'the declared variables are:'
                f' {self.vars}')
        return self.vars[var]

    @property
    def var_levels(
            self
            ) -> _VariableLevels:
        return dict(self.vars)

    @_ty.overload
    def _map_to_level(
            self,
            d:
                _abc.Mapping[
                    _VariableName,
                    _ty.Any] |
                _abc.Mapping[
                    _Level,
                    _ty.Any]
            ) -> dict[_Level, bool]:
        ...

    @_ty.overload
    def _map_to_level(
            self,
            d:
                _abc.Set[
                    _VariableName] |
                _abc.Set
                    [_Level]
            ) -> set[_Level]:
        ...

    def _map_to_level(
            self,
            d:
                _abc.Mapping[
                    _VariableName,
                    _ty.Any] |
                _abc.Mapping[
                    _Level,
                    _ty.Any] |
                _abc.Set[
                    _VariableName] |
                _abc.Set[
                    _Level]
            ) -> (
                dict[_Level, bool] |
                set[_Level]):
        """Map keys of `d` to variable levels.

        Uses `self.vars` to map the keys to levels.

        If `d` is an iterable but not a mapping,
        then an iterable is returned.
        """
        match d:
            case _abc.Mapping():
                d = dict(d)
            case _abc.Set():
                d = set(d)
            case _:
                raise TypeError(d)
        if not d:
            match d:
                case dict():
                    return dict()
                case set():
                    return set()
                case _:
                    raise TypeError(d)
        # are keys variable names ?
        u = next(iter(d))
        if u not in self.vars:
            self._assert_keys_are_levels(d)
            match d:
                case dict():
                    return {
                        int(k): v
                        for k, v in d.items()}
                case set():
                    return set(map(int, d))
                case _:
                    raise ValueError(d)
        if isinstance(d, _abc.Mapping):
            return {
                self.vars[var]: bool(val)
                for var, val in
                    d.items()}
        else:
            return {
                self.vars[k]
                for k in d}

    def _assert_keys_are_levels(
            self,
            kv:
                _abc.Iterable
            ) -> None:
        """Assert that `kv` values are levels.

        Raise `ValueError` if not.
        """
        not_levels = set()
        def key_is_level(
                key
                ) -> _Yes:
            is_level = (
                key in self._level_to_var)
            if not is_level:
                not_levels.add(key)
            return is_level
        keys_are_levels = all(map(
            key_is_level, kv))
        if keys_are_levels:
            return
        def fmt(key):
            return (
                f'key `{key}` '
                'is not a level')
        errors = ',\n'.join(map(
            fmt, not_levels))
        raise ValueError(
            f'{errors},\n'
            'currently the levels are:\n'
            f'{self._level_to_var = }')

    def _top_var(
            self,
            *nodes:
                _Ref
            ) -> _Level:
        def level_of(node):
            level, *_ = self._succ[abs(node)]
            return level
        return min(map(level_of, nodes))

    def copy(
            self,
            u:
                _Ref,
            other:
                'BDD'
            ) -> _Ref:
        """Transfer BDD with root `u` to `other`."""
        return copy_bdd(u, self, other)

    def descendants(
            self,
            roots:
                _abc.Iterable[_Ref]
            ) -> set[_Ref]:
        """Return nodes reachable from `roots`.

        Nodes pointed to by references in
        `roots` are included.
        Nodes are represented as positive integers.
        """
        abs_roots = set(map(abs, roots))
        visited = set()
        for u in abs_roots:
            visited.add(1)
            self._descendants(u, visited)
        if not abs_roots.issubset(visited):
            raise AssertionError(
                (abs_roots, visited))
        return visited

    def _descendants(
            self,
            u:
                _Ref,
            visited:
                set[_Node]
            ) -> None:
        r = abs(u)
        if r == 1 or r in visited:
            return
        _, v, w = self._succ[r]
        if not v:
            raise AssertionError(v)
        if not w:
            raise AssertionError(w)
        self._descendants(v, visited)
        self._descendants(w, visited)
        visited.add(r)

    def is_essential(
            self,
            u:
                _Ref,
            var:
                _VariableName
            ) -> _Yes:
        """Return `True` if `var` is essential for node `u`.

        If `var` is a name undeclared in
        `self.vars`, return `False`.
        """
        i = self.vars.get(var)
        if i is None:
            return False
        iu, v, w = self._succ[abs(u)]
        # var above node u ?
        if i < iu:
            return False
        if i == iu:
            return True
        # u depends on node labeled with var ?
        if not v:
            raise AssertionError(v)
        if not w:
            raise AssertionError(w)
        if self.is_essential(v, var):
            return True
        if self.is_essential(w, var):
            return True
        return False

    def support(
            self,
            u:
                _Ref,
            as_levels:
                _Yes=False
            ) -> set[
                _VariableName]:
        levels = set()
        nodes = set()
        self._support(u, levels, nodes)
        if as_levels:
            return levels
        return {self.var_at_level(i) for i in levels}

    def _support(
            self,
            u:
                _Ref,
            levels:
                set[_Level],
            nodes:
                set[_Ref]):
        """Recurse to collect variables in support."""
        # exhausted all vars ?
        if len(levels) == len(self.vars):
            return
        # visited ?
        r = abs(u)
        if r in nodes:
            return
        nodes.add(r)
        # terminal ?
        if r == 1:
            return
        # add var
        i, v, w = self._succ[r]
        if not v:
            raise AssertionError(v)
        if not w:
            raise AssertionError(w)
        levels.add(i)
        # recurse
        self._support(v, levels, nodes)
        self._support(w, levels, nodes)

    def levels(
            self,
            skip_terminals:
                _Yes=False
            ) -> _abc.Iterable[
                tuple[
                    _Ref,
                    _Level,
                    _Ref,
                    _Node]]:
        """Return generator of tuples `(u, i, v, w)`.

        Where `i` ranges from terminals to root.

        @param skip_terminals:
            if `True`, then omit
            terminal nodes.
        """
        if skip_terminals:
            n = len(self.vars) - 1
        else:
            n = len(self.vars)
        for i in range(n, -1, -1):
            for u, (j, v, w) in self._succ.items():
                if i != j:
                    continue
                yield u, i, v, w

    def _levels(
            self
            ) -> dict[
                _Level,
                set[_Node]]:
        """Return mapping from levels to nodes."""
        n = len(self.vars)
        levels = {
            i: set()
            for var, i in
                self.vars.items()}
        levels[n] = set()
        for u, (i, v, w) in self._succ.items():
            levels[i].add(u)
        levels.pop(n)
        return levels

    @_try_to_reorder
    def reduction(
            self):
        """Return copy reduced with respect to `self.vars`.

        This function has educational value.
        """
        # terminals
        bdd = BDD(self.vars)
        umap = {1: 1}
        # non-terminals
        levels = self.levels(
            skip_terminals=True)
        for u, i, v, w in levels:
            if u <= 0:
                raise AssertionError(u)
            p, q = umap[abs(v)], umap[abs(w)]
            p = _flip(p, v)
            q = _flip(q, w)
            r = bdd.find_or_add(i, p, q)
            if r <= 0:
                raise AssertionError(r)
            umap[u] = r
        for v in self.roots:
            p = umap[abs(v)]
            p = _flip(p, v)
            bdd.roots.add(p)
        return bdd

    def undeclare_vars(
            self,
            *vrs
            ) -> set[str]:
        """Remove unused variables `vrs` from `self.vars`.

        Asserts that each variable in `vrs` corresponds to
        an empty level.

        If `vrs` is empty, then remove all unused variables.

        Garbage collection may need to be called before
        calling `undeclare_vars`, in order to collect
        unused nodes to obtain empty levels.
        """
        for var in vrs:
            if var not in self.vars:
                raise ValueError(
                    f'name "{var}" is not '
                    'a declared variable. '
                    'The declared variables are:\n'
                    f'{self.vars}')
        full_levels = {
            i
            for i, _, _ in
                self._succ.values()}
        # remove only unused variables
        for var in vrs:
            level = self.level_of_var(var)
            if level in full_levels:
                raise ValueError(
                    f'the given variable "{var}" is not '
                    'at an empty level (i.e., there still '
                    f'exist BDD nodes at level {level}, '
                    f'where variable "{var}" is)')
        # keep unused variables not in `vrs`
        if vrs:
            full_levels |= {
                level
                for var, level in
                    self.vars.items()
                if var not in vrs}
        # map old to new levels
        n = 1 + len(self.vars)
            # include terminal
        new_levels = [
            i
            for i in range(n)
            if i in full_levels]
        new_levels = {
            i: new
            for new, i in
                enumerate(new_levels)}
        # update variables and level declarations
        rm_vars = {
            var for var, level in
                self.vars.items()
            if level not in full_levels}
        self.vars = {
            var: new_levels[old]
            for var, old in self.vars.items()
            if old in full_levels}
        self._level_to_var = {
            k: var
            for var, k in self.vars.items()}
        # update node levels
        self._succ = {
            u: (new_levels[i], v, w)
            for u, (i, v, w) in
                self._succ.items()}
        self._pred = {
            v: k
            for k, v in
                self._succ.items()}
        # clear cache
        self._ite_table = dict()
        return rm_vars

    def let(
            self,
            definitions:
                _Renaming |
                _Assignment |
                dict[
                    _VariableName,
                    _Ref],
            u:
                _Ref
            ) -> _Ref:
        d = definitions
        if not d:
            logger.warning(
                'Call to `BDD.let` with no effect: '
                '`defs` is empty.')
            return u
        var = next(iter(definitions))
        value = d[var]
        if isinstance(value, bool):
            return self.cofactor(u, d)
        elif isinstance(value, int):
            return self.compose(u, d)
        try:
            value + 's'
        except TypeError:
            raise ValueError(
                'Key must be var name as `str`, '
                'or Boolean value as `bool`, '
                'or BDD node as `int`.')
        return self.rename(u, d)

    @_try_to_reorder
    def compose(
            self,
            f:
                _Ref,
            var_sub:
                dict[
                    _VariableName,
                    _Ref]
            ) -> _Ref:
        """Return substitutions `var_sub` in `f`.

        @param f:
            node
        @param var_sub:
            `dict` that maps variables to BDD nodes
        """
        cache = dict()
        if len(var_sub) == 1:
            (var, g), = var_sub.items()
            j = self.level_of_var(var)
            return self._compose(
                f, j, g, cache)
        else:
            dvars = {
                self.level_of_var(var): g
                for var, g in
                    var_sub.items()}
            return self._vector_compose(
                f, dvars, cache)

    def _compose(
            self,
            f:
                _Ref,
            j:
                _Level,
            g:
                _Ref,
            cache:
                dict[
                    tuple[_Ref, _Ref],
                    _Ref]
            ) -> _Ref:
        # terminal ?
        if abs(f) == 1:
            return f
        # cached ?
        if (f, g) in cache:
            return cache[(f, g)]
        # independent of j ?
        i, v, w = self._succ[abs(f)]
        if not v:
            raise AssertionError(v)
        if not w:
            raise AssertionError(w)
        # below j ?
        if j < i:
            return f
        elif i == j:
            r = self.ite(g, w, v)
            # complemented edge ?
            if f < 0:
                r = -r
        else:
            if i >= j:
                raise AssertionError(
                    (i, j))
            k, _, _ = self._succ[abs(g)]
            z = min(i, k)
            f0, f1 = self._top_cofactor(f, z)
            g0, g1 = self._top_cofactor(g, z)
            p = self._compose(
                f0, j, g0,
                cache)
            q = self._compose(
                f1, j, g1,
                cache)
            r = self.find_or_add(z, p, q)
        cache[(f, g)] = r
        return r

    def _vector_compose(
            self,
            f:
                _Ref,
            level_sub:
                dict[_Level, _Ref],
            cache:
                dict[_Node, _Ref]
            ) -> _Ref:
        # terminal ?
        if abs(f) == 1:
            return f
        # cached ?
        r = cache.get(abs(f))
        if r is not None:
            if r == 0:
                raise AssertionError(r)
            # complement ?
            if f < 0:
                r = -r
            return r
        # recurse
        i, v, w = self._succ[abs(f)]
        if not v:
            raise AssertionError(v)
        if not w:
            raise AssertionError(w)
        p = self._vector_compose(
            v, level_sub,
            cache)
        q = self._vector_compose(
            w, level_sub,
            cache)
        # map this level
        g = level_sub.get(i)
        if g is None:
            g = self.find_or_add(i, -1, 1)
        r = self.ite(g, q, p)
        # memoize
        cache[abs(f)] = r
        # complement ?
        if f < 0:
            r = -r
        return r

    @_try_to_reorder
    def rename(
            self,
            u:
                _Ref,
            dvars:
                _Renaming
            ) -> _Ref:
        """Efficient rename to non-essential neighbors.

        @param dvars:
            `dict` from variabe levels to variable levels
            or from variable names to variable names
        """
        return rename(u, self, dvars)

    def _top_cofactor(
            self,
            u:
                _Ref,
            i:
                _Level
            ) -> tuple[
                _Ref,
                _Ref]:
        """Return successor pair with respect to level `i`."""
        # terminal node ?
        if abs(u) == 1:
            return (u, u)
        # non-terminal node
        iu, v, w = self._succ[abs(u)]
        if not v:
            raise AssertionError(v)
        if not w:
            raise AssertionError(w)
        # u independent of var ?
        if i < iu:
            return (u, u)
        if iu != i:
            raise AssertionError(
                'for i > iu, call cofactor instead '
                f'({i = }, {iu = })')
        # u labeled with var
        # complement ?
        if u < 0:
            v, w = -v, -w
        return (v, w)

    @_try_to_reorder
    def cofactor(
            self,
            u:
                _Ref,
            values:
                _Assignment
            ) -> _Ref:
        """Replace variables in `u` with Booleans."""
        level_values = self._map_to_level(values)
        cache = dict()
        ordvar = sorted(level_values)
        j = 0
        if abs(u) not in self:
            raise ValueError(
                f'node {u} not in `self`')
        return self._cofactor(
            u, j, ordvar, level_values, cache)

    def _cofactor(
            self,
            u:
                _Ref,
            j:
                _Level,
            ordvar:
                list[_Level],
            values:
                dict[_Level, bool],
            cache:
                dict[_Ref, _Ref]
            ) -> _Ref:
        """Recurse to compute cofactor."""
        # terminal ?
        if abs(u) == 1:
            return u
        # memoized ?
        if u in cache:
            return cache[u]
        i, v, w = self._succ[abs(u)]
        if not v:
            raise AssertionError(v)
        if not w:
            raise AssertionError(w)
        n = len(ordvar)
        # skip nonessential variables
        while j < n:
            if ordvar[j] < i:
                j += 1
            else:
                break
        if j == n:
            # exhausted valuation
            return u
        if j >= n:
            raise AssertionError((j, n))
        # recurse
        if i in values:
            val = values[i]
            if bool(val):
                v = w
            r = self._cofactor(
                v, j,
                ordvar, values,
                cache)
        else:
            p = self._cofactor(
                v, j,
                ordvar, values,
                cache)
            q = self._cofactor(
                w, j,
                ordvar, values,
                cache)
            r = self.find_or_add(i, p, q)
        # complement ?
        if u < 0:
            r = -r
        cache[u] = r
        return r

    @_try_to_reorder
    def quantify(
            self,
            u:
                _Ref,
            qvars:
                _abc.Iterable[
                    _VariableName],
            forall:
                _Yes=False
            ) -> _Ref:
        """Return existential or universal abstraction.

        @param u:
            node
        @param qvars:
            quantified variables
        @param forall:
            if `True`,
            then quantify `qvars` universally,
            else existentially.
        """
        qvars = self._map_to_level(set(qvars))
        cache = dict()
        ordvar = sorted(qvars)
        j = 0
        return self._quantify(
            u, j, ordvar,
            qvars, forall,
            cache)

    def _quantify(
            self,
            u:
                _Ref,
            j:
                _Level,
            ordvar:
                list[_Level],
            qvars:
                set[_Level],
            forall:
                _Yes,
            cache:
                dict[_Ref, _Ref]
            ) -> _Ref:
        """Recurse to quantify variables."""
        # terminal ?
        if abs(u) == 1:
            return u
        if u in cache:
            return cache[u]
        i, v, w = self._succ[abs(u)]
        if not v:
            raise AssertionError(v)
        if not w:
            raise AssertionError(w)
        # complement ?
        if u < 0:
            v, w = -v, -w
        n = len(ordvar)
        # skip nonessential variables
        while j < n:
            if ordvar[j] < i:
                j += 1
            else:
                break
        else:
            # exhausted valuation
            return u
        # recurse
        p = self._quantify(
            v, j, ordvar,
            qvars, forall,
            cache)
        q = self._quantify(
            w, j, ordvar,
            qvars, forall,
            cache)
        if i in qvars:
            if forall:
                r = self.ite(p, q, -1)
                    # conjoin
            else:
                r = self.ite(p, 1, q)
                    # disjoin
        else:
            r = self.find_or_add(i, p, q)
        cache[u] = r
        return r

    def forall(
            self,
            qvars:
                _abc.Iterable[
                    _VariableName],
            u:
                _Ref
            ) -> _Ref:
        return self.quantify(
            u, qvars,
            forall=True)

    def exist(
            self,
            qvars:
                _abc.Iterable[
                    _VariableName],
            u:
                _Ref
            ) -> _Ref:
        return self.quantify(
            u, qvars,
            forall=False)

    @_try_to_reorder
    def ite(
            self,
            g:
                _Ref,
            u:
                _Ref,
            v:
                _Ref
            ) -> _Ref:
        # wrap so reordering can
        # delete unused nodes
        return self._ite(g, u, v)

    def _ite(
            self,
            g:
                _Ref,
            u:
                _Ref,
            v:
                _Ref
            ) -> _Ref:
        """Recurse to compute ternary conditional."""
        # is g terminal ?
        if g == 1:
            return u
        elif g == -1:
            return v
        # g is non-terminal
        # already computed ?
        r = (g, u, v)
        w = self._ite_table.get(r)
        if w is not None:
            return w
        z = min(self._succ[abs(g)][0],
                self._succ[abs(u)][0],
                self._succ[abs(v)][0])
        g0, g1 = self._top_cofactor(g, z)
        u0, u1 = self._top_cofactor(u, z)
        v0, v1 = self._top_cofactor(v, z)
        p = self._ite(g0, u0, v0)
        q = self._ite(g1, u1, v1)
        w = self.find_or_add(z, p, q)
        # cache
        self._ite_table[r] = w
        return w

    def find_or_add(
            self,
            i:
                _Level,
            v:
                _Ref,
            w:
                _Ref
            ) -> _Ref:
        """Return reference to specified node.

        The returned node is at level `i`
        with successors `v, w`.

        If such a node exists already,
        then it is quickly found in the cached table,
        and the reference returned.

        @param i:
            level in `range(n_vars - 1)`
        @param v:
            low edge
        @param w:
            high edge
        """
        _request_reordering(self)
        if i < 0:
            raise ValueError(
                f'The given level: {i = } < 0')
        if i >= len(self.vars):
            raise ValueError(
                f'The given level: {i = } is not < of '
                'the number of '
                f'declared variables ({len(self.vars)}) '
                '(the set of levels is expected to '
                'comprise of contiguous numbers)')
        if abs(v) not in self._succ:
            raise ValueError(
                f'argument: {v = } is not '
                'a reference to an existing BDD node')
        if abs(w) not in self._succ:
            raise ValueError(
                f'argument: {w = } is not '
                'a reference to an existing BDD node')
        # ensure canonicity of complemented edges
        if w < 0:
            v, w = -v, -w
            r = -1
        else:
            r = 1
        # eliminate
        if v == w:
            return r * v
        # already exists ?
        t = (i, v, w)
        u = self._pred.get(t)
        if u is not None:
            return r * u
        # find a free integer
        u = self._min_free
        if u <= 1:
            raise AssertionError(
                f'min free index is {u}, '
                'which is <= 1')
        if u in self._succ:
            raise AssertionError(
                f'node index {u} '
                'is already used. '
                f'{self._succ = }')
        # add node
        self._pred[t] = u
        self._succ[u] = t
        self._ref[u] = 0
        self._min_free = self._next_free_int(u)
        # increment reference counters
        self.incref(v)
        self.incref(w)
        return r * u

    def _next_free_int(
            self,
            start:
                _Nat
            ) -> _Nat:
        """Return smallest unused integer `> start`."""
        if start < 1:
            raise ValueError(
                f'{start} = start < 1')
        for i in range(start, self.max_nodes):
            if i not in self._succ:
                return i
        raise RuntimeError(
            'full: reached `self.max_nodes` nodes '
            f'({self.max_nodes = }).')

    def collect_garbage(
            self,
            roots:
                _abc.Iterable[_Ref] |
                None=None
            ) -> None:
        """Recursively remove unused nodes

        A node is unused when
        its reference count is zero.

        Removal starts from the nodes in `roots` with zero
        reference count. If no `roots` are given, then
        all nodes are scanned for zero reference counts.
        """
        n = len(self)
        if roots is None:
            roots = self._ref
        def is_unused(
                u
                ) -> _Yes:
            return not self._ref[abs(u)]
        unused = filter(
            is_unused, roots)
        unused = set(map(
            abs, unused))
        # keep terminal
        #
        # Filtering above implies 1 is kept,
        # except within `__del__()`.
        # There `roots` happens to be `None`.
        if 1 in unused:
            unused.remove(1)
        while unused:
            u = unused.pop()
            if u == 1:
                raise AssertionError(u)
            # remove
            i, v, w = self._succ.pop(u)
            if not v:
                raise AssertionError(v)
            if not w:
                raise AssertionError(w)
            u_ = self._pred.pop((i, v, w))
            uref = self._ref.pop(u)
            self._min_free = min(u, self._min_free)
            if u != u_:
                raise AssertionError((u, u_))
            if uref:
                raise AssertionError(uref)
            if self._min_free <= 1:
                raise AssertionError(self._min_free)
            # decrement reference counters
            self.decref(v)
            self.decref(w)
            # unused ?
            if not self._ref[abs(v)] and abs(v) != 1:
                unused.add(abs(v))
            if not self._ref[w] and w != 1:
                unused.add(w)
        self._ite_table = dict()
        m = len(self)
        k = n - m
        if k < 0:
            raise AssertionError((n, m))

    def update_predecessors(
            self
            ) -> None:
        """Update table `self._pred`.

        `self._pred` maps triplets
        `(level, low, high)` to nodes.
        """
        for u, t in self._succ.items():
            if abs(u) == 1:
                continue
            self._pred[t] = u

    def swap(
            self,
            x:
                _VariableName |
                _Level,
            y:
                _VariableName |
                _Level,
            all_levels:
                dict[
                    _Level,
                    set[_Ref]] |
                None=None
            ) -> tuple[
                _Nat,
                _Nat]:
        """Permute adjacent variables `x` and `y`.

        Swapping invokes the garbage collector,
        so be sure to `incref` nodes that should remain.

        @param x, y:
            variable name or level
        """
        if all_levels is None:
            self.collect_garbage()
            all_levels = self._levels()
        logger.debug(
            f'swap variables "{x}" and "{y}"')
        if x in self.vars:
            x = self.vars[x]
        if y in self.vars:
            y = self.vars[y]
        match x:
            case int():
                pass
            case _:
                raise ValueError(x)
        match y:
            case int():
                pass
            case _:
                raise ValueError(y)
        if not (0 <= x < len(self.vars)):
            raise ValueError(x)
        if not (0 <= y < len(self.vars)):
            raise ValueError(y)
        # ensure x < y
        if x > y:
            x, y = y, x
        if x >= y:
            raise ValueError(
                (x, y))
        if abs(x - y) != 1:
            raise ValueError(
                (x, y))
        # count nodes
        oldsize = len(self._succ)
        # collect levels x and y
        levels: dict[
                _Ref,
                dict[_Ref, tuple]
            ] = {
                x: dict(),
                y: dict()}
        for j in (x, y):
            for u in all_levels[j]:
                i, v, w = self._succ[abs(u)]
                if i != j:
                    raise AssertionError(
                        (i, x, y))
                u_ = self._pred.pop(
                    (i, v, w))
                if u != u_:
                    raise AssertionError(
                        (u, u_))
                levels[j][u] = (v, w)
        # move level y up
        for u, (v, w) in levels[y].items():
            i, _, _ = self._succ[u]
            if i != y:
                raise AssertionError((i, y))
            r = (x, v, w)
            self._succ[u] = r
            if r in self._pred:
                raise AssertionError(r)
            self._pred[r] = u
        # move level x down
        # first x nodes independent of y
        done = set()
        for u, (v, w) in levels[x].items():
            i, _, _ = self._succ[u]
            if i != x:
                raise AssertionError((i, x))
            if not v:
                raise AssertionError(v)
            if not w:
                raise AssertionError(w)
            iv, v0, v1 = self._low_high(v)
            iw, w0, w1 = self._low_high(w)
            # dependeds on y ?
            if iv <= y or iw <= y:
                continue
            # independent of y
            r = (y, v, w)
            self._succ[u] = r
            if r in self._pred:
                raise AssertionError(r)
            self._pred[r] = u
            done.add(u)
        # x nodes dependent on y
        garbage = set()
        xfresh = set()
        for u, (v, w) in levels[x].items():
            # for type checking
            match u:
                case int():
                    pass
                case _:
                    raise AssertionError(u)
            if u in done:
                continue
            i, _, _ = self._succ[u]
            if i != x:
                raise AssertionError((i, x))
            if not v:
                raise AssertionError(v)
            if not w:
                raise AssertionError(w)
            self.decref(v)
            self.decref(w)
            # possibly unused
            garbage.add(abs(v))
            garbage.add(w)
            # calling cofactor can fail
            # because y moved
            iv, v0, v1 = self._swap_cofactor(v, y)
            iw, w0, w1 = self._swap_cofactor(w, y)
            # x node depends on y
            if not (y <= iv and y <= iw):
                raise AssertionError(
                    (iv, iw, y))
            if not (y == iv or y == iw):
                raise AssertionError(
                    (iv, iw, y))
            # complemented edge ?
            if v < 0 and y == iv:
                v0, v1 = -v0, -v1
            p = self.find_or_add(
                y, v0, w0)
            q = self.find_or_add(
                y, v1, w1)
            if q < 0:
                raise AssertionError(q)
            if p == q:
                raise AssertionError(
                    'No elimination: '
                    'node depends on both x and y')
            if self._succ[abs(p)][0] == y:
                xfresh.add(abs(p))
            if self._succ[q][0] == y:
                xfresh.add(q)
            r = (x, p, q)
            self._succ[u] = r
            if r in self._pred:
                raise AssertionError(
                    (u, r, levels, self._pred))
            self._pred[r] = u
            self.incref(p)
            self.incref(q)
            # garbage collection could be interleaved
            # but only if there is
            # substantial loss of efficiency
        # swap x and y in `vars`
        vx = self.var_at_level(x)
        self.vars[vx] = y
        vy = self.var_at_level(y)
        self.vars[vy] = x
        # reset
        self._level_to_var[y] = vx
        self._level_to_var[x] = vy
        self._ite_table = dict()
        # count nodes
        self.collect_garbage(garbage)
        newsize = len(self._succ)
        # new levels
        newx = set()
        newy = set()
        for u in levels[x]:
            if u not in self._succ:
                continue
            i, _, _ = self._succ[u]
            if i == x:
                newy.add(u)
            elif i == y:
                newx.add(u)
            else:
                raise AssertionError(
                    (u, i, x, y))
        for u in xfresh:
            i, _, _ = self._succ[u]
            if i != y:
                raise AssertionError(
                    (u, i, x, y))
            newx.add(u)
        for u in levels[y]:
            if u not in self._succ:
                continue
            i, _, _ = self._succ[u]
            if i != x:
                raise AssertionError(
                    (u, i, x, y))
            newy.add(u)
        all_levels[x] = newy
        all_levels[y] = newx
        return (
            oldsize,
            newsize)

    def _low_high(
            self,
            u:
                _Ref
            ) -> tuple[
                _Level,
                _Ref,
                _Node]:
        """Return level, low, and high.

        If node `u` is a leaf,
        then `u` is returned as low and high.

        This method is similar to the
        method `succ`, but different.

        @return:
            (level, low, high)
        """
        i, v, w = self._succ[abs(u)]
        if abs(u) == 1:
            return i, u, u
        if not v:
            raise AssertionError(v)
        if not w:
            raise AssertionError(w)
        return i, v, w

    def _swap_cofactor(
            self,
            u:
                _Ref,
            y:
                _Level
            ) -> tuple[
                _Level,
                _Ref,
                _Ref]:
        """Return cofactor of node `u` wrt level `y`.

        If node `u` is above level `y`, that means
        it was at level `y` when the swap started.
        To account for this,
        `y` is returned as the node level.
        """
        i, v, w = self._succ[abs(u)]
        if y < i:
            return (i, u, u)
        # restore index of y node that
        # moved up
        if not v:
            raise AssertionError(v)
        if not w:
            raise AssertionError(w)
        return (y, v, w)

    def count(
            self,
            u:
                _Ref,
            nvars:
                _Nat |
                None=None
            ) -> _Nat:
        n = nvars
        if abs(u) not in self:
            raise ValueError(u)
        # index those levels in
        # support separately
        levels = {
            self.level_of_var(var)
            for var in self.support(u)}
        k = len(levels)
        if n is None:
            n = k
        slack = n - k
        if slack < 0:
            raise ValueError(slack)
        map_level = dict()
        for new, old in enumerate(sorted(levels)):
            map_level[old] = new + slack
        old, _, _ = self._succ[1]
        map_level[old] = n
        map_level['all'] = n
        r = self._sat_len(
            u, map_level,
            d=dict())
        i, _, _ = self._succ[abs(u)]
        i = map_level[i]
        n_models = r * 2**i
        return self._assert_int(n_models)

    @staticmethod
    def _assert_int(
            number:
                _ty.Any
            ) -> int:
        """Return `number` if an `int`.

        Raise `AssertionError` otherwise.
        """
        match number:
            case int():
                return number
        raise AssertionError(
            'Expected `int` result, '
            f'but: {number = }')

    def _sat_len(
            self,
            u:
                _Ref,
            map_level:
                dict[
                    _Level |
                    _ty.Literal['all'],
                    _Level],
            d:
                dict[
                    _Node,
                    _Nat]
            ) -> _Nat:
        """Recurse to compute the number of models."""
        # terminal ?
        if u == 1:
            return 1
        if u == -1:
            return 0
        i, v, w = self._succ[abs(u)]
        if not v:
            raise AssertionError(v)
        if not w:
            raise AssertionError(w)
        i = map_level[i]
        # memoized ?
        if abs(u) in d:
            n = d[abs(u)]
            # complement ?
            if u < 0:
                n = 2**(map_level['all'] - i) - n
            return self._assert_int(n)
        # non-terminal
        nv = self._sat_len(v, map_level, d)
        nw = self._sat_len(w, map_level, d)
        iv, _, _ = self._succ[abs(v)]
        iw, _, _ = self._succ[w]
        iv = map_level[iv]
        iw = map_level[iw]
        # sum
        n = self._assert_int(
            nv * 2**(iv - i - 1) +
            nw * 2**(iw - i - 1))
        d[abs(u)] = n
        # complement ?
        if u < 0:
            n = 2**(map_level['all'] - i) - n
        return self._assert_int(n)

    def pick_iter(
            self,
            u:
                _Ref,
            care_vars:
                set[_VariableName] |
                None=None
            ) -> _abc.Iterable[
                _Assignment]:
        # empty ?
        if not self._succ:
            return
        # non-empty
        if abs(u) not in self._succ:
            raise ValueError(
                f'{u} is not a reference to '
                'a BDD node in the BDD manager '
                f'`self` ({self!r})')
        support = self.support(u)
        if care_vars is None:
            care_vars = support
        missing = {
            v
            for v in support
            if v not in care_vars}
        if missing:
            logger.warning(
                'Missing bits:  '
                f'support - care_vars = {missing}')
        cube = dict()
        value = True
        cubes = self._sat_iter(
            u, cube, value)
        for cube in cubes:
            minterms = _enumerate_minterms(
                cube, care_vars)
            for m in minterms:
                yield m

    def _sat_iter(
            self,
            u:
                _Ref,
            cube:
                dict[
                    _Level,
                    bool],
            value:
                bool
            ) -> _abc.Iterable[
                _Assignment]:
        """Recurse to enumerate models."""
        if u < 0:
            value = not value
        # terminal ?
        if abs(u) == 1:
            if value:
                cube = {
                    self._level_to_var[i]: v
                    for i, v in cube.items()}
                yield cube
            return
        # non-terminal
        i, v, w = self._succ[abs(u)]
        if not v:
            raise AssertionError(v)
        if not w:
            raise AssertionError(w)
        d0 = dict(cube)
        d0[i] = False
        d1 = dict(cube)
        d1[i] = True
        for x in self._sat_iter(v, d0, value):
            yield x
        for x in self._sat_iter(w, d1, value):
            yield x

    def assert_consistent(
            self
            ) -> None:
        """Raise `AssertionError` if not a valid BDD."""
        for root in self.roots:
            if abs(root) not in self._succ:
                raise AssertionError(root)
        # inverses
        succ_keys = set(self._succ)
        succ_values = set(self._succ.values())
        pred_keys = set(self._pred)
        pred_values = set(self._pred.values())
        if succ_keys != pred_values:
            raise AssertionError(
                succ_keys.symmetric_difference(
                    pred_values))
        if pred_keys != succ_values:
            raise AssertionError(
                pred_keys.symmetric_difference(
                    succ_values))
        # uniqueness
        n = len(succ_keys)
        n_ = len(succ_values)
        if n != n_:
            raise AssertionError(n - n_)
        for u, (i, v, w) in self._succ.items():
            if not isinstance(i, int):
                raise TypeError(i)
            # terminal ?
            if v is None:
                if w is not None:
                    raise AssertionError(w)
                continue
            else:
                if abs(v) not in self._succ:
                    raise AssertionError(v)
            if w is None:
                if v is not None:
                    raise AssertionError(v)
                continue
            else:
                # "high" is regular edge
                if w < 0:
                    raise AssertionError(w)
                if w not in self._succ:
                    raise AssertionError(w)
            # var order should increase
            for x in (v, w):
                ix, _, _ = self._succ[abs(x)]
                if not (i < ix):
                    raise AssertionError((u, i))
            # `_pred` contains inverse of `_succ`
            if (i, v, w) not in self._pred:
                raise AssertionError((i, v, w))
            if self._pred[(i, v, w)] != u:
                raise AssertionError(u)
            # reference count
            if u not in self._ref:
                raise AssertionError(u)
            if self._ref[u] < 0:
                raise AssertionError(self._ref[u])

    @_try_to_reorder
    def add_expr(
            self,
            expr:
                _Formula
            ) -> _Ref:
        return _parser.add_expr(expr, self)

    def to_expr(
            self,
            u:
                _Ref
            ) -> _Formula:
        if u not in self:
            raise ValueError(
                f'{u} is not a reference to '
                'a BDD node in the BDD manager '
                f'`self` ({self!r})')
        cache = dict()
        return self._to_expr(u, cache)

    def _to_expr(
            self,
            u:
                _Ref,
            cache:
                dict[int, str]
            ) -> _Formula:
        if u == 1:
            return 'TRUE'
        if u == -1:
            return 'FALSE'
        if u in cache:
            return cache[u]
        level, v, w = self._succ[abs(u)]
        if not v:
            raise AssertionError(v)
        if not w:
            raise AssertionError(w)
        var = self._level_to_var[level]
        p = self._to_expr(v, cache)
        q = self._to_expr(w, cache)
        # pure var ?
        if p == 'FALSE' and q == 'TRUE':
            expr = var
        else:
            expr = f'ite({var}, {q}, {p})'
        # complemented ?
        if u < 0:
            expr = f'(~ {expr})'
        cache[u] = expr
        return expr

    def apply(
            self,
            op:
                dd._abc.OperatorSymbol,
            u:
                _Ref,
            v:
                _Ref |
                None=None,
            w:
                _Ref |
                None=None
            ) -> _Ref:
        _utils.assert_operator_arity(op, v, w, 'bdd')
        if abs(u) not in self:
            raise ValueError(u)
        if v is not None and abs(v) not in self:
            raise ValueError(v)
        if w is not None and abs(w) not in self:
            raise ValueError(w)
        # unary
        if op in ('~', 'not', '!'):
            return -u
        # Implied by `assert_operator_arity()` above,
        # present here for type-checking.
        elif v is None:
            raise ValueError(
                '`v is None`')
        # binary
        elif op in ('or', r'\/', '|', '||'):
            return self.ite(u, 1, v)
        elif op in ('and', '/\\', '&', '&&'):
            return self.ite(u, v, -1)
        elif op in ('#', 'xor', '^'):
            return self.ite(u, -v, v)
        elif op in ('=>', '->', 'implies'):
            return self.ite(u, v, 1)
        elif op in ('<=>', '<->', 'equiv'):
            return self.ite(u, v, -v)
        elif op in ('diff', '-'):
            return self.ite(u, -v, -1)
        elif op in (r'\A', 'forall'):
            qvars = self.support(u)
            return self.quantify(
                v, qvars,
                forall=True)
        elif op in (r'\E', 'exists'):
            qvars = self.support(u)
            return self.quantify(
                v, qvars,
                forall=False)
        # Implied by `assert_operator_arity()` above,
        # present here for type-checking.
        elif w is None:
            raise ValueError(
                '`w is None`')
        # ternary
        elif op == 'ite':
            return self.ite(u, v, w)
        raise ValueError(
            f'unknown operator "{op}"')

    def _add_int(
            self,
            i:
                int
            ) -> _Ref:
        if i not in self:
            raise ValueError(
                f'{i = } is not a reference '
                'to a BDD node in the BDD manager '
                f'`self` ({self!r})')
        return i

    @_try_to_reorder
    def cube(
            self,
            dvars:
                _Assignment |
                _abc.Iterable[
                    _VariableName]
            ) -> _Ref:
        if not isinstance(dvars, dict):
            dvars = {
                k: True
                for k in dvars}
        # `dvars` keys can be var names or levels
        r = self.true
        for var, val in dvars.items():
            u = self.var(var)
            u = u if val else -u
            r = self.apply('and', u, r)
        return r

    def dump(
            self,
            filename:
                str,
            roots:
                dict[str, _Ref] |
                list[_Ref] |
                None=None,
             filetype:
                dd._abc.ImageFileType |
                dd._abc.PickleFileType |
                None=None,
            **kw
            ) -> None:
        if filetype is None:
            name = filename.lower()
            if name.endswith('.pdf'):
                filetype = 'pdf'
            elif name.endswith('.png'):
                filetype = 'png'
            elif name.endswith('.svg'):
                filetype = 'svg'
            elif name.endswith('.dot'):
                filetype = 'dot'
            elif name.endswith('.p'):
                filetype = 'pickle'
            else:
                raise ValueError(
                    'cannot infer file type '
                    'from extension of file '
                    f'name "{filename}"')
        if filetype in _utils.DOT_FILE_TYPES:
            self._dump_figure(
                roots, filename,
                filetype, **kw)
        elif filetype == 'pickle':
            self._dump_bdd(roots, filename, **kw)
        else:
            raise ValueError(
                f'unknown file type "{filetype}"')

    def _dump_figure(
            self,
            roots:
                _abc.Iterable[_Ref] |
                None,
            filename:
                str,
            filetype:
                dd._abc.ImageFileType,
            **kw
            ) -> None:
        """Write BDDs to `filename` as figure."""
        g = _to_dot(roots, self)
        g.dump(filename, filetype=filetype, **kw)

    def _dump_bdd(
            self,
            roots:
                dict[str, _Ref] |
                list[_Ref] |
                None,
            filename:
                str,
            **kw
            ) -> None:
        """Write BDDs to `filename` as pickle."""
        if roots is None:
            nodes = self._succ
            roots = list()
        else:
            values = _utils.values_of(roots)
            nodes = self.descendants(values)
        succ = (
            (k, self._succ[k])
            for k in nodes)
        d = dict(
            vars=self.vars,
            succ=dict(succ),
            roots=roots)
        kw.setdefault('protocol', 2)
        with open(filename, 'wb') as f:
            pickle.dump(d, f, **kw)

    def load(
            self,
            filename:
                str,
            levels:
                _Yes=True
            ) -> (
                dict[str, _Ref] |
                list[_Ref]):
        name = filename.lower()
        if not name.endswith('.p'):
            raise ValueError(
                f'Unknown file type of "{filename}"')
        umap, roots = self._load_pickle(
            filename, levels=levels)
        def map_node(u):
            v = umap[abs(u)]
            if u < 0:
                return - v
            else:
                return v
        return _utils.map_container(
            map_node, roots)

    def _load_pickle(
            self,
            filename:
                str,
            levels:
                _Yes=True
            ) -> tuple[
                dict,
                dict[str, _Ref] |
                list[_Ref]]:
        with open(filename, 'rb') as f:
            d = pickle.load(f)
        var2level = d['vars']
        succ = d['succ']
        n = len(var2level)
        level_map = dict()
        # level_map[n] = len(self.vars)
        for var, i in var2level.items():
            if not (0 <= i < n):
                raise AssertionError((i, n))
            if var not in self.vars:
                logger.warning(
                    f'variable "{var}" added')
            if levels:
                j = self.add_var(var, i)
            else:
                j = self.add_var(var)
            level_map[i] = j
        umap = dict()
        for u in succ:
            # already added ?
            if u in umap:
                continue
            # add
            self._load(
                u, succ, umap, level_map)
        return umap, d['roots']

    def _load(
            self,
            u:
                _Ref,
            succ:
                dict,
            umap:
                dict,
            level_map:
                dict
            ) -> _Ref:
        """Recurse to load BDD `u` from `succ`."""
        # terminal ?
        if abs(u) == 1:
            return u
        # memoized ?
        if u in umap:
            r = umap[abs(u)]
            if r <= 0:
                raise AssertionError(r)
            if u < 0:
                r = -r
            return r
        i, v, w = succ[abs(u)]
        j = level_map[i]
        p = self._load(
            v, succ, umap, level_map)
        q = self._load(
            w, succ, umap, level_map)
        r = self.find_or_add(j, p, q)
        if r <= 0:
            raise AssertionError(r)
        umap[abs(u)] = r
        if u < 0:
            r = -r
        return r

    def _dump_manager(
            self,
            filename:
                str,
            **kw
            ) -> None:
        """Write `BDD` to `filename` as pickle."""
        d = dict(
            vars=self.vars,
            max_nodes=self.max_nodes,
            roots=self.roots,
            pred=self._pred,
            succ=self._succ,
            ref=self._ref,
            min_free=self._min_free)
        kw.setdefault('protocol', 2)
        with open(filename, 'wb') as f:
            pickle.dump(d, f, **kw)

    @classmethod
    def _load_manager(
            cls,
            filename:
                str
            ) -> 'BDD':
        """Load `BDD` from pickle file `filename`."""
        with open(filename, 'rb') as f:
            d = pickle.load(f)
        bdd = cls(d['vars'])
        bdd.max_nodes = d['max_nodes']
        bdd.roots = d['roots']
        bdd._pred = d['pred']
        bdd._succ = d['succ']
        bdd._ref = d['ref']
        bdd._min_free = d['min_free']
        return bdd

    @property
    def false(
            self
            ) -> _Ref:
        return -1

    @property
    def true(
            self
            ) -> _Ref:
        return 1


def _enumerate_minterms(
        cube:
            _Assignment,
        bits:
            _abc.Iterable[
                _VariableName]
        ) -> _abc.Iterator[
            _Assignment]:
    """Generator of complete assignments in `cube`.

    @param bits:
        enumerate over those absent from `cube`
    """
    if cube is None:
        raise ValueError(cube)
    if bits is None:
        raise ValueError(bits)
    bits = set(bits).difference(cube)
    # fix order
    bits = list(bits)
    n = len(bits)
    for i in range(2**n):
        values = bin(i).lstrip('-0b').zfill(n)
        model = {
            k: bool(int(v))
            for k, v in
                zip(bits, values)}
        model.update(cube)
        if len(model) < len(bits):
            raise AssertionError((model, bits))
        if len(model) < len(cube):
            raise AssertionError((model, cube))
        yield model


def _assert_isomorphic_orders(
        old:
            _VariableLevels,
        new:
            _VariableLevels,
        support:
            set[_VariableName]
        ) -> None:
    """Raise `AssertionError` if not isomorphic.

    @param old, new:
        levels
    @param support:
        `old` and `new` compared after
        restriction to `support`.
    """
    _assert_valid_ordering(old)
    _assert_valid_ordering(new)
    s = {
        k: v
        for k, v in
            old.items()
        if k in support}
    t = {
        k: v
        for k, v in
            new.items()
        if k in support}
    old = sorted(s, key=s.get)
    new = sorted(t, key=t.get)
    if old != new:
        raise AssertionError((old, new))


def _assert_valid_ordering(
        levels:
            _VariableLevels
        ) -> None:
    """Check that `levels` is well-formed.

    - bijection
    - contiguous levels
    """
    # `levels` is a mapping from
    # each variable to a single level
    if not isinstance(levels, _abc.Mapping):
        raise TypeError(levels)
    # levels are contiguous integers ?
    n = len(levels)
    numbers = set(levels.values())
    numbers_ = set(range(n))
    if numbers != numbers_:
        raise AssertionError(n, numbers)


def rename(
        u:
            _Ref,
        bdd:
            BDD,
        dvars:
            _Renaming
        ) -> _Ref:
    """Rename variables of node `u`.

    @param dvars:
        `dict` from variabe names to variable names
    """
    if abs(u) not in bdd:
        raise ValueError(
            f'{u} (given as `u`) is not a reference to '
            'a BDD node in the given BDD manager '
            f'`bdd` ({bdd!r})')
    # nothing to rename ?
    if not dvars:
        return u
    # map variable names to levels
    levels = bdd.vars
    dvars = {
        levels[var]: levels[dvars.get(var, var)]
        for var in bdd.vars}
    cache = dict()
    return _copy_bdd(u, dvars, bdd, bdd, cache)


def _assert_valid_rename(
        u:
            _Ref,
        bdd:
            BDD,
        dvars:
            dict[
                _Level,
                _Level]
        ) -> None:
    """Assert renaming to only adjacent variables.

    Raise `AssertionError` if
    renaming to non-adjacent variables.

    @param dvars:
        `dict` that maps var levels to var levels
    """
    if not dvars:
        return
    # valid levels ?
    bdd.var_at_level(0)
    # pairwise disjoint ?
    _assert_no_overlap(dvars)


def _all_adjacent(
        dvars:
            dict,
        bdd:
            BDD
        ) -> _Yes:
    """Return `True` if all levels are adjacent.

    The pairs of levels checked for
    being adjacent are the key-value pairs
    of the mapping `dvars`.
    """
    for v, vp in dvars.items():
        if not _adjacent(v, vp, bdd):
            return False
    return True


def _adjacent(
        i:
            _Level,
        j:
            _Level,
        bdd:
            BDD
        ) -> _Yes:
    """Warn if levels `i` and `j` not adjacent."""
    if abs(i - j) == 1:
        return True
    logger.warning((
        'level {i} ("{x}") not adjacent to '
        'level {j} ("{y}")').format(
            i=i,
            j=j,
            x=bdd.var_at_level(i),
            y=bdd.var_at_level(j)))
    return False


def _assert_no_overlap(
        d:
            dict
        ) -> None:
    """Raise `AssertionError` if keys and values overlap."""
    if any((k in d) for k in d.values()):
        raise AssertionError(
            f'keys and values overlap: {d}')


def image(
        trans:
            _Ref,
        source:
            _Ref,
        rename:
            _Renaming |
            dict[_Level, _Level],
        qvars:
            _abc.Iterable[_VariableName] |
            _abc.Iterable[_Level],
        bdd:
            BDD,
        forall:
            _Yes=False
        ) -> _Ref:
    """Return set reachable from `source` under `trans`.

    @param trans:
        transition relation
    @param source:
        the transition must start in this set
    @param rename:
        maps primed variables in
        `trans` to unprimed variables in `trans`.
        Applied to the quantified conjunction of
        `trans` and `source`.
    @param qvars:
        variables to quantify
    @param forall:
        if `True`,
        then quantify `qvars` universally,
        else existentially.
    """
    # map to levels
    qvars = bdd._map_to_level(set(qvars))
    rename = {
        bdd.vars.get(k, k): bdd.vars.get(v, v)
        for k, v in rename.items()}
    # init
    cache = dict()
    rename_u = rename
    rename_v = None
    # no overlap and neighbors
    _assert_no_overlap(rename)
    if not _all_adjacent(rename, bdd):
        logger.warning(
            'BDD.image: not all vars adjacent')
    # unpriming maps to qvars or
    # outside support of conjunction
    s = bdd.support(trans, as_levels=True)
    s.update(bdd.support(source, as_levels=True))
    s.difference_update(qvars)
    s.intersection_update(rename.values())
    if s:
        raise AssertionError(s)
    return _image(
        trans, source, rename_u, rename_v,
        qvars, bdd, forall, cache)


def preimage(
        trans:
            _Ref,
        target:
            _Ref,
        rename:
            _Renaming |
            dict[_Level, _Level],
        qvars:
            _abc.Iterable[_VariableName] |
            _abc.Iterable[_Level],
        bdd:
            BDD,
        forall:
            _Yes=False
        ) -> _Ref:
    """Return set that can reach `target` under `trans`.

    Also known as the "relational product".
    Assumes that primed and
    unprimed variables are neighbors.
    Variables are identified by their levels.

    @param trans:
        transition relation
    @param target:
        the transition must end in this set
    @param rename:
        maps (unprimed) variables in `target` to
        (primed) variables in `trans`
    @param qvars:
        variables to quantify
    @param forall:
        if `True`,
        then quantify `qvars` universally,
        else existentially.
    """
    # map to levels
    qvars = bdd._map_to_level(set(qvars))
    rename = {
        bdd.vars.get(k, k): bdd.vars.get(v, v)
        for k, v in rename.items()}
    # init
    cache = dict()
    rename_u = None
    rename_v = rename
    # check
    _assert_valid_rename(target, bdd, rename)
    return _image(
        trans, target, rename_u, rename_v,
        qvars, bdd, forall, cache)


def _image(
        u:
            _Ref,
        v:
            _Ref,
        umap:
            dict |
            None,
        vmap:
            dict |
            None,
        qvars:
            set[_Level],
        bdd:
            BDD,
        forall:
            _Yes,
        cache:
            dict[
                tuple[_Ref, _Ref],
                _Ref]
        ) -> _Ref:
    """Recursive (pre)image computation.

    Renaming requires that in each pair
    the variables are adjacent.

    @param umap:
        renaming of variables in `u`
        that occurs after conjunction of `u` with `v`
        and quantification.
    @param vmap:
        renaming of variables in `v`
        that occurs before conjunction with `u`.
    """
    # controlling values for conjunction ?
    if u == -1 or v == -1:
        return -1
    if u == 1 and v == 1:
        return 1
    # already computed ?
    t = (u, v)
    w = cache.get(t)
    if w is not None:
        return w
    # recurse (descend)
    iu, _, _ = bdd._succ[abs(u)]
    jv, _, _ = bdd._succ[abs(v)]
    if vmap is None:
        iv = jv
    else:
        iv = vmap.get(jv, jv)
    z = min(iu, iv)
    u0, u1 = bdd._top_cofactor(u, z)
    v0, v1 = bdd._top_cofactor(v, jv + z - iv)
    p = _image(
        u0, v0, umap, vmap, qvars,
        bdd, forall, cache)
    q = _image(
        u1, v1, umap, vmap, qvars,
        bdd, forall, cache)
    # quantified ?
    if z in qvars:
        if forall:
            r = bdd.ite(p, q, -1)
                # conjoin
        else:
            r = bdd.ite(p, 1, q)
                # disjoin
    else:
        if umap is None:
            m = z
        else:
            m = umap.get(z, z)
        g = bdd.find_or_add(m, -1, 1)
        r = bdd.ite(g, q, p)
    cache[t] = r
    return r


def reorder(
        bdd:
            BDD,
        order:
            _VariableLevels |
            None=None
        ) -> None:
    """Apply Rudell's sifting algorithm to reduce `bdd` size.

    Reordering invokes the garbage collector,
    so be sure to `incref` nodes that should remain.

    @param order:
        if given, then swap vars to obtain this order.
        The dictionary `order` maps each
        variable name to a level.
    """
    len_before = len(bdd)
    if order is None:
        _apply_sifting(bdd)
    else:
        _sort_to_order(bdd, order)
    len_after = len(bdd)
    logger.info(
        'Reordering changed `BDD` manager size '
        f'from {len_before} to {len_after} nodes.')


def _apply_sifting(
        bdd:
            BDD
        ) -> None:
    """Apply Rudell's sifting algorithm."""
    bdd.collect_garbage()
    n = len(bdd)
    # using `set` injects some randomness
    levels = bdd._levels()
    names = set(bdd.vars)
    for var in names:
        k = _reorder_var(bdd, var, levels)
        m = len(bdd)
        logger.info(
            f'{m} nodes for variable '
            f'"{var}" at level {k}')
    if m > n:
        raise AssertionError(
            f'expected: m <= n, but {m = } > {n = }')
    logger.info(f'final variable order:\n{bdd.vars}')


def _reorder_var(
        bdd:
            BDD,
        var:
            _VariableName,
        levels:
            dict[
                _Level,
                set[_Ref]]
        ) -> _Nat:
    """Reorder by sifting a variable `var`."""
    if var not in bdd.vars:
        raise ValueError((var, bdd.vars))
    m = len(bdd)
    n = len(bdd.vars) - 1
    if n < 0:
        raise AssertionError(n)
    start = 0
    end = n
    level = bdd.level_of_var(var)
    # closer to bottom ?
    if (2 * level) >= n:
        start, end = end, start
    _shift(bdd, level, start, levels)
    sizes = _shift(bdd, start, end, levels)
    k = min(sizes, key=sizes.get)
    _shift(bdd, end, k, levels)
    m_ = len(bdd)
    if sizes[k] != m_:
        raise AssertionError((sizes[k], m_))
    if m_ > m:
        raise AssertionError((m_, m))
    return k


def _shift(
        bdd:
            BDD,
        start:
            _Level,
        end:
            _Level,
        levels:
            dict[
                _Level,
                set[_Ref]]
        ) -> dict[
            _Level,
            _Level]:
    r"""Shift level `start` to become `end`, by swapping.

    ```tla
    ASSUMPTION
        LET
            n_vars == len(bdd.vars)
            level_range == 0..(n_vars - 1)
        IN
            /\ start \in level_range
            /\ end \in level_range
    ```
    """
    m = len(bdd.vars)
    if not (0 <= start < m):
        raise AssertionError((start, m))
    if not (0 <= end < m):
        raise AssertionError((end, m))
    sizes = dict()
    d = 1 if start < end else -1
    for i in range(start, end, d):
        j = i + d
        oldn, n = bdd.swap(i, j, levels)
        sizes[i] = oldn
        sizes[j] = n
    return sizes


def _sort_to_order(
        bdd:
            BDD,
        order:
            _VariableLevels
        ) -> None:
    """Swap variables to obtain `order`."""
    # TODO: use min number of swaps
    if len(bdd.vars) != len(order):
        raise ValueError(
            'The number of BDD variables: '
            f'{len(bdd.vars) = } is not equal to: '
            f'{len(order) = }')
    m = 0
    levels = bdd._levels()
    n = len(order)
    for k in range(n):
        for i in range(n - 1):
            for root in bdd.roots:
                if root not in bdd:
                    raise ValueError(
                        f'{root} in `bdd.roots` is not '
                        'a reference to a BDD node in '
                        'the given BDD manager `bdd` '
                        f'({bdd!r})')
            x = bdd.var_at_level(i)
            y = bdd.var_at_level(i + 1)
            p = order[x]
            q = order[y]
            if p > q:
                bdd.swap(i, i + 1, levels)
                m += 1
                logger.debug(
                    f'swap: {p} with {q}, {i}')
            if logger.getEffectiveLevel() < logging.DEBUG:
                bdd.assert_consistent()
    logger.info(f'total swaps: {m}')


def reorder_to_pairs(
        bdd:
            BDD,
        pairs:
            _Renaming
        ) -> None:
    """Reorder variables to make adjacent the given pairs.

    @param pairs:
        has variable names as keys and values
    """
    m = 0
    levels = bdd._levels()
    for x, y in pairs.items():
        jx = bdd.level_of_var(x)
        jy = bdd.level_of_var(y)
        k = abs(jx - jy)
        if k <= 0:
            raise AssertionError((jx, jy))
        # already adjacent ?
        if k == 1:
            continue
        # shift x next to y
        if jx > jy:
            jx, jy = jy, jx
        _shift(bdd, start=jx, end=jy - 1, levels=levels)
        m += k
        logger.debug(f'shift by {k}')
    logger.info(f'total swaps: {m}')


def copy_bdd(
        u:
            _Ref,
        from_bdd:
            BDD,
        to_bdd:
            BDD
        ) -> _Ref:
    """Copy BDD of node `u` `from_bdd` `to_bdd`.

    @param u:
        node in `from_bdd`
    """
    if from_bdd is to_bdd:
        logger.warning(
            'copying node to same BDD manager')
        return u
    level_map = {
        from_bdd.level_of_var(var):
            to_bdd.level_of_var(var)
        for var in from_bdd.vars
        if var in to_bdd.vars}
    r = _copy_bdd(
        u, level_map,
        from_bdd, to_bdd,
        cache=dict())
    return r


def _copy_bdd(
        u:
            _Ref,
        level_map:
            dict[_Level, _Level],
        old_bdd:
            BDD,
        bdd:
            BDD,
        cache:
            dict[_Node, _Ref]
        ) -> _Ref:
    """Recurse to copy nodes from `old_bdd` to `bdd`.

    @param u:
        node in `old_bdd`
    @param level_map:
        maps old to new levels
    """
    # terminal ?
    if abs(u) == 1:
        return u
    # non-terminal
    # memoized ?
    r = cache.get(abs(u))
    if r is not None:
        if r <= 0:
            raise AssertionError(r)
        # complement ?
        if u < 0:
            r = -r
        return r
    # recurse
    jold, v, w = old_bdd._succ[abs(u)]
    if not v:
        raise AssertionError(v)
    if not w:
        raise AssertionError(w)
    p = _copy_bdd(
        v, level_map,
        old_bdd, bdd,
        cache)
    q = _copy_bdd(
        w, level_map,
        old_bdd, bdd,
        cache)
    if p * v <= 0:
        raise AssertionError((p, v))
    if q <= 0:
        raise AssertionError(q)
    # map this level
    jnew = level_map[jold]
    g = bdd.find_or_add(jnew, -1, 1)
    r = bdd.ite(g, q, p)
    # memoize
    if r <= 0:
        raise AssertionError(r)
    cache[abs(u)] = r
    # complement ?
    if u < 0:
        r = -r
    return r


def _flip(
        r:
            _Ref,
        u:
            _Ref
        ) -> _Ref:
    """Flip `r` if `u` is negated, else identity."""
    return -r if u < 0 else r


def to_nx(
        bdd:
            BDD,
        roots:
            set[_Ref]
        ) -> '_utils.MultiDiGraph':
    """Convert node references in `roots` to graph.

    The resulting graph has:

      - nodes labeled with:
        - `level`:
          `int` from 0 to `len(bdd)`
      - edges labeled with:
        - `value`:
          `False` for low/"else",
          `True` for high/"then"
        - `complement`:
          `True` if target node is negated

    @param roots:
        iterable of edges, each a signed `int`
    """
    _nx = _utils.import_module('networkx')
    g = _nx.MultiDiGraph()
    for root in roots:
        if abs(root) not in bdd:
            raise ValueError(root)
        Q = {root}
        while Q:
            u = Q.pop()
            u = abs(u)
            i, v, w = bdd._succ[u]
            if u <= 0:
                raise AssertionError(u)
            g.add_node(u, level=i)
            # terminal ?
            if v is None or w is None:
                if v is not None:
                    raise AssertionError(v)
                if w is not None:
                    raise AssertionError(w)
                continue
            # non-terminal
            r = (v < 0)
            v = abs(v)
            w = abs(w)
            if v not in g:
                Q.add(v)
            if w not in g:
                Q.add(w)
            if v <= 0:
                raise AssertionError(v)
            if w <= 0:
                raise AssertionError(w)
            g.add_edge(
                u, v,
                value=False,
                complement=r)
            g.add_edge(
                u, w,
                value=True,
                complement=False)
    return g


def _to_dot(
        roots:
            _abc.Iterable[_Ref] |
            None,
        bdd:
            BDD
        ) -> _utils.DotGraph:
    """Convert `BDD` to DOT graph.

    Nodes are ordered by variable levels in support.
    Edges to low successors are dashed.
    Complemented edges are labeled with "-1".

    Nodes not reachable from `roots`
    are ignored, unless `roots is None`.

    The roots are plotted as external references,
    with complemented edges where applicable.
    """
    # all nodes ?
    if roots is None:
        nodes = bdd._succ
        roots = list()
    else:
        nodes = bdd.descendants(roots)
    # show only levels in aggregate support
    levels = {
        bdd._succ[abs(u)][0]
        for u in nodes}
    if bdd._succ[1][0] not in levels:
        raise AssertionError(
            'level of node 1 is missing from computed '
            'set of BDD nodes reachable from `roots`')
    g = _utils.DotGraph(
        graph_type='digraph')
    skeleton = list()
    subgraphs = dict()
    # layer for external BDD references
    layers = [-1] + sorted(levels)
    # add nodes for BDD levels
    for i in layers:
        h = _utils.DotGraph(
            rank='same')
        g.subgraphs.append(h)
        subgraphs[i] = h
        # add phantom node
        u = f'"L{i}"'
        skeleton.append(u)
        if i == -1:
            # layer for external BDD references
            label = 'ref'
        else:
            # BDD level
            label = str(i)
        h.add_node(
            u,
            label=label,
            shape='none')
    # auxiliary edges for ranking
    for i, u in enumerate(skeleton[:-1]):
        v = skeleton[i + 1]
        g.add_edge(
            u, v,
            style='invis')
    # add nodes
    idx2var = {
        k: v
        for v, k in bdd.vars.items()}
    # BDD nodes
    def f(x):
        return str(abs(x))
    for u in nodes:
        i, v, w = bdd._succ[abs(u)]
        # terminal ?
        if v is None:
            var = str(bool(abs(u)))
        else:
            var = idx2var[i]
        su = f(u)
        label = f'{var}-{su}'
        # add node to subgraph for level i
        h = subgraphs[i]
        h.add_node(
            su,
            label=label)
        # add edges
        if v is None:
            continue
        sv = f(v)
        sw = f(w)
        kw = dict(style='dashed')
        if v < 0:
            kw['taillabel'] = '-1'
        g.add_edge(
            su, sv,
            **kw)
        g.add_edge(
            su, sw,
            style='solid')
    # external references to BDD nodes
    for u in roots:
        i, _, _ = bdd._succ[abs(u)]
        su = f'"ref{u}"'
        label = f'@{u}'
        # add node to subgraph for level -1
        h = subgraphs[-1]
        h.add_node(
            su,
            label=label)
        # add edge from external reference to BDD node
        if u is None:
            raise ValueError(f'{u} in `roots`')
        sv = str(abs(u))
        kw = dict(style='dashed')
        if u < 0:
            kw.update(taillabel='-1')
        g.add_edge(
            su, sv,
            **kw)
    return g
