"""Construct BDD nodes from quantified Boolean formulae."""
# Copyright 2015 by California Institute of Technology
# All rights reserved. Licensed under BSD-3.
#
import logging
import typing as _ty
import astutils


_TABMODULE: _ty.Final[str] =\
    'dd._expr_parser_state_machine'
_QUANTIFIERS = {r'\A', r'\E'}
_BOOLEANS = {'false', 'true'}


class Lexer(astutils.Lexer):
    """Lexer for Boolean formulae."""

    def __init__(self, **kw):
        self.reserved = {
            'ite':
                'ITE',
            'False':
                'FALSE',
            'True':
                'TRUE',
            'FALSE':
                'FALSE',
            'TRUE':
                'TRUE'}
        self.delimiters = [
            'LPAREN',
            'RPAREN',
            'COMMA']
        self.operators = [
            'NOT',
            'AND',
            'OR',
            'XOR',
            'IMPLIES',
            'EQUIV',
            'EQUALS',
            'MINUS',
            'DIV',
            'AT',
            'COLON',
            'FORALL',
            'EXISTS',
            'RENAME']
        self.misc = [
            'NAME',
            'NUMBER']
        super().__init__(**kw)

    def t_NAME(
            self, token):
        r"""
        [A-Za-z_]
        [A-za-z0-9_']*
        """
        token.type = self.reserved.get(
            token.value, 'NAME')
        return token

    def t_AND(
            self, token):
        r"""
          \&\&
        | \&
        | /\\
        """
        token.value = '&'
        return token

    def t_OR(
            self, token):
        r"""
          \|\|
        | \|
        | \\/
        """
        token.value = '|'
        return token

    def t_NOT(
            self, token):
        r"""
          \~
        | !
        """
        token.value = '!'
        return token

    def t_IMPLIES(
            self, token):
        r"""
          =>
        | \->
        """
        token.value = '=>'
        return token

    def t_EQUIV(
            self, token):
        r"""
          <=>
        | <\->
        """
        token.value = '<->'
        return token

    t_XOR = r'''
          \#
        | \^
        '''
    t_EQUALS = r' = '
    t_LPAREN = r' \( '
    t_RPAREN = r' \) '
    t_MINUS = r' \- '
    t_NUMBER = r' \d+ '
    t_COMMA = r' , '
    t_COLON = r' : '
    t_FORALL = r' \\ A '
    t_EXISTS = r' \\ E '
    t_RENAME = r' \\ S '
    t_DIV = r' / '
    t_AT = r' @ '
    t_ignore = ''.join(['\x20', '\t'])

    def t_trailing_comment(
            self, token):
        r' \\ \* .* '
        return None

    def t_doubly_delimited_comment(
            self, token):
        r"""
        \( \*
        [\s\S]*?
        \* \)
        """
        return None

    def t_newline(
            self, token):
        r' \n+ '
        token.lexer.lineno += (
            token.value.count('\n'))


class Parser(astutils.Parser):
    """Parser for Boolean formulae."""

    def __init__(self, **kw):
        self.tabmodule = _TABMODULE
        self.start = 'expr'
        # low to high
        self.precedence = (
            ('left',
                'COLON'),
            ('left',
                'EQUIV'),
            ('left',
                'IMPLIES'),
            ('left',
                'MINUS'),
            ('left',
                'XOR'),
            ('left',
                'OR'),
            ('left',
                'AND'),
            ('left',
                'EQUALS'),
            ('right',
                'NOT'),
            ('right',
                'UMINUS'))
        kw.setdefault('lexer', Lexer())
        super().__init__(**kw)

    def p_bool(
            self, p):
        """expr : TRUE
                | FALSE
        """
        p[0] = self.nodes.Terminal(
            p[1], 'bool')

    def p_node(
            self, p):
        """expr : AT number"""
        p[0] = p[2]

    def p_number(
            self, p):
        """number : NUMBER"""
        p[0] = self.nodes.Terminal(
            p[1], 'num')

    def p_negative_number(
            self, p):
        ("""number : MINUS NUMBER """
         """           %prec UMINUS""")
        x = p[1] + p[2]
        p[0] = self.nodes.Terminal(
            x, 'num')

    def p_var(
            self, p):
        """expr : name"""
        p[0] = p[1]

    def p_unary(
            self, p):
        """expr : NOT expr"""
        p[0] = self.nodes.Operator(
            p[1], p[2])

    def p_binary(
            self, p):
        """expr : expr AND expr
                | expr OR expr
                | expr XOR expr
                | expr IMPLIES expr
                | expr EQUIV expr
                | expr EQUALS expr
                | expr MINUS expr
        """
        p[0] = self.nodes.Operator(
            p[2], p[1], p[3])

    def p_ternary_conditional(
            self, p):
        ("""expr : ITE LPAREN """
         """             expr COMMA """
         """             expr COMMA """
         """             expr RPAREN""")
        p[0] = self.nodes.Operator(
            p[1], p[3], p[5], p[7])

    def p_quantifier(
            self, p):
        """expr : EXISTS names COLON expr
                | FORALL names COLON expr
        """
        p[0] = self.nodes.Operator(
            p[1], p[2], p[4])

    def p_rename(
            self, p):
        """expr : RENAME subs COLON expr"""
        p[0] = self.nodes.Operator(
            p[1], p[4], p[2])

    def p_substitutions_iter(
            self, p):
        """subs : subs COMMA sub"""
        u = p[1]
        u.append(p[3])
        p[0] = u

    def p_substitutions_end(
            self, p):
        """subs : sub"""
        p[0] = [p[1]]

    def p_substitution(
            self, p):
        """sub : name DIV name"""
        new = p[1]
        old = p[3]
        p[0] = (old, new)

    def p_names_iter(
            self, p):
        """names : names COMMA name"""
        u = p[1]
        u.append(p[3])
        p[0] = u

    def p_names_end(
            self, p):
        """names : name"""
        p[0] = [p[1]]

    def p_name(
            self, p):
        """name : NAME"""
        p[0] = self.nodes.Terminal(
            p[1], 'var')

    def p_paren(
            self, p):
        """expr : LPAREN expr RPAREN"""
        p[0] = p[2]


_parsers = dict()


def add_expr(expression, bdd):
    """Return `bdd` node for `expression`.

    Creates a node that represents `expression`,
    and returns this node.

    @type expression:
        `str`
    """
    if 'boolean' not in _parsers:
        _parsers['boolean'] = Parser()
    tree = _parsers['boolean'].parse(expression)
    return _add_ast(tree, bdd)


def _add_ast(tree, bdd):
    """Add abstract syntax `tree` to `self`.

    Any AST nodes are acceptable,
    provided they have attributes:
      - `"operator"` and `"operands"` for
        operator nodes
      - `"value"` equal to:
        - `"True"` or `"False"` for
          Boolean constants
        - a key (var name) passed to
          `bdd.var()` for variables

    @type tree:
        `Terminal` or `Operator` of
        `astutils`
    @type bdd:
        object with:
        - `bdd.false`
        - `bdd.true`
        - `bdd.var()`
        - `bdd.apply()`
        - `bdd.quantify()`
    """
    if tree.type == 'operator':
        if (tree.operator in _QUANTIFIERS and
                len(tree.operands) == 2):
            qvars, expr = tree.operands
            qvars = {x.value for x in qvars}
            forall = (tree.operator == r'\A')
            u = _add_ast(expr, bdd)
            return bdd.quantify(
                u, qvars,
                forall=forall)
        elif tree.operator == r'\S':
            expr, rename = tree.operands
            rename = {
                k.value: v.value
                for k, v in rename}
            u = _add_ast(expr, bdd)
            return bdd.rename(u, rename)
        else:
            operands = [
                _add_ast(x, bdd)
                for x in tree.operands]
            return bdd.apply(
                tree.operator, *operands)
    elif tree.type == 'bool':
        value = tree.value.lower()
        if value not in _BOOLEANS:
            raise ValueError(tree.value)
        return getattr(bdd, value)
    elif tree.type == 'var':
        return bdd.var(tree.value)
    elif tree.type == 'num':
        i = int(tree.value)
        return bdd._add_int(i)
    raise ValueError(
        f'unknown node type:  {tree.type = }')


def _rewrite_tables(outputdir='./'):
    """Recache state machine of parser.

    @type outputdir:
        `str`
    """
    astutils.rewrite_tables(
        Parser, _TABMODULE, outputdir)


def _main():
    """Recompute parser state machine.

    Cache the state machine in a file.
    Configure logging.
    """
    log = logging.getLogger('astutils')
    log.setLevel('DEBUG')
    log.addHandler(logging.StreamHandler())
    _rewrite_tables()


if __name__ == '__main__':
    _main()
