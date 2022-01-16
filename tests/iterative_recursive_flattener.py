"""Mapping trees to BDDs by iteration, and by recursion.

The iterative traversal avoids exceeding:
- CPython's call-stack bound, and
- the underlying C call-stack bound.
"""
# This file is released in the public domain.
#
import typing as _ty


_QUANTIFIERS: _ty.Final = {
    r'\A',
    r'\E'}
_LEAFS: _ty.Final = {
    'bool',
    'num',
    'var'}
_BOOLEANS: _ty.Final = {
    'false',
    'true'}


def _recurse_syntax_tree(
        tree,
        bdd):
    r"""Add abstract syntax `tree` to `self`.

    ```tla
    ASSUME
        /\ hasattr(tree_node, 'operator')
        /\ hasattr(tree_node, 'operands')
        /\ \/ ~ is_leaf(tree_node)
           \/ /\ hasattr(tree_node, value)
              /\ \/ tree_node.value \in {"FALSE", "TRUE"}
                    (* for leaf nodes that represent
                    Boolean constants
                    *)
                 \/ tree_node.value \in STRING \ {
                        "FALSE", "TRUE"}
                    (* for leaf nodes that represent
                    identifiers of BDD variables, or
                    numeric literals
                    *)
    ```
    """
    match tree.type:
        case 'operator':
            if (tree.operator in _QUANTIFIERS and
                    len(tree.operands) == 2):
                qvars, expr = tree.operands
                qvars = {x.value for x in qvars}
                forall = (tree.operator == r'\A')
                u = _recurse_syntax_tree(expr, bdd)
                return bdd.quantify(
                    u, qvars,
                    forall=forall)
            elif tree.operator == r'\S':
                expr, rename = tree.operands
                rename = {
                    k.value: v.value
                    for k, v in rename}
                u = _recurse_syntax_tree(expr, bdd)
                return bdd.rename(u, rename)
            else:
                operands = [
                    _recurse_syntax_tree(x, bdd)
                    for x in tree.operands]
                return bdd.apply(
                    tree.operator, *operands)
        case 'bool':
            value = tree.value.lower()
            if value not in _BOOLEANS:
                raise ValueError(tree.value)
            return getattr(bdd, value)
        case 'var':
            return bdd.var(tree.value)
        case 'num':
            i = int(tree.value)
            return bdd._add_int(i)
    raise ValueError(
        f'unknown node type:  {tree.type = }')


def _reduce_syntax_tree(
        tree,
        bdd):
    """Convert syntax tree to decision diagram.

    This function is implemented iteratively
    in Python, in order to avoid recursion
    limits of Python's implementation.
    """
    stack = [
        list(),
        [tree]]
    while len(stack) > 1:
        _reduce_step(stack, bdd)
    if len(stack) == 1 and len(stack[0]):
        res, = stack[0]
        return res
    raise AssertionError(stack)


def _reduce_step(
        stack:
            list,
        bdd
        ) -> None:
    """Step in iteration of tree reduction."""
    tree, *operands = stack[-1]
    match tree.type:
        case 'operator':
            if tree.operator in _QUANTIFIERS:
                _reduce_quantifier(
                    tree, operands, stack, bdd)
            elif tree.operator == r'\S':
                _reduce_substitution(
                    tree, operands, stack, bdd)
            else:
                _reduce_operator(
                    tree, operands, stack, bdd)
        case 'bool':
            stack.pop()
            value = tree.value.lower()
            if value not in _BOOLEANS:
                raise ValueError(tree.value)
            u = getattr(bdd, value)
            stack[-1].append(u)
        case 'var':
            stack.pop()
            value = bdd.var(tree.value)
            stack[-1].append(value)
        case 'num':
            stack.pop()
            number = int(tree.value)
            value = bdd._add_int(number)
            stack[-1].append(value)
        case _:
            raise ValueError(
                f'unknown node type:  {tree.type}')


def _reduce_quantifier(
        tree,
        operands,
        stack:
            list,
        bdd
        ) -> None:
    """Reduce quantifier tree."""
    if not operands:
        _, successor = tree.operands
        stack.append([successor])
        return
    u, = operands
    qvars, _ = tree.operands
    qvars = {
        name.value
        for name in qvars}
    forall = (tree.operator == r'\A')
    res = bdd.quantify(
        u, qvars,
        forall=forall)
    stack.pop()
    stack[-1].append(res)


def _reduce_substitution(
        tree,
        operands,
        stack:
            list,
        bdd
        ) -> None:
    """Reduce `LET`."""
    if not operands:
        successor, _ = tree.operands
        stack.append([successor])
        return
    u, = operands
    _, renaming = tree.operands
    renaming = {
        k.value: v.value
        for k, v in renaming}
    res = bdd.rename(u, renaming)
    stack.pop()
    stack[-1].append(res)


def _reduce_operator(
        tree,
        operands,
        stack:
            list,
        bdd
        ) -> None:
    """Reduce operator application."""
    n_operands = len(operands)
    n_successors = len(tree.operands)
    if 0 < n_operands == n_successors:
        res = bdd.apply(
            tree.operator,
            *operands)
        stack.pop()
        stack[-1].append(res)
    elif 0 <= n_operands < n_successors:
        successor = tree.operands[n_operands]
        stack.append([successor])
    else:
        raise AssertionError(
            tree, operands)
