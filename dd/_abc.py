"""Interface specification.

This specification is implemented by the modules:

- `dd.autoref`
- `dd.cudd`
- `dd.cudd_zdd`
- `dd.sylvan` (partially)
- `dd.buddy` (partially)
"""
# Copyright 2017 by California Institute of Technology
# All rights reserved. Licensed under BSD-3.
#
import collections.abc as _abc
import typing as _ty


def _literals_of(
        type_alias:
            type
        ) -> set[str]:
    """Return arguments of `type_alias`.

    Recursive computation.
    Assumes `str` literals.
    """
    return set(_literals_of_recurse(type_alias))


def _literals_of_recurse(
        type_alias:
            type
        ) -> _abc.Iterable[str]:
    """Yield literals of `type_alias`."""
    args = _ty.get_args(type_alias)
    literals = set()
    for arg in args:
        match arg:
            case str():
                yield arg
            case _:
                yield from _literals_of_recurse(arg)
    return literals


Yes: _ty.TypeAlias = bool
Nat: _ty.TypeAlias = int
    # ```tla
    # Nat
    # ```
Cardinality: _ty.TypeAlias = Nat
NumberOfBytes: _ty.TypeAlias = Cardinality
VariableName: _ty.TypeAlias = str
Level: _ty.TypeAlias = Nat
VariableLevels: _ty.TypeAlias = dict[
    VariableName,
    Level]
Ref = _ty.TypeVar('Ref')
Assignment: _ty.TypeAlias = dict[
    VariableName,
    bool]
Renaming: _ty.TypeAlias = dict[
    VariableName,
    VariableName]
Fork: _ty.TypeAlias = tuple[
    Level,
    Ref | None,
    Ref | None]
Formula: _ty.TypeAlias = str
_UnaryOperatorSymbol: _ty.TypeAlias = _ty.Literal[
    # negation
    'not',
    '~',
    '!']
UNARY_OPERATOR_SYMBOLS: _ty.Final = _literals_of(
    _UnaryOperatorSymbol)
# These assertions guard against typos in
# the enumerations.
if len(UNARY_OPERATOR_SYMBOLS) != 3:
    raise AssertionError(UNARY_OPERATOR_SYMBOLS)
_BinaryOperatorSymbol: _ty.TypeAlias = _ty.Literal[
    # conjunction
    'and',
    '/\\',
    '&',
    '&&',
    # disjunction
    'or',
    r'\/',
    '|',
    '||',
    # different
    '#',
    'xor',
    '^',
    # implication
    '=>',
    '->',
    'implies',
    # equivalence
    '<=>',
    '<->',
    'equiv',
    # subtraction (i.e., `a /\ ~ b`)
    'diff',
    '-',
    # quantification
    r'\A',
    'forall',
    r'\E',
    'exists']
BINARY_OPERATOR_SYMBOLS: _ty.Final = _literals_of(
    _BinaryOperatorSymbol)
if len(BINARY_OPERATOR_SYMBOLS) != 23:
    raise AssertionError(BINARY_OPERATOR_SYMBOLS)
_TernaryOperatorSymbol: _ty.TypeAlias = _ty.Literal[
    # ternary conditional
    # (if-then-else)
    'ite']
TERNARY_OPERATOR_SYMBOLS: _ty.Final = _literals_of(
    _TernaryOperatorSymbol)
if len(TERNARY_OPERATOR_SYMBOLS) != 1:
    raise AssertionError(TERNARY_OPERATOR_SYMBOLS)
BDD_OPERATOR_SYMBOLS: _ty.Final = {
    *UNARY_OPERATOR_SYMBOLS,
    *BINARY_OPERATOR_SYMBOLS,
    *TERNARY_OPERATOR_SYMBOLS}
if len(BDD_OPERATOR_SYMBOLS) != 3 + 23 + 1:
    raise AssertionError(BDD_OPERATOR_SYMBOLS)
_AgdUnaryOperatorSymbol: _ty.TypeAlias = (
    _UnaryOperatorSymbol |
    _ty.Literal['log'])
ADD_UNARY_OPERATOR_SYMBOLS: _ty.Final = _literals_of(
    _AgdUnaryOperatorSymbol)
if len(ADD_UNARY_OPERATOR_SYMBOLS) != 3 + 1:
    raise AssertionError(ADD_UNARY_OPERATOR_SYMBOLS)
_AgdBinaryOperatorSymbol: _ty.TypeAlias = (
    _BinaryOperatorSymbol |
    _ty.Literal[
        '+',
        '*',
        '/',
        'nand'])
ADD_BINARY_OPERATOR_SYMBOLS: _ty.Final = _literals_of(
    _AgdBinaryOperatorSymbol)
if len(ADD_BINARY_OPERATOR_SYMBOLS) != 23 + 4:
    # `'-' in BINARY_OPERATOR_SYMBOLS`
    raise AssertionError(ADD_BINARY_OPERATOR_SYMBOLS)
ADD_TERNARY_OPERATOR_SYMBOLS: _ty.Final = {
    *TERNARY_OPERATOR_SYMBOLS}
if len(ADD_TERNARY_OPERATOR_SYMBOLS) != 1:
    raise AssertionError(ADD_TERNARY_OPERATOR_SYMBOLS)
ADD_OPERATOR_SYMBOLS: _ty.Final = {
    *ADD_UNARY_OPERATOR_SYMBOLS,
    *ADD_BINARY_OPERATOR_SYMBOLS,
    *ADD_TERNARY_OPERATOR_SYMBOLS}
if len(ADD_OPERATOR_SYMBOLS) != 4 + 27 + 1:
    raise AssertionError(ADD_OPERATOR_SYMBOLS)
OperatorSymbol: _ty.TypeAlias = (
    _UnaryOperatorSymbol |
    _BinaryOperatorSymbol |
    _TernaryOperatorSymbol)
AgdOperatorSymbol: _ty.TypeAlias = (
    _AgdUnaryOperatorSymbol |
    _AgdBinaryOperatorSymbol |
    _TernaryOperatorSymbol)
ImageFileType: _ty.TypeAlias = _ty.Literal[
    'pdf',
    'png',
    'svg']
JSONFileType: _ty.TypeAlias = _ty.Literal[
    'json']
PickleFileType: _ty.TypeAlias = _ty.Literal[
    'pickle']
BDDFileType: _ty.TypeAlias = (
    ImageFileType |
    JSONFileType)


class BDD(_ty.Protocol[Ref]):
    """Shared reduced ordered binary decision diagram."""

    vars: VariableLevels

    def __init__(
            self,
            levels:
                dict |
                None=None
            ) -> None:
        ...

    def __eq__(
            self,
            other
            ) -> Yes:
        """Return `True` if `other` has same manager"""

    def __len__(
            self
            ) -> Cardinality:
        """Return number of nodes."""

    def __contains__(
            self,
            u:
                Ref
            ) -> Yes:
        """Return `True` """

    def __str__(
            self
            ) -> str:
        return 'Specification of BDD class.'

    def configure(
            self,
            **kw
            ) -> dict[
                str,
                _ty.Any]:
        """Read and apply parameter values."""

    def statistics(
            self
            ) -> dict[
                str,
                _ty.Any]:
        """Return BDD manager statistics."""
        # default implementation that offers no info
        return dict()

    def succ(
            self,
            u:
                Ref
            ) -> Fork:
        """Return `(level, low, high)` for node `u`.

        The manager uses complemented edges,
        so `low` and `high` correspond to the rectified `u`.
        """

    def declare(
            self,
            *variables:
                VariableName
            ) -> None:
        """Add names in `variables` to `self.vars`.

        ```python
        bdd.declare('x', 'y', 'z')
        ```
        """

    def var(
            self,
            var:
                VariableName
            ) -> Ref:
        """Return node for variable named `var`."""

    def var_at_level(
            self,
            level:
                Level
            ) -> VariableName:
        """Return variable with `level`."""

    def level_of_var(
            self,
            var:
                VariableName
            ) -> (
                Level |
                None):
        """Return level of `var`, or `None`."""

    @property
    def var_levels(
            self
            ) -> VariableLevels:
        """Return mapping from variables to levels."""

    def copy(
            self,
            u:
                Ref,
            other:
                'BDD'
            ) -> Ref:
        """Copy operator `u` from `self` to `other` manager."""

    def support(
            self,
            u:
                Ref,
            as_levels:
                Yes=False
            ) -> (
                set[VariableName] |
                set[Level]):
        """Return variables that node `u` depends on.

        @param as_levels:
            if `True`, then return variables
            as integers, insted of strings
        """

    def let(
            self,
            definitions:
                dict[VariableName, VariableName] |
                Assignment |
                dict[VariableName, Ref],
            u:
                Ref
            ) -> Ref:
        """Substitute variables in `u`.

        The mapping `definitions` need not have
        all declared variables as keys.
        """

    def forall(
            self,
            variables:
                _abc.Iterable[
                    VariableName],
            u:
                Ref
            ) -> Ref:
        """Quantify `variables` in `u` universally."""

    def exist(
            self,
            variables:
                _abc.Iterable[
                    VariableName],
            u:
                Ref
            ) -> Ref:
        """Quantify `variables` in `u` existentially."""

    def count(
            self,
            u:
                Ref,
            nvars:
                Cardinality |
                None=None
            ) -> Cardinality:
        """Return number of models of node `u`.

        @param n:
            number of variables to assume.

            If omitted, then assume those in `support(u)`.
            The levels of variables outside support
            are ignored in counting, and `n` used to
            increase the result at the end of recursion.
        """

    def pick(
            self,
            u:
                Ref,
            care_vars:
                set[VariableName] |
                None=None
            ) -> (
                Assignment |
                None):
        r"""Return a single assignment.

        An assignment is a `dict` that maps
        each variable to a `bool`. Examples:

        ```python
        >>> u = bdd.add_expr('x')
        >>> bdd.pick(u)
        {'x': True}

        >>> u = bdd.add_expr('y')
        >>> bdd.pick(u)
        {'y': True}

        >>> u = bdd.add_expr('y')
        >>> bdd.pick(u, care_vars=['x', 'y'])
        {'x': False, 'y': True}

        >>> u = bdd.add_expr(r'x \/ y')
        >>> bdd.pick(u)
        {'x': False, 'y': True}

        >>> u = bdd.false
        >>> bdd.pick(u) is None
        True
        ```

        By default, `care_vars = support(u)`.
        Log a warning if `care_vars < support(u)`.

        Thin wrapper around `pick_iter`.
        """
        picks = self.pick_iter(u, care_vars)
        return next(iter(picks), None)

    def pick_iter(
            self,
            u:
                Ref,
            care_vars:
                set[VariableName] |
                None=None
            ) -> _abc.Iterable[
                Assignment]:
        """Return iterator over assignments.

        By default, `care_vars = support(u)`.
        Log a warning if `care_vars < support(u)`.

        CASES:

        1. `None`: return (uniform) assignments that
           include exactly those variables in `support(u)`

        2. `set`: return (possibly partial) assignments
           that include at least all bits in `care_vars`
        """

    # def to_bdd(
    #         self,
    #         expr):
    #     raise NotImplementedError('use `add_expr`')

    def add_expr(
            self,
            expr:
                Formula
            ) -> Ref:
        """Return node for expression `expr`.

        Nodes are created for the BDD that
        represents the expression `expr`.
        """

    def to_expr(
            self,
            u:
                Ref
            ) -> Formula:
        """Return a Boolean expression for node `u`."""

    def ite(
            self,
            g:
                Ref,
            u:
                Ref,
            v:
                Ref
            ) -> Ref:
        """Ternary conditional `IF g THEN u ELSE v`.

        @param g:
            condition
        @param u:
            high
        @param v:
            low
        """

    def apply(
            self,
            op:
                OperatorSymbol,
            u:
                Ref,
            v:
                Ref |
                None=None,
            w:
                Ref |
                None=None
            ) -> Ref:
        r"""Apply operator `op` to nodes `u`, `v`, `w`."""

    def _add_int(
            self,
            i:
                int
            ) -> Ref:
        """Return node from `i`."""

    def cube(
            self,
            dvars:
                Assignment
            ) -> Ref:
        """Return node for conjunction of literals in `dvars`."""

    # TODO: homogeneize i/o API with `dd.cudd`
    def dump(
            self,
            filename:
                str,
            roots:
                dict[str, Ref] |
                list[Ref] |
                None=None,
            filetype:
                ImageFileType |
                None=None,
            **kw
            ) -> None:
        """Write BDDs to `filename`.

        The file type is inferred from the
        extension (case insensitive),
        unless a `filetype` is explicitly given.

        `filetype` can have the values:

          - `'pickle'` for Pickle
          - `'pdf'` for PDF
          - `'png'` for PNG
          - `'svg'` for SVG

        If `filetype is None`, then `filename`
        must have an extension that matches
        one of the file types listed above.

        Dump nodes reachable from `roots`.
        If `roots is None`,
        then all nodes in the manager are dumped.

        @type roots:
            - `list` of nodes, or
            - for Pickle: `dict` that maps
              names to nodes
        """

    def load(
            self,
            filename:
                str,
            levels:
                Yes=True
            ) -> (
                dict[str, Ref] |
                list[Ref]):
        """Load nodes from Pickle file `filename`.

        If `levels is True`,
        then load variables at the same levels.
        Otherwise, add missing variables.

        @return:
            roots of the loaded BDDs
        @rtype:
            depends on the contents of the file,
            either:
            - `dict` that maps names
              to nodes, or
            - `list` of nodes
        """

    @property
    def false(
            self
            ) -> Ref:
        """Return Boolean constant false."""

    @property
    def true(
            self
            ) -> Ref:
        """Return Boolean constant true."""


def reorder(
        bdd:
            BDD,
        order:
            VariableLevels |
            None=None
        ) -> None:
    """Apply Rudell's sifting algorithm to `bdd`.

    @param order:
        reorder to this specific order,
        if `None` then invoke group sifting
    """


class Operator(_ty.Protocol):
    """Convenience wrapper for edges returned by `BDD`."""

    def __init__(
            self,
            node,
            bdd
            ) -> None:
        self.bdd: BDD
        self.manager: object
        self.node: object

    def __hash__(
            self
            ) -> int:
        return self.node

    def to_expr(
            self
            ) -> Formula:
        """Return Boolean expression of function."""

    def __int__(
            self
            ) -> int:
        """Return integer ID of node.

        To invert this method call `BDD._add_int`.
        """

    def __str__(
            self
            ) -> str:
        """Return string form of node as `@INT`.

        "INT" is an integer that depends on
        the implementation. For example "@54".
        The integer value is `int(self)`.

        The integer value is recognized by the method
        `BDD._add_int` of the same manager that the
        node belongs to.
        """
        return f'@{int(self)}'

    def __len__(
            self
            ) -> Cardinality:
        """Number of nodes reachable from this node."""

    def __del__(
            self
            ) -> None:
        r"""Dereference node in manager."""

    def __eq__(
            self,
            other
            ) -> Yes:
        r"""`|= self \equiv other`.

        Return `False` if `other is None`.
        """

    def __ne__(
            self,
            other
            ) -> Yes:
        r"""`~ |= self \equiv other`.

        Return `True` if `other is None`.
        """

    def __lt__(
            self,
            other
            ) -> Yes:
        r"""`(|= self => other) /\ ~ |= self \equiv other`."""

    def __le__(
            self,
            other
            ) -> Yes:
        """`|= self => other`."""

    def __invert__(
            self
            ) -> 'Operator':
        """Negation `~ self`."""

    def __and__(
            self,
            other
            ) -> 'Operator':
        r"""Conjunction `self /\ other`."""

    def __or__(
            self,
            other
            ) -> 'Operator':
        r"""Disjunction `self \/ other`."""

    def implies(
            self,
            other
            ) -> 'Operator':
        """Logical implication `self => other`."""

    def equiv(
            self,
            other
            ) -> 'Operator':
        r"""Logical equivalence `self <=> other`.

        The result is *different* from `__eq__`:

        - Logical equivalence is the Boolean function that is
          `TRUE` for models for which both `self` and `other`
          are `TRUE`, and `FALSE` otherwise.

        - BDD equality (`__eq__`) is the Boolean function
          that results from universal quantification of the
          logical equivalence, over all declared variables.

        In other words:

        "A <=> B" versus "\A x, y, ..., z:  A <=> B"
        or, from a metatheoretic viewpoint:
        "A <=> B" versus "|= A <=> B"

        In the metatheory, [[A <=> B]] (`equiv`) is different from
        [[A]] = [[B]] (`__eq__`).

        Also, `equiv` differs from `__eq__` in that it returns a BDD
        as `Function`, instead of `bool`.
        """

    @property
    def level(
            self
            ) -> Level:
        """Level where this node currently is."""

    @property
    def var(
            self
            ) -> (
                VariableName |
                None):
        """Variable at level where this node is."""

    @property
    def low(
            self
            ) -> '''(
                Operator |
                None
                )''':
        """Return "else" node."""

    @property
    def high(
            self
            ) -> '''(
                Operator |
                None
                )''':
        """Return "then" node."""

    @property
    def ref(
            self
            ) -> Cardinality:
        """Sum of reference counts of node and its negation."""

    @property
    def negated(
            self
            ) -> Yes:
        """Return `True` if `self` is a complemented edge."""

    @property
    def support(
            self
            ) -> set[
                VariableName]:
        """Return variables in support."""

    def let(
            self,
            **definitions: '''(
                VariableName |
                Operator |
                bool
                )'''
            ) -> 'Operator':
        return self.bdd.let(definitions, self)

    def exist(
            self,
            *variables:
                VariableName
            ) -> 'Operator':
        return self.bdd.exist(variables, self)

    def forall(
            self,
            *variables:
                VariableName
            ) -> 'Operator':
        return self.bdd.forall(variables, self)

    def pick(
            self,
            care_vars:
                set[VariableName] |
                None=None
            ) -> (
                Assignment |
                None):
        return self.bdd.pick(self, care_vars)

    def count(
            self,
            nvars:
                Cardinality |
                None=None
            ) -> Cardinality:
        return self.bdd.count(self, nvars)
