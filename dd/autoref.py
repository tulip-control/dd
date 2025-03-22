"""Wraps `dd.bdd` to automate reference counting.

For function docstrings, refer to `dd.bdd`.
"""
# Copyright 2015 by California Institute of Technology
# All rights reserved. Licensed under BSD-3.
#
import collections.abc as _abc
import logging
import typing as _ty
import warnings

import dd._abc
import dd._copy as _copy
import dd._utils as _utils
import dd.bdd as _bdd


log = logging.getLogger(__name__)


_Yes: _ty.TypeAlias = dd._abc.Yes
_Cardinality: _ty.TypeAlias = dd._abc.Cardinality
_VariableName: _ty.TypeAlias = dd._abc.VariableName
_Level: _ty.TypeAlias = dd._abc.Level
_VariableLevels: _ty.TypeAlias = dd._abc.VariableLevels
_Ref: _ty.TypeAlias = _ty.Union['Function']
_MaybeRef: _ty.TypeAlias = '''(
    _Ref |
    None
    )'''
_Fork: _ty.TypeAlias = '''(
    tuple[
        _Level,
        _MaybeRef,
        _MaybeRef]
    )'''
_Assignment: _ty.TypeAlias = dd._abc.Assignment
_Renaming: _ty.TypeAlias = dd._abc.Renaming
_Formula: _ty.TypeAlias = dd._abc.Formula


class BDD(dd._abc.BDD[_Ref]):
    """Shared ordered binary decision diagram.

    It takes and returns `Function` instances,
    which automate reference counting.

    Attributes:

      - `vars`: `dict` mapping `variables` to `int` levels
          Do not assign the `dict` itself.

    For docstrings, refer to methods of `dd.bdd.BDD`,
    with the difference that `Function`s replace nodes
    as arguments and returned types.
    """
    # omitted docstrings are inheritted from `super()`

    def __init__(
            self,
            levels:
                _VariableLevels |
                None=None):
        manager = _bdd.BDD(levels)
        self._bdd = manager
        self.vars: _VariableLevels = manager.vars

    def __eq__(
            self,
            other:
                'BDD'
            ) -> _Yes:
        if not isinstance(other, BDD):
            raise NotImplementedError
        return (self._bdd is other._bdd)

    def __len__(
            self
            ) -> _Cardinality:
        return len(self._bdd)

    def __contains__(
            self,
            u:
                _Ref
            ) -> _Yes:
        if self is not u.bdd:
            raise ValueError('`self is not u.bdd`')
        return u.node in self._bdd

    def __str__(
            self
            ) -> str:
        return (
            'Binary decision diagram (`dd.bdd.BDD` wrapper):\n'
            '------------------------\n'
            f'\t {len(self.vars)} BDD variables\n'
            f'\t {len(self)} nodes\n')

    def _wrap(
            self,
            u:
                int
            ) -> _Ref:
        """Return reference to node `u`.

        References can be thought of also
        as edges.

        @param u:
            node in `self._bdd`
        """
        if u not in self._bdd:
            raise ValueError(u)
        return Function(u, self)

    def configure(
            self,
            **kw
            ) -> dict[
                str,
                _ty.Any]:
        return self._bdd.configure(**kw)

    def succ(
            self,
            u
            ) -> _Fork:
        i, v, w = self._bdd.succ(u.node)
        def wrap(
                node:
                    int |
                    None
                ) -> _MaybeRef:
            match node:
                case None:
                    return None
                case int():
                    return self._wrap(node)
            raise AssertionError(node)
        return i, wrap(v), wrap(w)

    def incref(
            self,
            u:
                _Ref
            ) -> None:
        self._bdd.incref(u.node)

    def decref(
            self,
            u:
                _Ref,
            **kw
            ) -> None:
        self._bdd.decref(u.node)

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
        return self._bdd.add_var(var, level=level)

    def var(
            self,
            var:
                _VariableName
            ) -> _Ref:
        r = self._bdd.var(var)
        return self._wrap(r)

    def var_at_level(
            self,
            level:
                _Level
            ) -> _VariableName:
        return self._bdd.var_at_level(level)

    def level_of_var(
            self,
            var:
                _VariableName
            ) -> _Level:
        return self._bdd.level_of_var(var)

    @property
    def var_levels(
            self
            ) -> _VariableLevels:
        return self._bdd.var_levels

    def reorder(
            self,
            var_order:
                _VariableLevels |
                None=None
            ) -> None:
        reorder(self, var_order)

    def copy(
            self,
            u:
                _Ref,
            other:
                'BDD'
            ) -> _Ref:
        if u not in self:
            raise ValueError(u)
        if self is other:
            log.warning('copying node to same manager')
            return u
        r = self._bdd.copy(u.node, other._bdd)
        return other._wrap(r)

    def support(
            self,
            u:
                _Ref,
            as_levels:
                _Yes=False
            ) -> set[_VariableName]:
        if u not in self:
            raise ValueError(u)
        return self._bdd.support(u.node, as_levels)

    def let(
            self,
            definitions:
                _Renaming |
                _Assignment |
                dict[_VariableName, _Ref],
            u:
                _Ref
            ) -> _Ref:
        if u not in self:
            raise ValueError(u)
        if not definitions:
            return u
        var = next(iter(definitions))
        value = definitions[var]
        match value:
            case str() | bool():
                d = definitions
            case Function():
                def node_of(
                        ref
                        ) -> int:
                    if isinstance(ref, Function):
                        return ref.node
                    raise ValueError(
                        'Expected homogeneous type '
                        'for `dict` values.')
                d = {
                    var: node_of(value)
                    for var, value in
                        definitions.items()}
            case _:
                raise TypeError(value)
        r = self._bdd.let(d, u.node)
        return self._wrap(r)

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
        if u not in self:
            raise ValueError(u)
        r = self._bdd.quantify(u.node, qvars, forall)
        return self._wrap(r)

    def forall(
            self,
            qvars:
                _abc.Iterable[_VariableName],
            u:
                _Ref
            ) -> _Ref:
        return self.quantify(u, qvars, forall=True)

    def exist(
            self,
            qvars:
                _abc.Iterable[
                    _VariableName],
            u:
                _Ref
            ) -> _Ref:
        return self.quantify(u, qvars, forall=False)

    def ite(
            self,
            g:
                _Ref,
            u:
                _Ref,
            v:
                _Ref
            ) -> _Ref:
        if g not in self:
            raise ValueError(g)
        if u not in self:
            raise ValueError(u)
        if v not in self:
            raise ValueError(v)
        r = self._bdd.ite(g.node, u.node, v.node)
        return self._wrap(r)

    def find_or_add(
            self,
            var:
                _VariableName,
            low:
                _Ref,
            high:
                _Ref
            ) -> _Ref:
        """Return node `IF var THEN high ELSE low`."""
        level = self.level_of_var(var)
        r = self._bdd.find_or_add(level, low.node, high.node)
        return self._wrap(r)

    def count(
            self,
            u:
                _Ref,
            nvars:
                _Cardinality |
                None=None
            ) -> _Cardinality:
        if u not in self:
            raise ValueError(u)
        return self._bdd.count(u.node, nvars)

    def pick_iter(
            self,
            u:
                _Ref,
            care_vars:
                set[_VariableName] |
                None=None
            ) -> _abc.Iterable[
                _Assignment]:
        if u not in self:
            raise ValueError(u)
        return self._bdd.pick_iter(u.node, care_vars)

    def add_expr(
            self,
            e:
                _Formula
            ) -> _Ref:
        r = self._bdd.add_expr(e)
        return self._wrap(r)

    def to_expr(
            self,
            u:
                _Ref
            ) -> _Formula:
        if u not in self:
            raise ValueError(u)
        return self._bdd.to_expr(u.node)

    def apply(
            self,
            op:
                dd._abc.OperatorSymbol,
            u:
                _Ref,
            v:
                _MaybeRef
                =None,
            w:
                _MaybeRef
                =None
            ) -> _Ref:
        if u not in self:
            raise ValueError(u)
        if v is None and w is not None:
            raise ValueError(w)
        if v is not None and v not in self:
            raise ValueError(v)
        if w is not None and w not in self:
            raise ValueError(w)
        if v is None:
            r = self._bdd.apply(op, u.node)
        elif w is None:
            r = self._bdd.apply(op, u.node, v.node)
        else:
            r = self._bdd.apply(op, u.node, v.node, w.node)
        return self._wrap(r)

    def _add_int(
            self,
            i:
                int
            ) -> _Ref:
        r = self._bdd._add_int(i)
        return self._wrap(r)

    def cube(
            self,
            dvars:
                _Assignment
            ) -> _Ref:
        r = self._bdd.cube(dvars)
        return self._wrap(r)

    def collect_garbage(
            self
            ) -> None:
        """Recursively remove nodes with zero reference count."""
        self._bdd.collect_garbage()

    def dump(
            self,
            filename:
                str,
            roots:
                dict[str, _Ref] |
                list[_Ref] |
                None=None,
            filetype:
                dd._abc.BDDFileType |
                dd._abc.PickleFileType |
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
          - `'json'` for JSON

        If `filetype is None`, then `filename`
        must have an extension that matches
        one of the file types listed above.

        Dump nodes reachable from `roots`.
        If `roots is None`,
        then all nodes in the manager are dumped.

        Dumping a JSON file requires that `roots`
        be nonempty.

        @type roots:
            - `list` of nodes, or
            - for JSON or Pickle:
              `dict` that maps names
              to nodes
        """
        # The method's docstring is a slight modification
        # of the docstring of the method `dd._abc.BDD.dump`.
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
            elif name.endswith('.json'):
                filetype = 'json'
            else:
                raise ValueError(
                    'cannot infer file type '
                    'from extension of file '
                    f'name "{filename}"')
        if filetype == 'json':
            if roots is None:
                raise ValueError(roots)
            _copy.dump_json(roots, filename)
            return
        elif (filetype != 'pickle' and
                filetype not in _utils.DOT_FILE_TYPES):
            raise ValueError(filetype)
        if roots is not None:
            def mapper(u):
                return u.node
            roots = _utils.map_container(
                mapper, roots)
        self._bdd.dump(
            filename,
            roots=roots,
            filetype=filetype)

    def load(
            self,
            filename:
                str,
            levels:
                _Yes=True
            ) -> (
                dict[str, _Ref] |
                list[_Ref]):
        """Load nodes from Pickle or JSON file `filename`.

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
        # This method's docstring is a slight
        # modification of the docstring of
        # the method `dd._abc.BDD.dump`.
        name = filename.lower()
        if name.endswith('.p'):
            return self._load_pickle(
                filename, levels=levels)
        elif name.endswith('.json'):
            nodes = _copy.load_json(filename, self)
            def check(
                    node
                    ) -> Function:
                if isinstance(node, Function):
                    return node
                raise AssertionError(node)
            match nodes:
                case dict():
                    return {
                        k: check(v)
                        for k, v in nodes.items()}
                case list():
                    return list(map(check, nodes))
                case _:
                    raise AssertionError(nodes)
        else:
            raise ValueError(
                f'Unknown file type of "{filename}"')

    def _load_pickle(
            self,
            filename:
                str,
            levels:
                _Yes=True
            ) -> (
                dict[str, _Ref] |
                list[_Ref]):
        roots = self._bdd.load(filename, levels=levels)
        return _utils.map_container(self._wrap, roots)

    def assert_consistent(
            self
            ) -> None:
        self._bdd.assert_consistent()

    @property
    def false(
            self
            ) -> _Ref:
        u = self._bdd.false
        return self._wrap(u)

    @property
    def true(
            self
            ) ->_Ref:
        u = self._bdd.true
        return self._wrap(u)


def image(
        trans:
            _Ref,
        source:
            _Ref,
        rename:
            _Renaming,
        qvars:
            set[_VariableName],
        forall:
            _Yes=False
        ) -> _Ref:
    if trans.bdd is not source.bdd:
        raise ValueError(
            (trans.bdd, source.bdd))
    u = _bdd.image(
        trans.node, source.node, rename,
        qvars, trans.manager, forall)
    return trans.bdd._wrap(u)


def preimage(
        trans:
            _Ref,
        target:
            _Ref,
        rename:
            _Renaming,
        qvars:
            set[_VariableName],
        forall:
            _Yes=False
        ) -> _Ref:
    if trans.bdd is not target.bdd:
        raise ValueError(
            (trans.bdd, target.bdd))
    u = _bdd.preimage(
        trans.node, target.node, rename,
        qvars, trans.manager, forall)
    return trans.bdd._wrap(u)


def reorder(
        bdd:
            BDD,
        order:
            _VariableLevels |
            None=None
        ) -> None:
    """Apply Rudell's sifting algorithm to `bdd`."""
    _bdd.reorder(bdd._bdd, order=order)


def copy_vars(
        source:
            BDD,
        target:
            BDD
        ) -> None:
    _copy.copy_vars(source._bdd, target._bdd)


def copy_bdd(
        u:
            _Ref,
        target:
            BDD
        ) -> _Ref:
    r = _bdd.copy_bdd(u.node, u.manager, target._bdd)
    return target._wrap(r)


class Function(dd._abc.Operator):
    r"""Convenience wrapper for edges returned by `BDD`.

    ```python
    import dd.autoref

    bdd = dd.autoref.BDD()
    bdd.declare('x', 'y')
    nd = bdd._bdd.add_expr(r'x /\ y')
        # `nd` is an integer
        # `bdd._bdd` is an instance of the
        # class `dd.bdd.BDD`
    u = _bdd.Function(nd, bdd)
    ```

    Attributes:

    - `node`: `int` that describes edge (signed node)
    - `bdd`: `dd.autoref.BDD` instance that node belongs to
    - `manager`: `dd.bdd.BDD` instance that node belongs to

    Operations are valid only between functions with
    the same `BDD` in `Function.bdd`.

    After all references to a `Function` have been deleted,
    the reference count of its associated node is decremented.
    To explicitly release a `Function` instance, invoke `del f`.

    The design here is inspired by the PyEDA package.
    """

    def __init__(
            self,
            node:
                int,
            bdd:
                BDD
            ) -> None:
        if node not in bdd._bdd:
            raise ValueError(node)
        self.bdd = bdd
        self.manager = bdd._bdd
        self.node = node
        self.manager.incref(node)

    def __hash__(
            self
            ) -> int:
        return self.node

    def to_expr(
            self
            ) -> _Formula:
        """Return Boolean expression of function."""
        return self.manager.to_expr(self.node)

    def __int__(
            self
            ) -> int:
        return self.node

    def __len__(
            self
            ) -> _Cardinality:
        return len(self.manager.descendants([self.node]))

    @property
    def dag_size(
            self
            ) -> _Cardinality:
        return len(self)

    def __del__(
            self
            ) -> None:
        """Decrement reference count of `self.node` in `self.bdd`."""
        if self.node is None:
            return
        node = self.node
        self.node = None
        self.manager.decref(node)

    def __eq__(
            self,
            other
            ) -> _Yes:
        if other is None:
            return False
        if not isinstance(other, Function):
            raise NotImplementedError
        if self.bdd is not other.bdd:
            raise ValueError((self.bdd, other.bdd))
        return self.node == other.node

    def __ne__(
            self,
            other
            ) -> _Yes:
        if other is None:
            return True
        if not isinstance(other, Function):
            raise NotImplementedError
        if self.bdd is not other.bdd:
            raise ValueError((self.bdd, other.bdd))
        return not (self == other)

    def __le__(
            self,
            other
            ) -> _Yes:
        if not isinstance(other, Function):
            raise NotImplementedError
        return (other | ~ self) == self.bdd.true

    def __lt__(
            self,
            other
            ) -> _Yes:
        if not isinstance(other, Function):
            raise NotImplementedError
        return self <= other and self != other

    def __invert__(
            self
            ) -> _Ref:
        return self._apply('not', other=None)

    def __and__(
            self,
            other:
                _Ref
            ) -> _Ref:
        return self._apply('and', other)

    def __or__(
            self,
            other:
                _Ref
            ) -> _Ref:
        return self._apply('or', other)

    def __xor__(
            self,
            other:
                _Ref
            ) -> _Ref:
        return self._apply('xor', other)
                
    def implies(
            self,
            other:
                _Ref
            ) -> _Ref:
        return self._apply('implies', other)

    def equiv(
            self,
            other:
                _Ref
            ) -> _Ref:
        return self._apply('equiv', other)

    def _apply(
            self,
            op:
                dd._abc.OperatorSymbol,
            other:
                _MaybeRef
            ) -> _Ref:
        """Return result of operation `op` with `other`."""
        # unary op ?
        if other is None:
            u = self.manager.apply(op, self.node)
        else:
            if self.bdd is not other.bdd:
                raise ValueError((self.bdd, other.bdd))
            u = self.manager.apply(op, self.node, other.node)
        return Function(u, self.bdd)

    @property
    def level(
            self
            ) -> _Level:
        i, _, _ = self.manager._succ[abs(self.node)]
        return i

    @property
    def var(
            self
            ) -> (
                _VariableName |
                None):
        i, low, _ = self.manager._succ[abs(self.node)]
        if low is None:
            return None
        return self.manager.var_at_level(i)

    @property
    def low(
            self
            ) -> '''(
                _Ref |
                None
                )''':
        _, v, _ = self.manager._succ[abs(self.node)]
        if v is None:
            return None
        return Function(v, self.bdd)

    @property
    def high(
            self
            ) -> '''(
                _Ref |
                None
                )''':
        _, _, w = self.manager._succ[abs(self.node)]
        if w is None:
            return None
        return Function(w, self.bdd)

    @property
    def ref(
            self
            ) -> _Cardinality:
        return self.manager._ref[abs(self.node)]

    @property
    def negated(
            self
            ) -> _Yes:
        return self.node < 0

    @property
    def support(
            self
            ) -> set[_VariableName]:
        return self.manager.support(self.node)
