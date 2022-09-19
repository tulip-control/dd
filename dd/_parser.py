"""Construct BDD nodes from quantified Boolean formulae."""
# Copyright 2015 by California Institute of Technology
# All rights reserved. Licensed under BSD-3.
#
import collections.abc as _abc
import logging
import typing as _ty

import astutils


_TABMODULE: _ty.Final[str] =\
    'dd._expr_parser_state_machine'
_TRANSLATOR_CACHE: _ty.Final[str] =\
    'dd._bdd_translator_state_machine'


class _Token(_ty.Protocol):
    type: str
    value: str


class Lexer(astutils.Lexer):
    """Lexer for Boolean formulae."""

    def __init__(
            self,
            **kw
            ) -> None:
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
            self,
            token:
                _Token
            ) -> _Token:
        r"""
        [A-Za-z_]
        [A-za-z0-9_']*
        """
        token.type = self.reserved.get(
            token.value, 'NAME')
        return token

    def t_AND(
            self,
            token:
                _Token
            ) -> _Token:
        r"""
          \&\&
        | \&
        | /\\
        """
        token.value = '&'
        return token

    def t_OR(
            self,
            token:
                _Token
            ) -> _Token:
        r"""
          \|\|
        | \|
        | \\/
        """
        token.value = '|'
        return token

    def t_NOT(
            self,
            token:
                _Token
            ) -> _Token:
        r"""
          \~
        | !
        """
        token.value = '!'
        return token

    def t_IMPLIES(
            self,
            token:
                _Token
            ) -> _Token:
        r"""
          =>
        | \->
        """
        token.value = '=>'
        return token

    def t_EQUIV(
            self,
            token:
                _Token
            ) -> _Token:
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
            self,
            token:
                _Token
            ) -> None:
        r' \\ \* .* '
        return None

    def t_doubly_delimited_comment(
            self,
            token:
                _Token
            ) -> None:
        r"""
        \( \*
        [\s\S]*?
        \* \)
        """
        return None

    def t_newline(
            self,
            token
            ) -> None:
        r' \n+ '
        token.lexer.lineno += (
            token.value.count('\n'))


_ParserResult = _ty.TypeVar('_ParserResult')


class _ParserProtocol(
        _ty.Protocol,
        _ty.Generic[
            _ParserResult]):
    """Parser internal interface."""

    def _apply(
            self,
            operator:
                str,
            *operands:
                _ty.Any
            ) -> _ParserResult:
        ...

    def _add_var(
            self,
            name:
                str
            ) -> _ParserResult:
        ...

    def _add_int(
            self,
            numeric_literal:
                str
            ) -> _ParserResult:
        ...

    def _add_bool(
            self,
            bool_literal:
                str
            ) -> _ParserResult:
        ...


class Parser(
        astutils.Parser,
        _ParserProtocol):
    """Parser for Boolean formulae."""

    def __init__(
            self,
            **kw
            ) -> None:
        tabmodule_is_defined = (
            hasattr(self, 'tabmodule') and
            self.tabmodule)
        if not tabmodule_is_defined:
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

    def _apply(
            self,
            operator:
                str,
            *operands:
                _ty.Any):
        """Return syntax tree of application."""
        if operator == r'\S':
            match operands:
                case subs, expr:
                    pass
                case _:
                    raise AssertionError(operands)
            return self.nodes.Operator(
                operator, expr, subs)
        return self.nodes.Operator(
            operator, *operands)

    def _add_var(
            self,
            name:
                str):
        """Return syntax tree for identifier."""
        return self.nodes.Terminal(
            name, 'var')

    def _add_int(
            self,
            numeric_literal:
                str):
        """Return syntax tree of given index."""
        return self.nodes.Terminal(
            numeric_literal, 'num')

    def _add_bool(
            self,
            bool_literal:
                str):
        """Return syntax tree for Boolean."""
        return self.nodes.Terminal(
            bool_literal, 'bool')

    def p_bool(
            self,
            p:
                list
            ) -> None:
        """expr : TRUE
                | FALSE
        """
        p[0] = self._add_bool(p[1])

    def p_node(
            self,
            p:
                list
            ) -> None:
        """expr : AT number"""
        p[0] = p[2]

    def p_number(
            self,
            p:
                list
            ) -> None:
        """number : NUMBER"""
        p[0] = self._add_int(p[1])

    def p_negative_number(
            self,
            p:
                list
            ) -> None:
        ("""number : MINUS NUMBER """
         """           %prec UMINUS""")
        numeric_literal = f'{p[1]}{p[2]}'
        p[0] = self._add_int(numeric_literal)

    def p_var(
            self,
            p:
                list
            ) -> None:
        """expr : name"""
        p[0] = self._add_var(p[1].value)

    def p_unary(
            self,
            p:
                list
            ) -> None:
        """expr : NOT expr"""
        p[0] = self._apply(
            p[1], p[2])

    def p_binary(
            self,
            p:
                list
            ) -> None:
        """expr : expr AND expr
                | expr OR expr
                | expr XOR expr
                | expr IMPLIES expr
                | expr EQUIV expr
                | expr EQUALS expr
                | expr MINUS expr
        """
        p[0] = self._apply(
            p[2], p[1], p[3])

    def p_ternary_conditional(
            self,
            p:
                list
            ) -> None:
        ("""expr : ITE LPAREN """
         """             expr COMMA """
         """             expr COMMA """
         """             expr RPAREN""")
        p[0] = self._apply(
            p[1], p[3], p[5], p[7])

    def p_quantifier(
            self,
            p:
                list
            ) -> None:
        """expr : EXISTS names COLON expr
                | FORALL names COLON expr
        """
        p[0] = self._apply(
            p[1], p[2], p[4])

    def p_rename(
            self,
            p:
                list
            ) -> None:
        """expr : RENAME subs COLON expr"""
        p[0] = self._apply(
            p[1], p[2], p[4])

    def p_substitutions_iter(
            self,
            p:
                list
            ) -> None:
        """subs : subs COMMA sub"""
        u = p[1]
        u.append(p[3])
        p[0] = u

    def p_substitutions_end(
            self,
            p:
                list
            ) -> None:
        """subs : sub"""
        p[0] = [p[1]]

    def p_substitution(
            self,
            p:
                list
            ) -> None:
        """sub : name DIV name"""
        new = p[1]
        old = p[3]
        p[0] = (old, new)

    def p_names_iter(
            self,
            p:
                list
            ) -> None:
        """names : names COMMA name"""
        u = p[1]
        u.append(p[3])
        p[0] = u

    def p_names_end(
            self,
            p:
                list
            ) -> None:
        """names : name"""
        p[0] = [p[1]]

    def p_name(
            self,
            p:
                list
            ) -> None:
        """name : NAME"""
        p[0] = self.nodes.Terminal(
            p[1], 'var')

    def p_paren(
            self,
            p:
                list
            ) -> None:
        """expr : LPAREN expr RPAREN"""
        p[0] = p[2]


_Ref = _ty.TypeVar('_Ref')


class _BDD(_ty.Protocol[
        _Ref]):
    """Interface of BDD context."""

    @property
    def false(
            self
            ) -> _Ref:
        ...

    @property
    def true(
            self
            ) -> _Ref:
        ...

    def var(
            self,
            name:
                str
            ) -> _Ref:
        ...

    def apply(
            self,
            op:
                str,
            u:
                _Ref,
            v:
                _Ref |
                None=None,
            w:
                _Ref |
                None=None
            ) -> _Ref:
        ...

    def quantify(
            self,
            u:
                _Ref,
            qvars:
                set[str],
            forall:
                bool=False
            ) -> _Ref:
        ...

    def rename(
            self,
            u:
                _Ref,
            renaming:
                _abc.Mapping
            ) -> _Ref:
        ...

    def _add_int(
            self,
            number:
                int
            ) -> _Ref:
        ...


class _Translator(Parser):
    """Parser for Boolean formulas."""

    def __init__(
            self,
            **kw
            ) -> None:
        self.tabmodule = _TRANSLATOR_CACHE
        super().__init__(**kw)
        self._reset_state()

    def parse(
            self,
            expression:
                str,
            bdd:
                _BDD[_Ref]
            ) -> _Ref:
        """Return BDD of `expression`.

        The returned BDD is stored in
        the BDD manager `bdd`.
        """
        self._bdd = bdd
        u = super().parse(expression)
        self._reset_state()
        return u

    def _reset_state(
            self
            ) -> None:
        """Set default attribute values."""
        self._bdd = None
        has_lr_stack = (
            self.parser is not None and
            hasattr(self.parser, 'statestack') and
            hasattr(self.parser, 'symstack'))
        if not has_lr_stack:
            return
        self.parser.restart()
            # Avoid references to BDD nodes
            # remaining in the LR stack,
            # because this side-effect would
            # change the reference-counts.

    def _add_bool(
            self,
            bool_literal:
                str):
        """Return BDD for Boolean values."""
        value = bool_literal.lower()
        if value not in {'false', 'true'}:
            raise ValueError(value)
        return getattr(self._bdd, value)

    def _add_int(
            self,
            numeric_literal:
                str):
        """Return BDD with given index."""
        number = int(numeric_literal)
        return self._bdd._add_int(number)

    def _add_var(
            self,
            name:
                str):
        """Return BDD for variable `name`."""
        return self._bdd.var(name)

    def _apply(
            self,
            operator:
                str,
            *operands:
                _ty.Any):
        """Return BDD from applying `operator`."""
        match operator:
            case r'\A' | r'\E':
                names, expr = operands
                names = {
                    x.value
                    for x in names}
                forall = (operator == r'\A')
                return self._bdd.quantify(
                    expr, names,
                    forall=forall)
            case r'\S':
                subs, expr = operands
                renaming = {
                    k.value: v.value
                    for k, v in subs}
                return self._bdd.rename(
                    expr, renaming)
        return self._bdd.apply(
            operator, *operands)


_parsers = dict()


def add_expr(
        expression:
            str,
        bdd:
            _BDD[_Ref]
        ) -> _Ref:
    """Return `bdd` node for `expression`.

    Creates in `bdd` a node that represents
    `expression`, and returns this node.
    """
    if 'boolean' not in _parsers:
        _parsers['boolean'] = _Translator()
    translator = _parsers['boolean']
    return translator.parse(expression, bdd)


def _rewrite_tables(
        outputdir:
            str='./'
        ) -> None:
    """Recache state machine of parser."""
    astutils.rewrite_tables(
        Parser, _TABMODULE, outputdir)
    astutils.rewrite_tables(
        _Translator, _TRANSLATOR_CACHE, outputdir)


def _main(
        ) -> None:
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
