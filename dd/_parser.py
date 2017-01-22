"""Construct BDD nodes from quantified Boolean formulae."""
# Copyright 2015 by California Institute of Technology
# All rights reserved. Licensed under BSD-3.
#
import logging
import astutils


TABMODULE = 'dd.bdd_parsetab'


class Lexer(astutils.Lexer):
    """Lexer for Boolean formulae."""

    reserved = {
        'ite': 'ITE',
        'False': 'FALSE',
        'True': 'TRUE'}
    delimiters = ['LPAREN', 'RPAREN', 'COMMA']
    operators = ['NOT', 'AND', 'OR', 'XOR', 'IMPLIES', 'EQUIV',
                 'EQUALS', 'MINUS', 'DIV',
                 'COLON', 'FORALL', 'EXISTS', 'RENAME']
    misc = ['NAME', 'NUMBER']

    def t_NAME(self, t):
        r"[A-Za-z_][A-za-z0-9_']*"
        t.type = self.reserved.get(t.value, 'NAME')
        return t

    def t_AND(self, t):
        r'\&\&|\&|/\\'
        t.value = '&'
        return t

    def t_OR(self, t):
        r'\|\||\||\\/'
        t.value = '|'
        return t

    def t_NOT(self, t):
        r'~|\!'
        t.value = '!'
        return t

    def t_IMPLIES(self, t):
        r'\=>|->'
        t.value = '=>'
        return t

    def t_EQUIV(self, t):
        r'\<\=>|\<->'
        t.value = '<->'
        return t

    t_XOR = r'\^'
    t_EQUALS = r'\='
    t_LPAREN = r'\('
    t_RPAREN = r'\)'
    t_MINUS = r'-'
    t_NUMBER = r'\d+'
    t_COMMA = r','
    t_COLON = r'\:'
    t_FORALL = r'\\A'
    t_EXISTS = r'\\E'
    t_RENAME = r'\\S'
    t_DIV = r'/'
    t_ignore = " \t"

    def t_comment(self, t):
        r'\#.*'
        return

    def t_newline(self, t):
        r'\n+'
        t.lexer.lineno += t.value.count("\n")


class Parser(astutils.Parser):
    """Parser for Boolean formulae."""

    tabmodule = TABMODULE
    start = 'expr'
    # low to high
    precedence = (
        ('left', 'COLON'),
        ('left', 'EQUIV'),
        ('left', 'IMPLIES'),
        ('left', 'MINUS'),
        ('left', 'XOR'),
        ('left', 'OR'),
        ('left', 'AND'),
        ('left', 'EQUALS'),
        ('right', 'NOT'),
        ('right', 'UMINUS'))
    Lexer = Lexer

    def p_bool(self, p):
        """expr : TRUE
                | FALSE
        """
        p[0] = self.nodes.Terminal(p[1], 'bool')

    def p_number(self, p):
        """expr : NUMBER"""
        p[0] = self.nodes.Terminal(p[1], 'num')

    def p_negative_number(self, p):
        """expr : MINUS NUMBER %prec UMINUS"""
        x = p[1] + p[2]
        p[0] = self.nodes.Terminal(x, 'num')

    def p_var(self, p):
        """expr : name"""
        p[0] = p[1]

    def p_unary(self, p):
        """expr : NOT expr"""
        p[0] = self.nodes.Operator(p[1], p[2])

    def p_binary(self, p):
        """expr : expr AND expr
                | expr OR expr
                | expr XOR expr
                | expr IMPLIES expr
                | expr EQUIV expr
                | expr EQUALS expr
                | expr MINUS expr
        """
        p[0] = self.nodes.Operator(p[2], p[1], p[3])

    def p_ternary_conditional(self, p):
        """expr : ITE LPAREN expr COMMA expr COMMA expr RPAREN"""
        p[0] = self.nodes.Operator(p[1], p[3], p[5], p[7])

    def p_quantifier(self, p):
        """expr : EXISTS names COLON expr
                | FORALL names COLON expr
        """
        p[0] = self.nodes.Operator(p[1], p[2], p[4])

    def p_rename(self, p):
        """expr : RENAME subs COLON expr"""
        p[0] = self.nodes.Operator(p[1], p[4], p[2])

    def p_substitutions_iter(self, p):
        """subs : subs COMMA sub"""
        u = p[1]
        u.append(p[3])
        p[0] = u

    def p_substitutions_end(self, p):
        """subs : sub"""
        p[0] = [p[1]]

    def p_substitution(self, p):
        """sub : name DIV name"""
        new = p[1]
        old = p[3]
        p[0] = (old, new)

    def p_names_iter(self, p):
        """names : names COMMA name"""
        u = p[1]
        u.append(p[3])
        p[0] = u

    def p_names_end(self, p):
        """names : name"""
        p[0] = [p[1]]

    def p_name(self, p):
        """name : NAME"""
        p[0] = self.nodes.Terminal(p[1], 'var')

    def p_paren(self, p):
        """expr : LPAREN expr RPAREN"""
        p[0] = p[2]


_parsers = dict()


def add_expr(e, bdd):
    """Return node for expression `e`, after adding it.

    If the attribute `_parser` is `None`,
    then it is attempted to import `tulip.spec`.
    To avoid this, set `_parser` to a custom parser
    with a method `parse` that returns a syntax tree
    that conforms to `add_ast`.

    @type expr: `str`
    """
    if 'boolean' not in _parsers:
        _parsers['boolean'] = Parser()
    t = _parsers['boolean'].parse(e)
    return add_ast(t, bdd)


def add_ast(t, bdd):
    """Add abstract syntax tree `t` to `self`.

    Any AST nodes are acceptable,
    provided they have attributes:
      - `"operator"` and `"operands"` for operator nodes
      - `"value"` equal to:
        - `"True"` or `"False"` for Boolean constants
        - a key (var name) passed to `bdd.var()` for variables

    @type t: `Terminal` or `Operator` of `astutils`
    @type bdd: object with:
      - `bdd.false`
      - `bdd.true`
      - `bdd.var()`
      - `bdd.apply()`
      - `bdd.quantify()`
    """
    # operator ?
    if t.type == 'operator':
        if t.operator in ('\A', '\E') and len(t.operands) == 2:
            qvars, expr = t.operands
            u = add_ast(expr, bdd)
            qvars = {x.value for x in qvars}
            assert t.operator in ('\A', '\E'), t.operator
            forall = (t.operator == '\A')
            return bdd.quantify(u, qvars, forall=forall)
        elif t.operator == '\S':
            expr, rename = t.operands
            u = add_ast(expr, bdd)
            rename = {k.value: v.value for k, v in rename}
            return bdd.rename(u, rename)
        else:
            operands = [add_ast(x, bdd) for x in t.operands]
            return bdd.apply(t.operator, *operands)
    elif t.type == 'bool':
        u = bdd.false if t.value.lower() == 'false' else bdd.true
        return u
    elif t.type == 'var':
        return bdd.var(t.value)
    elif t.type == 'num':
        i = int(t.value)
        u = bdd._add_int(i)
        return u
    else:
        raise Exception(
            'unknown node type "{t}"'.format(t=t.type))


def _rewrite_tables(outputdir='./'):
    astutils.rewrite_tables(Parser, TABMODULE, outputdir)


if __name__ == '__main__':
    log = logging.getLogger('astutils')
    log.setLevel('DEBUG')
    log.addHandler(logging.StreamHandler())
    _rewrite_tables()
