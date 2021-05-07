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


class BDD(object):
    """Shared reduced ordered binary decision diagram."""

    def __init__(self, levels=None):
        # subclasses are not supposed to call `super().__init__()`
        self.vars = dict()  # overridden

    def __eq__(self, other):
        """Return `True` if `other` has same manager"""

    def __len__(self):
        """Return number of nodes."""

    def __contains__(self, u):
        """Return `True` """

    def __str__(self):
        return 'Specification of BDD class.'

    def configure(self, **kw):
        """Read and apply parameter values."""

    def statistics(self):
        """Return `dict` with BDD manager statistics."""
        # default implementation that offers no info
        return dict()

    def succ(self, u):
        """Return `(level, low, high)` for node `u`.

        The manager uses complemented edges,
        so `low` and `high` correspond to the rectified `u`.
        """

    def declare(self, *variables):
        """Add names in `variables` to `self.vars`.

        ```python
        bdd.declare('x', 'y', 'z')
        ```
        """
        for var in variables:
            self.add_var(var)

    def var(self, var):
        """Return node for variable named `var`."""

    def var_at_level(self, level):
        """Return variable with `level`."""

    def level_of_var(self, var):
        """Return level of `var`, or `None`."""

    @property
    def var_levels(self):
        """Return `dict` that maps variables to levels."""

    def copy(self, u, other):
        """Copy operator `u` from `self` to `other` manager."""

    def support(self, u, as_levels=False):
        """Return `set` of variables that node `u` depends on.

        @param as_levels: if `True`, then return variables
            as integers, insted of strings
        """

    def let(self, definitions, u):
        """Substitute `definitions` for variables in `u`.

        @param definitions: `dict` that maps some variable
            names to Boolean values, or other variable names,
            or BDD nodes. All values should be of same type.
        """

    def forall(self, variables, u):
        """Quantify `variables` in `u` universally."""

    def exist(self, variables, u):
        """Quantify `variables` in `u` existentially."""

    def count(self, u, nvars=None):
        """Return number of models of node `u`.

        @param n: number of variables to assume.

            If omitted, then assume those in `support(u)`.
            The levels of variables outside support
            are ignored in counting, and `n` used to
            increase the result at the end of recursion.
        """

    def pick(self, u, care_vars=None):
        r"""Return a single assignment as `dict`.

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
        return next(self.pick_iter(u, care_vars), None)

    def pick_iter(self, u, care_vars=None):
        """Return generator over assignments.

        By default, `care_vars = support(u)`.
        Log a warning if `care_vars < support(u)`.

        @param care_vars: cases:

            1. `None`: return (uniform) assignments that
               include exactly those variables in `support(u)`

            2. `set`: return (possibly partial) assignments
               that include at least all bits in `set`

        @rtype: generator of `dict(str: bool)`
        """

    # def to_bdd(self, expr):
    #     raise NotImplementedError('use `add_expr`')

    def add_expr(self, expr):
        """Return node for expression `e`, after adding it.

        If you would like to use your own parser,
        you can use utilities from `dd._parser`.

        @type expr: `str`
        """

    def to_expr(self, u):
        """Return a Boolean expression for node `u`."""

    def ite(self, g, u, v):
        """Ternary conditional `IF g THEN u ELSE v`.

        @param g: condition
        @param u: high
        @param v: low
        @type g, u, v: nodes
        @rtype: node
        """

    def apply(self, op, u, v=None, w=None):
        r"""Apply operator `op` to nodes `u` and `v`.

        @type op: `str` in:
          - `'not', '~', '!'`
          - `'and', '/\\', '&', '&&'`
          - `'or', r'\/', '|', '||'`
          - `'xor', '#', '^'`
          - `'=>', '->', 'implies'`
          - `'<=>', '<->', 'equiv'`
          - `'diff', '-'`
          - `r'\A', 'forall'`
          - `r'\E', 'exists'`
          - `'ite'`
        @type u, v, w: nodes
        """

    def _add_int(self, i):
        """Return node from integer `i`."""

    def cube(self, dvars):
        """Return node for conjunction of literals in `dvars`.

        @param dvars: `dict` that maps each variable to a `bool`
        """

    # TODO: homogeneize i/o API with `dd.cudd`
    def dump(
            self, filename, roots=None,
            filetype=None, **kw):
        """Write BDDs to `filename`.

        The file type is inferred from the
        extension (case insensitive),
        unless a `filetype` is explicitly given.

        `filetype` can have the values:

          - `'p'` for Pickle
          - `'pdf'` for PDF
          - `'png'` for PNG
          - `'svg'` for SVG

        If `filetype is None`, then `filename`
        must have an extension that matches
        one of the file types listed above.

        Dump nodes reachable from `roots`.
        If `roots is None`,
        then all nodes in the manager are dumped.

        @type filename: `str`
        @type filetype: `str`, e.g., `"pdf"`
        @type roots: container of nodes
        """

    # revise this method to return roots as `list` or
    # named nodes as `dict`
    def load(self, filename, levels=True):
        """Load nodes from Pickle file `filename`.

        If `levels is True`,
        then load variables at the same levels.
        Otherwise, add missing variables.

        @type filename: `str`
        @return: map from dumped to loaded nodes
        @rtype: `dict`
        """

    @property
    def false(self):
        """Return Boolean constant false."""

    @property
    def true(self):
        """Return Boolean constant true."""


def reorder(bdd, order=None):
    """Apply Rudell's sifting algorithm to `bdd`.

    @param order: reorder to this specific order,
        if `None` then invoke group sifting
    @type order: `dict: str -> int` that maps
        variable names to levels
    """


class Operator(object):
    """Convenience wrapper for edges returned by `BDD`."""

    def __init__(self, node, bdd):
        assert node in bdd._bdd, node
        self.bdd = bdd
        self.manager = bdd._bdd
        self.node = node
        self.manager.incref(node)

    def __hash__(self):
        return self.node

    def to_expr(self):
        """Return Boolean expression of function as `str`."""

    def __int__(self):
        """Return integer ID of node.

        To invert this method call `BDD._add_int`.
        """

    def __str__(self):
        """Return string form of node as `@INT`.

        "INT" is an integer that depends on
        the implementation. For example "@54".
        The integer value is `int(self)`.

        The integer value is recognized by the method
        `BDD._add_int` of the same manager that the
        node belongs to.
        """
        return '@' + str(int(self))

    def __len__(self):
        """Number of nodes reachable from this node."""

    def __del__(self):
        r"""Dereference node in manager."""

    def __eq__(self, other):
        r"""`|= self \equiv other`."""

    def __ne__(self, other):
        r"""`~ |= self \equiv other`."""

    def __lt__(self, other):
        r"""`(|= self => other) /\ ~ |= self \equiv other`."""

    def __le__(self, other):
        """`|= self => other`."""

    def __invert__(self):
        """Negation `~ self`."""

    def __and__(self, other):
        r"""Conjunction `self /\ other`."""

    def __or__(self, other):
        r"""Disjunction `self \/ other`."""

    def implies(self, other):
        """Logical implication `self => other`."""

    def equiv(self, other):
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
    def level(self):
        """Level where this node currently is."""

    @property
    def var(self):
        """Variable at level where this node is."""

    @property
    def low(self):
        """Return "else" node."""

    @property
    def high(self):
        """Return "then" node."""

    @property
    def ref(self):
        """Sum of reference counts of node and its negation."""

    @property
    def negated(self):
        """Return `True` if `self` is a complemented edge."""

    @property
    def support(self):
        """Return `set` of variables in support."""

    def let(self, **definitions):
        return self.bdd.let(definitions, self)

    def exist(self, *variables):
        return self.bdd.exist(variables, self)

    def forall(self, *variables):
        return self.bdd.forall(variables, self)

    def pick(self, care_vars=None):
        return self.bdd.pick(self, care_vars)

    def count(self, nvars=None):
        return self.bdd.count(self, nvars)
