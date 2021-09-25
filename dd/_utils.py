"""Convenience functions."""
# Copyright 2017-2018 by California Institute of Technology
# All rights reserved. Licensed under 3-clause BSD.
#
import collections as _cl
import collections.abc as _abc
import os
import shlex as _sh
import subprocess as _sbp
import textwrap as _tw
import types
import typing as _ty

import dd._abc

try:
    import networkx as _nx
except ImportError as error:
    _nx = None
    _nx_error = error


if _nx is not None:
    MultiDiGraph: _ty.TypeAlias = _nx.MultiDiGraph


# The mapping from values of argument `op` of
# `__richcmp__()` of Cython objects,
# to the corresponding operator symbols.
# Constants are defined in `cpython.object`.
_CY_SYMBOLS: _ty.Final = {
    2: '==',
    3: '!=',
    0: '<',
    1: '<=',
    4: '>',
    5: '>='}


def import_module(
        module_name:
            str
        ) -> types.ModuleType:
    """Return module with `module_name`, if present.

    Raise `ImportError` otherwise.
    """
    modules = dict(
        networkx=_nx)
    if module_name in modules:
        return modules[module_name]
    errors = dict(
        networkx=_nx_error)
    raise errors[module_name]


def print_var_levels(
        bdd
        ) -> None:
    """Print `bdd` variables ordered by level."""
    n = len(bdd.vars)
    levels = [
        bdd.var_at_level(level)
        for level in range(n)]
    print(
        'Variable order (starting at level 0):\n'
        f'{levels}')


def var_counts(
        bdd
        ) -> str:
    """Return levels and numbers of variables, CUDD indices.

    @type bdd:
        `dd.cudd.BDD` or
        `dd.cudd_zdd.ZDD`
    """
    n_declared_vars = len(bdd.vars)
    n_cudd_vars = bdd._number_of_cudd_vars()
    return _tw.dedent(f'''
        There are:
        {n_cudd_vars} variable indices in CUDD,
        {n_declared_vars} declared variables in {bdd!r}.

        So the set of levels of the declared variables
        is not a contiguous range of integers.

        This can occur when specific levels have been
        given to `{type(bdd)}.add_var()`.

        The declared variables and their levels are:
        {bdd.var_levels}
        ''')


def contiguous_levels(
        callable:
            str,
        bdd
        ) -> str:
    """Return requirement about contiguous levels.

    @type bdd:
        `dd.cudd.BDD` or
        `dd.cudd_zdd.ZDD`
    """
    return _tw.dedent(f'''
        The callable `{callable}()` requires that
        the number of variable indices in CUDD, and
        the number of declared variables in {bdd!r}
        be equal.
        ''')


def raise_runtimerror_about_ref_count(
        ref_count_lb:
            int,
        name:
            str,
        class_name:
            str
        ) -> _ty.NoReturn:
    """Raise `RuntimeError` about reference count lower bound.

    Call this function when an unexpected nonpositive
    lower bound on a node's reference count is detected
    for a `Function` instance.

    @param ref_count_lb:
        lower bound on the reference count of
        the node that the `Function` instance points to.
        ```tla
        ASSUME
            ref_count_lb <= 0
        ```
    @param name:
        to mention as location where
        the error was detected. For example:
        ```python
        'method `dd.cudd.BDD.decref`'
        ```
    @param class_name:
        to mention as name of
        the class of the object where the value
        `ref_count_lb` was found. For example:
        ```python
        '`dd.cudd.Function`'
        ```
    """
    if ref_count_lb > 0:
        raise ValueError(ref_count_lb)
    raise RuntimeError(
        f'The {name} requires '
        'that `u._ref > 0` '
        f'(where `u` is an instance of {class_name}). '
        'This ensures that deallocated memory '
        'in CUDD will not be accessed. The current '
        f'value of attribute `_ref` is:\n{ref_count_lb}\n'
        'For more information read the docstring of '
        f'the class {class_name}.')



@_ty.overload
def map_container(
        mapper:
            _abc.Callable,
        container:
            _abc.Mapping
        ) -> dict:
    ...


@_ty.overload
def map_container(
        mapper:
            _abc.Callable,
        container:
            _abc.Iterable
        ) -> list:
    ...


def map_container(
        mapper,
        container):
    """Map `container`, using `mapper()`.

    If `container` is a sequence,
    then map each item.

    If `container` is a mapping of
    keys to values, then map each value.
    """
    if isinstance(container, _abc.Mapping):
        return _map_values(mapper, container)
    return list(map(mapper, container))


def _map_values(
        mapper:
            _abc.Callable,
        kv:
            _abc.Mapping
        ) -> dict:
    """Map each value of `kv` using `mapper()`.

    The keys of `kv` remain unchanged.
    """
    return {k: mapper(v) for k, v in kv.items()}


def values_of(
        container:
            _abc.Mapping |
            _abc.Collection
        ) -> _abc.Iterable:
    """Return container values.

    @return:
        - `container.values()` if
          `container` is a mapping
        - `container` otherwise
    """
    if isinstance(container, _abc.Mapping):
        return container.values()
    return container


def total_memory(
        ) -> (
            int |
            None):
    """Return number of bytes of memory.

    Requires that:
    - `SC_PAGE_SIZE` and
    - `SC_PHYS_PAGES`
    be readable via `os.sysconf()`.
    """
    names = os.sysconf_names
    has_both = (
        'SC_PAGE_SIZE' in names and
        'SC_PHYS_PAGES' in names)
    if not has_both:
        print(
            'skipping check that '
            'initial memory estimate fits '
            'in available memory of system, '
            "because either `'SC_PAGE_SIZE'` or "
            "`'SC_PHYS_PAGES'` undefined in "
            '`os.sysconf_names`.')
        return None
    page_size = os.sysconf('SC_PAGE_SIZE')
    n_pages = os.sysconf('SC_PHYS_PAGES')
    both_defined = (
        page_size >= 0 and
        n_pages >= 0)
    if not both_defined:
        return None
    return page_size * n_pages


_OPERATOR_MAP: _ty.Final = dict(
    bdd=dict(
        unary=dd._abc.UNARY_OPERATOR_SYMBOLS,
        binary=dd._abc.BINARY_OPERATOR_SYMBOLS,
        ternary=dd._abc.TERNARY_OPERATOR_SYMBOLS,
        all=dd._abc.BDD_OPERATOR_SYMBOLS),
    agd=dict(
        unary=dd._abc.ADD_UNARY_OPERATOR_SYMBOLS,
        binary=dd._abc.ADD_BINARY_OPERATOR_SYMBOLS,
        ternary=dd._abc.ADD_TERNARY_OPERATOR_SYMBOLS,
        all=dd._abc.ADD_OPERATOR_SYMBOLS))


def assert_operator_arity(
        op:
            str,
        v:
            object |
            None,
        w:
            object |
            None,
        diagram_type:
            _ty.Literal[
                'bdd',
                'agd']
        ) -> None:
    """Raise `ValueError` if unexpected values.

    Asserts:
    - `op` is an operator symbol
    - `v` is `None` if `op` is a unary operator
    - `w` is `None` if `op` has arity <= 2
    """
    operators = _OPERATOR_MAP[diagram_type]
    if op not in operators['all']:
        raise ValueError(
            f'Unknown operator: "{op}"')
    if op in operators['unary']:
        if v is not None:
            raise ValueError(
                f'`v is not None`, but: {v}')
        if w is not None:
            raise ValueError(
                f'`w is not None`, but: {w}')
    elif op in operators['binary']:
        if v is None:
            raise ValueError(
                '`v is None`')
        if w is not None:
            raise ValueError(
                f'`w is not None`, but: {w}')
    elif op in operators['ternary']:
        if v is None:
            raise ValueError(
                '`v is None`')
        if w is None:
            raise ValueError(
                '`w is None`')


_GraphType: _ty.TypeAlias = _ty.Literal[
    'digraph',
    'graph',
    'subgraph']
DOT_FILE_TYPES: _ty.Final = {
    'pdf', 'svg', 'png', 'dot'}


class DotGraph:
    def __init__(
            self,
            graph_type:
                _GraphType='digraph',
            rank:
                str |
                None=None
            ) -> None:
        """A DOT graph."""
        self.graph_type = graph_type
        self.rank = rank
        self.nodes = _cl.defaultdict(dict)
        self.edges = _cl.defaultdict(list)
        self.subgraphs = list()

    def add_node(
            self,
            node,
            **kw
            ) -> None:
        """Add node with attributes `kw`.

        If node exists, update its attributes.
        """
        self.nodes[node].update(kw)

    def add_edge(
            self,
            start_node,
            end_node,
            **kw
            ) -> None:
        """Add edge with attributes `kw`.

        Multiple edges can exist between the same nodes.
        """
        self.edges[start_node, end_node].append(kw)

    def to_dot(
            self,
            graph_type:
                _GraphType |
                None=None
            ) -> str:
        """Return DOT code."""
        subgraphs = ''.join(
            g.to_dot(
                graph_type='subgraph')
            for g in self.subgraphs)
        def format_attributes(
                attr
                ) -> str:
            """Return formatted assignment."""
            return ', '.join(
                f'{k}="{v}"'
                for k, v in attr.items())
        def format_node(
                u,
                attr
                ) -> str:
            """Return DOT code for node."""
            attributes = format_attributes(attr)
            return f'{u} [{attributes}];'
        def format_edge(
                u,
                v,
                attr
                ) -> str:
            """Return DOT code for edge."""
            attributes = format_attributes(attr)
            return f'{u} -> {v} [{attributes}];'
        nodes = '\n'.join(
            format_node(u, attr)
            for u, attr in self.nodes.items())
        edges = list()
        for (u, v), attrs in self.edges.items():
            for attr in attrs:
                edge = format_edge(u, v, attr)
                edges.append(edge)
        edges = '\n'.join(edges)
        indent_level = 4 * '\x20'
        def fmt(
                text:
                    str
                ) -> str:
            """Return indented text."""
            newline = '\n' if text else ''
            return newline + _tw.indent(
                text,
                prefix=4 * indent_level)
        nodes = fmt(nodes)
        edges = fmt(edges)
        subgraphs = fmt(subgraphs)
        if graph_type is None:
            graph_type = self.graph_type
        if self.rank is None:
            rank = ''
        else:
            rank = f'rank = {self.rank}'
        return _tw.dedent(f'''
            {graph_type} {{
                {rank}{nodes}{edges}{subgraphs}
            }}
            ''')

    def dump(
            self,
            filename:
                str,
            filetype:
                str,
            **kw
            ) -> None:
        """Write to file."""
        if filetype not in DOT_FILE_TYPES:
            raise ValueError(
                f'Unknown file type "{filetype}" '
                f'for "{filename}"')
        dot_code = self.to_dot()
        if filetype == 'dot':
            with open(filename, 'w') as fd:
                fd.write(dot_code)
            return
        dot = _sh.split(f'''
            dot
                -T{filetype}
                -o '{filename}'
            ''')
        _sbp.run(
            dot,
            encoding='utf8',
            input=dot_code,
            capture_output=True,
            check=True)
