"""Tests of module `dd._parser`."""
# This file is released in the public domain.
#
import collections.abc as _abc
import itertools as _itr
import logging
import math
import sys
import typing as _ty

import dd.autoref as _bdd
import dd._parser
import pytest

import iterative_recursive_flattener as _flattener


_log = logging.getLogger(__name__)


def _make_parser_test_expressions(
        ) -> _abc.Iterable[str]:
    """Yield test formulas."""
    expressions = [
        '~ FALSE',
        '~ TRUE',
        '! FALSE',
        '! TRUE',
        '@15',
        '@-24',
        r'FALSE /\ TRUE',
        r'TRUE /\ FALSE',
        r'FALSE \/ TRUE',
        r'TRUE \/ FALSE',
        r'TRUE \/ TRUE \/ FALSE',
        'TRUE # FALSE',
        'TRUE && TRUE',
        'FALSE || TRUE',
        'TRUE & FALSE',
        'FALSE | TRUE',
        'TRUE ^ FALSE',
        r'\E x, y, z:  TRUE ^ x => y',
        r'\A y:  y \/ x',
        r'(TRUE) => (FALSE /\ TRUE)',
        'TRUE <=> TRUE',
        '~ (FALSE <=> FALSE)',
        'ite(FALSE, FALSE, TRUE)',
        " var_name' => x' ",
        ]
    def rm_blanks(expr):
        return expr.replace('\x20', '')
    return _itr.chain(
        expressions,
        map(rm_blanks, expressions))


BDD_TRANSLATION_TEST_EXPRESSIONS: _ty.Final = [
    '~ a',
    r'a /\ b',
    r'a \/ b',
    'a => b',
    'a <=> b',
    'a # b',
    'a ^ b',
    r'\E a:  a => b',
    r'\A a:  \E b:  a \/ ~ b',
    r'! a /\ ~ b',
    'a || b',
    'a | b | c',
    'a && b && c',
    'a & b',
    'b -> a',
    'c -> a -> b',
    'b <-> a',
    r'(a \/ b) & c',
    ]
PARSER_TEST_EXPRESSIONS: _ty.Final = list(
    _make_parser_test_expressions())


def test_all_parsers_same_results():
    parser = dd._parser.Parser()
    bdd = _bdd.BDD()
    bdd.declare('a', 'b', 'c')
    for expr in BDD_TRANSLATION_TEST_EXPRESSIONS:
        u1 = dd._parser.add_expr(expr, bdd)
            # translator that directly
            # creates BDDs from expression strings
        tree = parser.parse(expr)
            # parser creates a syntax tree
        u2 = _flattener._recurse_syntax_tree(tree, bdd)
            # recursive translation of
            # syntax tree to BDD
        u3 = _flattener._reduce_syntax_tree(tree, bdd)
            # iterative translation of
            # syntax tree to BDD
        assert u1 == u2, (
            u1, u2,
            bdd.to_expr(u1),
            bdd.to_expr(u2))
        assert u2 == u3, (u2, u3)


def test_translator_vs_recursion_limit():
    bdd = _bdd.BDD()
    bdd.declare('a', 'b', 'c')
    parser = dd._parser.Parser()
    # expression < recursion limit
    expr = r'a /\ b \/ c'
    dd._parser.add_expr(expr, bdd)
    # expression > recursion limit
    expr = make_expr_gt_recursion_limit()
    dd._parser.add_expr(expr, bdd)


def test_log_syntax_tree_to_bdd():
    bdd = _bdd.BDD()
    bdd.declare('a')
    expr = syntax_tree_of_shape('log')
    # parse to syntax tree
    parser = dd._parser.Parser()
    tree = parser.parse(expr)
    # flatten to BDD
    u1 = dd._parser.add_expr(expr, bdd)
    u2 = _flattener._recurse_syntax_tree(tree, bdd)
    u3 = _flattener._reduce_syntax_tree(tree, bdd)
    assert u1 == u2, (u1, u2)
    assert u2 == u3, (u2, u3)


def test_linear_syntax_tree_to_bdd():
    bdd = _bdd.BDD()
    bdd.declare('a')
    expr = syntax_tree_of_shape('linear')
    # parse to syntax tree
    parser = dd._parser.Parser()
    tree = parser.parse(expr)
    # flatten to BDD
    u1 = dd._parser.add_expr(expr, bdd)
    u2 = _flattener._reduce_syntax_tree(tree, bdd)
    assert u1 == u2, (u1, u2)
    with pytest.raises(RecursionError):
        _flattener._recurse_syntax_tree(tree, bdd)


def make_expr_gt_recursion_limit(
        ) -> str:
    """Return expression with many operators.

    The returned expression contains more
    operator applications than Python's
    current recursion limit.
    """
    recursion_limit = sys.getrecursionlimit()
    n_operators = 2 * recursion_limit
    tail = n_operators * r' /\ a '
    return f' a{tail} '


def syntax_tree_of_shape(
        shape:
            _ty.Literal[
                'log',
                'linear']
        ) -> str:
    """Return expression."""
    match shape:
        case 'log':
            delimit = True
        case 'linear':
            delimit = False
        case _:
            raise ValueError(shape)
    recursion_limit = sys.getrecursionlimit()
    log2 = math.log2(recursion_limit)
    depth = round(2 + log2)
    expr = 'a'
    for _ in range(depth):
        expr = _delimit(
            rf'{expr} /\ {expr}',
            '(', ')',
            delimit)
    return expr


def _delimit(
        expr:
            str,
        start:
            str,
        end:
            str,
        delimit:
            bool
        ) -> str:
    """Return `expr` delimited."""
    if not delimit:
        return expr
    return f'{start} {expr} {end}'


def test_lexing():
    lexer = dd._parser.Lexer()
    expr = 'variable'
    tokens = tokenize(expr, lexer)
    assert len(tokens) == 1, tokens
    token, = tokens
    assert token.type == 'NAME', token.type
    assert token.value == 'variable', token.value
    expr = " primed' "
    tokens = tokenize(expr, lexer)
    assert len(tokens) == 1, tokens
    token, = tokens
    assert token.type == 'NAME', token.type
    assert token.value == "primed'", token.value
    expr = '~ a'
    tokens = tokenize(expr, lexer)
    assert len(tokens) == 2, tokens
    tilde, name = tokens
    assert tilde.type == 'NOT', tilde.type
    assert tilde.value == '!', tilde.value
    assert name.type == 'NAME', name.type
    assert name.value == 'a', name.value
    expr = '! a'
    tokens = tokenize(expr, lexer)
    assert len(tokens) == 2, tokens
    not_, name = tokens
    assert not_.type == 'NOT', not_.type
    assert not_.value == '!', not_.value
    assert name.type == 'NAME', name.type
    assert name.value == 'a', name.value
    infixal = [
        (r'a /\ b', 'AND', '&'),
        ('a && b', 'AND', '&'),
        ('a & b', 'AND', '&'),
        (r'a \/ b', 'OR', '|'),
        ('a || b', 'OR', '|'),
        ('a | b', 'OR', '|'),
        ('a => b', 'IMPLIES', '=>'),
        ('a -> b', 'IMPLIES', '=>'),
        ('a <=> b', 'EQUIV', '<->'),
        ('a <-> b', 'EQUIV', '<->'),
        ('a # b', 'XOR', '#'),
        ('a ^ b', 'XOR', '^'),
        ('a = b', 'EQUALS', '='),
        ]
    for expr, op_type, op_value in infixal:
        tokens = tokenize(expr, lexer)
        assert len(tokens) == 3, tokens
        a, op, b = tokens
        _assert_names_operator(
            op, a, b, op_type, op_value)
    expr = '@4'
    tokens = tokenize(expr, lexer)
    assert len(tokens) == 2, tokens
    at, four = tokens
    assert at.type == 'AT', at.type
    assert at.value == '@', at.value
    assert four.type == 'NUMBER', four.type
    assert four.value == '4', four.value
    expr = '@-1'
    tokens = tokenize(expr, lexer)
    assert len(tokens) == 3, tokens
    at, minus, one = tokens
    assert at.type == 'AT', at.type
    assert at.value == '@', at.value
    assert minus.type == 'MINUS', minus.type
    assert minus.value == '-', minus.value
    assert one.type == 'NUMBER', one.type
    assert one.value == '1', one.value
    expr = r'\A x1, x2, x3:  (x1 => (x2 <=> x3))'
    tokens = tokenize(expr, lexer)
    assert len(tokens) == 16, tokens
    (forall, x1_1, comma_1, x2_1, comma_2,
        x3_1, colon, lparen_1, x1_2, implies,
        lparen_2, x2_2, equiv, x3_2, rparen_1,
        rparen_2) = tokens
    assert forall.type == 'FORALL', forall.type
    assert forall.value == r'\A', forall.value
    assert x1_1.type == 'NAME', x1_1.type
    assert x1_1.value == 'x1', x1_1.value
    assert x1_2.type == 'NAME', x1_2.type
    assert x1_2.value == 'x1', x1_2.value
    assert x2_1.type == 'NAME', x2_1.type
    assert x2_1.value == 'x2', x2_1.value
    assert x2_2.type == 'NAME', x2_2.type
    assert x2_2.value == 'x2', x2_2.value
    assert x3_1.type == 'NAME', x3_1.type
    assert x3_1.value == 'x3', x3_1.value
    assert x3_2.type == 'NAME', x3_2.type
    assert x3_2.value == 'x3', x3_2.value
    assert colon.type == 'COLON', colon.type
    assert colon.value == ':', colon.value
    assert lparen_1.type == 'LPAREN', lparen_1.type
    assert lparen_1.value == '(', lparen_1.value
    assert lparen_2.type == 'LPAREN', lparen_1.type
    assert lparen_2.value == '(', lparen_2.value
    assert rparen_1.type == 'RPAREN', rparen_1.type
    assert rparen_1.value == ')', rparen_1.value
    assert rparen_2.type == 'RPAREN', rparen_2.type
    assert rparen_2.value == ')', rparen_2.value
    assert implies.type == 'IMPLIES', implies.type
    assert implies.value == '=>', implies.value
    assert equiv.type == 'EQUIV', equiv.type
    assert equiv.value == '<->', equiv.value
    assert comma_1.type == 'COMMA', comma_1.type
    assert comma_1.value == ',', comma_1.value
    assert comma_2.type == 'COMMA', comma_2.type
    assert comma_2.value == ',', comma_2.value
    expr = r'\E x, y:  x /\ y'
    tokens = tokenize(expr, lexer)
    assert len(tokens) == 8, tokens
    (exists, x_1, comma, y_1, colon,
        x_2, and_, y_2) = tokens
    assert exists.type == 'EXISTS', exists.type
    assert exists.value == r'\E', exists.value
    assert x_1.type == 'NAME', x_1.type
    assert x_1.value == 'x', x_1.value
    assert x_2.type == 'NAME', x_2.type
    assert x_2.value == 'x', x_2.value
    assert y_1.type == 'NAME', y_1.type
    assert y_1.value == 'y', y_1.value
    assert y_2.type == 'NAME', y_2.type
    assert y_2.value == 'y', y_2.value
    assert and_.type == 'AND', and_.type
    assert and_.value == '&', and_.value
    assert colon.type == 'COLON', colon.type
    assert colon.value == ':', colon.value
    assert comma.type == 'COMMA', comma.type
    assert comma.value == ',', comma.value


def _assert_names_operator(
        op,
        a,
        b,
        op_type,
        op_value):
    assert a.type == 'NAME', a.type
    assert a.value == 'a', a.value
    assert b.type == 'NAME', b.type
    assert b.value == 'b', b.value
    assert op.type == op_type, (
        op.type, op_type)
    assert op.value == op_value, (
        op.value, op_value)


def tokenize(
        string:
            str,
        lexer
        ) -> list:
    r"""Return tokens representing `string`.

    ```tla
    ASSUME
        /\ hasattr(lexer, 'lexer')
        /\ hasattr(lexer.lexer, 'input')
        /\ is_iterable(lexer.lexer)
    ```
    """
    lexer.lexer.input(string)
    return list(lexer.lexer)


def test_parsing():
    # nullary operators
    parser = dd._parser.Parser()
    expr = 'FALSE'
    tree = parser.parse(expr)
    _assert_false_node(tree)
    expr = 'TRUE'
    tree = parser.parse(expr)
    _assert_true_node(tree)
    expr = '@1'
    tree = parser.parse(expr)
    assert tree.type == 'num', tree.type
    assert tree.value == '1', tree.value
    expr = '@20'
    tree = parser.parse(expr)
    assert tree.type == 'num', tree.type
    assert tree.value == '20', tree.value
    expr = 'operator_name'
    tree = parser.parse(expr)
    assert tree.type == 'var', tree.type
    assert (tree.value == 'operator_name'
        ), tree.value
    expr = "operator_name'"
    tree = parser.parse(expr)
    assert tree.type == 'var', tree.type
    assert (tree.value == "operator_name'"
        ), tree.value
    expr = '_OPerATorN_amE'
    tree = parser.parse(expr)
    assert (tree.type == 'var'
        ), tree.type
    assert tree.value == '_OPerATorN_amE'
    # unary operators
    expr = '~ FALSE'
    tree = parser.parse(expr)
    assert tree.type == 'operator', tree.type
    assert tree.operator == '!', tree.operator
    assert (len(tree.operands) == 1
        ), tree.operands
    tree, = tree.operands
    _assert_false_node(tree)
    expr = '! TRUE'
    tree = parser.parse(expr)
    assert tree.type == 'operator', tree.type
    assert tree.operator == '!', tree.operator
    assert (len(tree.operands) == 1
        ), tree.operands
    tree, = tree.operands
    _assert_true_node(tree)
    expr = '@1'
    tree = parser.parse(expr)
    assert tree.type == 'num', tree.type
    assert tree.value == '1', tree.value
    expr = '@-5'
    tree = parser.parse(expr)
    assert tree.type == 'num', tree.type
    assert tree.value == '-5', tree.value
    # binary operators
    binary_operators = {
        '/\\':
            '&',
        r'\/':
            '|',
        '=>':
            '=>',
        '<=>':
            '<->',
        '&&':
            '&',
        '||':
            '|',
        '->':
            '=>',
        '<->':
            '<->',
        '&':
            '&',
        '|':
            '|',
        '^':
            '^',
        '#':
            '#',
        '=':
            '=',
        }
    pairs = binary_operators.items()
    for operator, token_type in pairs:
        _check_binary_operator(
            operator, token_type,
            parser)
    expr = 'TRUE <=> TRUE'
    tree = parser.parse(expr)
    _assert_binary_operator_tree(tree, '<->')
    true_1, true_2 = tree.operands
    _assert_true_node(true_1)
    _assert_true_node(true_2)
    expr = '(TRUE)'
    tree = parser.parse(expr)
    _assert_true_node(tree)
    expr = '(~ TRUE)'
    tree = parser.parse(expr)
    assert tree.type == 'operator', tree.type
    assert tree.operator == '!', tree.operator
    assert (len(tree.operands) == 1
        ), tree.operands
    true, = tree.operands
    _assert_true_node(true)
    expr = r'(TRUE /\ FALSE)'
    tree = parser.parse(expr)
    _assert_binary_operator_tree(tree, '&')
    true, false = tree.operands
    _assert_false_true_nodes(false, true)
    # ternary operators
    expr = 'ite(TRUE, FALSE, TRUE)'
    tree = parser.parse(expr)
    assert tree.type == 'operator', tree.type
    assert tree.operator == 'ite', tree.operator
    assert (len(tree.operands) == 3
        ), tree.operands
    true_1, false, true_2 = tree.operands
    _assert_true_node(true_1)
    _assert_true_node(true_2)
    _assert_false_node(false)
    # quantification
    expr = r'\A x, y, z:  (x /\ y) => z'
    tree = parser.parse(expr)
    assert tree.type == 'operator', tree.type
    assert tree.operator == r'\A', tree.operator
    assert (len(tree.operands) == 2
        ), tree.operands
    names, predicate = tree.operands
    assert len(names) == 3, names
    x, y, z = names
    assert x.type == 'var', x.type
    assert x.value == 'x', x.value
    assert y.type == 'var', y.type
    assert y.value == 'y', y.value
    assert z.type == 'var', z.type
    assert z.value == 'z', z.value
    _assert_binary_operator_tree(
        predicate, '=>')
    expr_1, expr_2 = predicate.operands
    _assert_binary_operator_tree(
        expr_1, '&')
    x, y = expr_1.operands
    assert x.type == 'var', x.type
    assert x.value == 'x', x.value
    assert y.type == 'var', y.type
    assert y.value == 'y', y.value
    assert expr_2.type == 'var', expr_2.type
    assert expr_2.value == 'z', expr_2.value
    names, predicate = tree.operands
    expr = r'\E u:  (u = x) \/ (x # u)'
    tree = parser.parse(expr)
    assert tree.type == 'operator', tree.type
    assert (tree.operator == r'\E'
        ), tree.operator
    assert (len(tree.operands) == 2
        ), tree.operands
    names, predicate = tree.operands
    assert len(names) == 1, names
    name, = names
    assert name.type == 'var', name.type
    assert name.value == 'u', name.value
    _assert_binary_operator_tree(
        predicate, '|')
    expr_1, expr_2 = predicate.operands
    _assert_binary_operator_tree(expr_1, '=')
    u, x = expr_1.operands
    assert u.type == 'var', u.type
    assert u.value == 'u', u.value
    assert x.type == 'var', x.type
    assert x.value == 'x', x.value
    _assert_binary_operator_tree(expr_2, '#')
    x, u = expr_2.operands
    assert x.type == 'var', x.type
    assert x.value == 'x', x.value
    assert u.type == 'var', u.type
    assert u.value == 'u', u.value


def _check_binary_operator(
        operator:
            str,
        token_type:
            str,
        parser
        ) -> None:
    expr = f'FALSE {operator} TRUE'
    _log.debug(expr)
    tree = parser.parse(expr)
    _assert_binary_operator_tree(
        tree, token_type)
    false, true = tree.operands
    _assert_false_true_nodes(false, true)


def _assert_binary_operator_tree(
        tree,
        operator:
            str
        ) -> None:
    assert tree.type == 'operator', tree.type
    assert tree.operator == operator, (
        tree.operator, operator)
    assert (len(tree.operands) == 2
        ), tree.operands


def _assert_false_true_nodes(
        false,
        true):
    _assert_false_node(false)
    _assert_true_node(true)


def _assert_false_node(
        false):
    assert false.type == 'bool', false.type
    assert false.value == 'FALSE', false.value


def _assert_true_node(
        true):
    assert true.type == 'bool', true.type
    assert true.value == 'TRUE', true.value


def test_add_expr():
    bdd = BDD()
    for expr in PARSER_TEST_EXPRESSIONS:
        _log.debug(expr)
        dd._parser.add_expr(expr, bdd)


class BDD:
    """Scaffold for testing."""

    def __init__(
            self):
        self.false = 1
        self.true = 1

    def _add_int(
            self,
            number):
        _log.debug(f'{number = }')
        return 1

    def var(
            self,
            name):
        _log.debug(f'{name =}')
        return 1

    def apply(
            self,
            operator,
            *operands):
        _log.debug(f'''
            {operator = }
            {operands = }
            ''')
        return 1

    def quantify(
            self,
            u,
            qvars,
            forall=None):
        _log.debug(f'''
            {u = }
            {qvars = }
            {forall = }
            ''')
        return 1

    def rename(
            self,
            u,
            renaming):
        _log.debug(f'''
            {u = }
            {renaming = }
            ''')
        return 1


def test_recursive_traversal_vs_recursion_limit():
    bdd = BDD()
    parser = dd._parser.Parser()
    # expression < recursion limit
    expr = r'a /\ b \/ c'
    tree = parser.parse(expr)
    _flattener._recurse_syntax_tree(tree, bdd)
    # expression > recursion limit
    expr = make_expr_gt_recursion_limit()
    tree = parser.parse(expr)
    with pytest.raises(RecursionError):
        _flattener._recurse_syntax_tree(tree, bdd)


def test_iterative_traversal_vs_recursion_limit():
    bdd = BDD()
    parser = dd._parser.Parser()
    # expression < recursion limit
    expr = r'a \/ ~ b /\ c'
    tree = parser.parse(expr)
    _flattener._reduce_syntax_tree(tree, bdd)
    # expression > recursion limit
    expr = make_expr_gt_recursion_limit()
    tree = parser.parse(expr)
    _flattener._reduce_syntax_tree(tree, bdd)


if __name__ == '__main__':
    test_all_parsers_same_results()
