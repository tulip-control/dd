"""Parser for DDDMP file format.

CUDD exports Binary Decision Diagrams (BDD) in DDDMP.
For more details on the Decision Diagram DuMP (DDDMP) package,
read the file [1] included in the CUDD distribution [2].
The text file format details can be found
by reading the source code [3].


References
==========

[1] Gianpiero Cabodi and Stefano Quer
    "DDDMP: Decision Diagram DuMP package"
    `cudd-X.Y.Z/dddmp/doc/dddmp-2.0-Letter.ps`, 2004

[2] <http://vlsi.colorado.edu/~fabio/CUDD/>

[3] `cudd-X.Y.Z/dddmp/dddmpStoreBdd.c`, lines: 329--331, 345, 954
"""
# Copyright 2014 by California Institute of Technology
# All rights reserved. Licensed under BSD-3.
#
import logging
import typing as _ty

import astutils
import ply.lex
import ply.yacc

import dd.bdd as _bdd


logger = logging.getLogger(__name__)
TABMODULE: _ty.Final = 'dd._dddmp_parser_state_machine'
LEX_LOG: _ty.Final = 'dd.dddmp.lex_logger'
YACC_LOG: _ty.Final = 'dd.dddmp.yacc_logger'
PARSER_LOG: _ty.Final = 'dd.dddmp.parser_logger'


class Lexer:
    """Token rules to build LTL lexer."""

    def __init__(
            self,
            debug=False):
        reserved = {
            'ver':
                'VERSION',
            'add':
                'ADD',
            'mode':
                'FILEMODE',
            'varinfo':
                'VARINFO',
            'dd':
                'DD',
            'nnodes':
                'NNODES',
            'nvars':
                'NVARS',
            'orderedvarnames':
                'ORDEREDVARNAMES',
            'nsuppvars':
                'NSUPPVARS',
            'suppvarnames':
                'SUPPVARNAMES',
            'ids':
                'IDS',
            'permids':
                'PERMIDS',
            'auxids':
                'AUXIDS',
            'nroots':
                'NROOTS',
            'rootids':
                'ROOTIDS',
            'rootnames':
                'ROOTNAMES',
            # 'nodes':
            #     'NODES',
            # 'end':
            #     'END'
            }
        self.reserved = {
            f'.{k}': v
            for k, v in reserved.items()}
        self.misc = [
            'MINUS',
            'DOT',
            'NAME',
            'NUMBER']
        self.tokens = self.misc + list(
            sorted(self.reserved.values()))
        self.build(debug=debug)

    # token rules
    t_MINUS = r' \- '
    t_DOT = r' \. '
    t_NUMBER = r' \d+ '
    t_ignore = ''.join(['\x20', '\t'])

    def t_KEYWORD(
            self, t):
        r"""
        \.
        [a-zA-Z]
        [a-zA-Z]*
        """
        t.type = self.reserved.get(t.value, 'NAME')
        return t

    def t_NAME(
            self, t):
        r"""
        [a-zA-Z_]
        [a-zA-Z_@0-9'\.]*
        """
        t.type = self.reserved.get(t.value, 'NAME')
        return t

    def t_comment(
            self, t):
        r' \# .* '
        return

    def t_newline(
            self, t):
        r' \n+ '

    def t_error(
            self,
            token):
        raise ValueError(
            f'Unexpected character "{token.value[0]}"')

    def build(
            self,
            debug=False,
            debuglog=None,
            **kwargs):
        """Create a lexer.

        @param kwargs:
            Same arguments as `ply.lex.lex`:

            - except for `module` (fixed to `self`)
            - `debuglog` defaults to `logger`.
        """
        if debug and debuglog is None:
            debuglog = logging.getLogger(LEX_LOG)
        self.lexer = ply.lex.lex(
            module=self,
            debug=debug,
            debuglog=debuglog,
            **kwargs)


class Parser:
    """Production rules to build LTL parser."""

    def __init__(
            self):
        self.tabmodule = TABMODULE
        self._lexer = Lexer()
        self.tokens = self._lexer.tokens
        self.reset()
        self.parser = None

    def build(
            self,
            tabmodule=None,
            outputdir=None,
            write_tables=False,
            debug=False,
            debuglog=None):
        if tabmodule is None:
            tabmodule = self.tabmodule
        if debug and debuglog is None:
            debuglog = logger
        self._lexer.build(debug=debug)
        self.parser = ply.yacc.yacc(
            module=self,
            start='file',
            tabmodule=tabmodule,
            outputdir=outputdir,
            write_tables=write_tables,
            debug=debug,
            debuglog=debuglog)

    def parse(
            self,
            filename,
            debuglog=None):
        """Parse DDDMP file containing BDD."""
        if self.parser is None:
            self.build()
        levels, roots = self._parse_header(filename, debuglog)
        self._parse_body(filename)
        return self.bdd, self.n_vars, levels, roots

    def _parse_header(
            self,
            filename,
            debuglog):
        self.reset()
        if debuglog is None:
            debuglog = logging.getLogger(PARSER_LOG)
        # parse header (small but inhomogeneous)
        with open(filename, 'r') as f:
            a = list()
            for line in f:
                if '.nodes' in line:
                    break
                a.append(line)
            s = '\n'.join(a)
            lexer = self._lexer.lexer
            lexer.input(s)
            r = self.parser.parse(lexer=lexer, debug=debuglog)
        if r is None:
            raise Exception('failed to parse')
        self._assert_consistent()
        # prepare mapping from fixed var index to level among all vars
        # id2name = {
        #     i: var
        #     for i, var in zip(self.var_ids, self.support_vars)}
        c = self.var_extra_info
        if c == 0:
            logger.info('var IDs')
            id2permid = {
                i: k
                for i, k in zip(self.var_ids, self.permuted_var_ids)}
            self.info2permid = id2permid
        elif c == 1:
            logger.info('perm IDs')
            self.info2permid = {k: k for k in self.permuted_var_ids}
        elif c == 2:
            logger.info('aux IDs')
            raise NotImplementedError
        elif c == 3:
            logger.info('var names')
            self.info2permid = {
                var: k for k, var in enumerate(self.ordered_vars)}
        elif c == 4:
            logger.info('none')
            raise NotImplementedError
        else:
            raise Exception('unknown `varinfo` case')
        self.info2permid['T'] = self.n_vars + 1
        # support_var_ord_ids = {
        #     d['var_index'] for u, d in g.nodes(data=True)}
        # if len(support_var_ord_ids) != self.n_support_vars:
        #     raise AssertionError((
        #         support_var_ord_ids, self.n_support_vars))
        # prepare levels
        if self.ordered_vars is not None:
            levels = {var: k for k, var in enumerate(self.ordered_vars)}
        elif self.support_vars is not None:
            permid2var = {
                k: var for k, var in zip(self.permuted_var_ids,
                                         self.support_vars)}
            levels = {
                permid2var[k]: k for k in sorted(self.permuted_var_ids)}
        else:
            levels = {
                idx: level for level, idx in
                enumerate(self.permuted_var_ids)}
        roots = set(self.rootids)
        return levels, roots

    def _parse_body(
            self,
            filename):
        # parse nodes (large but very uniform)
        with open(filename, 'r') as f:
            for line in f:
                if '.nodes' in line:
                    break
            for line in f:
                if '.end' in line:
                    break
                u, info, index, v, w = line.split(' ')
                u, index, v, w = map(int, (u, index, v, w))
                try:
                    info = int(info)
                except ValueError:
                    pass  # info == 'T' or `str` var name
                if info not in self.info2permid:
                    raise AssertionError(
                        (info, self.info2permid))
                self._add_node(u, info, index, v, w)
        if len(self.bdd) != self.n_nodes:
            raise AssertionError((len(self.bdd), self.n_nodes))

    def _add_node(
            self,
            u,
            info,
            index,
            v,
            w):
        """Add new node to BDD.

        @type u, index, v, w:
            `int`
        @type info:
            `int` or `"T"`
        """
        if v == 0:
            v = None
        elif v < 0:
            raise ValueError(
                'only "else" edges '
                f'can be complemented ({v = })')
        if w == 0:
            w = None
        # map fixed var index to level among all vars
        level = self.info2permid[info]
        # dddmp stores (high, low)
        # swap to (low, high), as used in `dd.bdd`
        self.bdd[u] = (level, w, v)

    def reset(
            self):
        self.bdd = dict()
        self.algebraic_dd = None
        self.var_extra_info = None
        self.n_nodes = None
        self.rootids = None
        self.n_roots = None
        # vars
        self.n_vars = None
        self.ordered_vars = None
        # support vars
        self.n_support_vars = None
        self.support_vars = None
        # permuted and aux vars
        self.var_ids = None
        self.permuted_var_ids = None
        self.aux_var_ids = None
        self.info2permid = None

    def _assert_consistent(
            self):
        """Check that the loaded attributes are reasonable."""
        if self.support_vars is not None:
            if len(self.support_vars) != self.n_support_vars:
                raise AssertionError((
                    len(self.support_vars),
                    self.n_support_vars,
                    self.support_vars))
        if self.ordered_vars is not None:
            if len(self.ordered_vars) != self.n_vars:
                raise AssertionError((
                    len(self.ordered_vars),
                    self.n_vars,
                    self.ordered_vars))
        if len(self.var_ids) != self.n_support_vars:
            raise AssertionError((
                len(self.var_ids),
                self.n_support_vars,
                self.var_ids))
        if len(self.permuted_var_ids) != self.n_support_vars:
            raise AssertionError((
                len(self.permuted_var_ids),
                self.n_support_vars,
                self.permuted_var_ids))
        if self.aux_var_ids is not None:
            if len(self.aux_var_ids) != self.n_support_vars:
                raise AssertionError((
                    len(self.aux_var_ids),
                    self.n_support_vars,
                    self.aux_var_ids))
        if len(self.rootids) != self.n_roots:
            raise AssertionError((
                len(self.rootids),
                self.n_roots,
                self.rootids))

    def p_file(
            self, p):
        """file : lines"""
        p[0] = True

    def p_lines_iter(
            self, p):
        """lines : lines line"""

    def p_lines_end(
            self, p):
        """lines : line"""

    def p_line(
            self, p):
        """line : version
                | mode
                | varinfo
                | diagram_name
                | nnodes
                | nvars
                | nsupportvars
                | supportvars
                | orderedvars
                | varids
                | permids
                | auxids
                | nroots
                | rootids
                | algdd
                | rootnames
        """

    def p_version(
            self, p):
        """version : VERSION name MINUS number DOT number"""

    def p_text_mode(
            self, p):
        """mode : FILEMODE NAME"""
        f = p[2]
        if f == 'A':
            logger.debug('text mode')
        elif f == 'B':
            logger.debug('binary mode')
            raise Exception('This parser supports only text DDDMP format.')
        else:
            raise Exception(f'unknown DDDMP format: {f}')

    def p_varinfo(
            self, p):
        """varinfo : VARINFO number"""
        self.var_extra_info = p[2]

    def p_dd_name(
            self, p):
        """diagram_name : DD name"""
        self.bdd_name = p[2]

    def p_num_nodes(
            self, p):
        """nnodes : NNODES number"""
        self.n_nodes = p[2]

    def p_num_vars(
            self, p):
        """nvars : NVARS number"""
        self.n_vars = p[2]

    def p_nsupport_vars(
            self, p):
        """nsupportvars : NSUPPVARS number"""
        self.n_support_vars = p[2]

    def p_support_varnames(
            self, p):
        """supportvars : SUPPVARNAMES varnames"""
        self.support_vars = p[2]

    def p_ordered_varnames(
            self, p):
        """orderedvars : ORDEREDVARNAMES varnames"""
        self.ordered_vars = p[2]

    def p_varnames_iter(
            self, p):
        """varnames : varnames varname"""
        p[1].append(p[2])
        p[0] = p[1]

    def p_varnames_end(
            self, p):
        """varnames : varname"""
        p[0] = [p[1]]

    def p_varname(
            self, p):
        """varname : name
                   | number
        """
        p[0] = p[1]

    def p_var_ids(
            self, p):
        """varids : IDS integers"""
        self.var_ids = p[2]

    def p_permuted_ids(
            self, p):
        """permids : PERMIDS integers"""
        self.permuted_var_ids = p[2]

    def p_aux_ids(
            self, p):
        """auxids : AUXIDS integers"""
        self.aux_var_ids = p[2]

    def p_integers_iter(
            self, p):
        """integers : integers number"""
        p[1].append(p[2])
        p[0] = p[1]

    def p_integers_end(
            self, p):
        """integers : number"""
        p[0] = [p[1]]

    def p_num_roots(
            self, p):
        """nroots : NROOTS number"""
        self.n_roots = p[2]

    def p_root_ids(
            self, p):
        """rootids : ROOTIDS integers"""
        self.rootids = p[2]

    def p_root_names(
            self, p):
        """rootnames : ROOTNAMES varnames"""
        raise NotImplementedError

    def p_algebraic_dd(
            self, p):
        """algdd : ADD"""
        self.algebraic_dd = True

    def p_number(
            self, p):
        """number : NUMBER"""
        p[0] = int(p[1])

    def p_neg_number(
            self, p):
        """number : MINUS NUMBER"""
        p[0] = -int(p[2])

    def p_expression_name(
            self, p):
        """name : NAME"""
        p[0] = p[1]

    def p_error(
            self, p):
        raise Exception(f'Syntax error at "{p}"')


def load(
        fname:
            str
        ) -> _bdd.BDD:
    """Return a `BDD` loaded from DDDMP file `fname`.

    If no `.orderedvarnames` appear in the file,
    then `.suppvarnames` and `.permids` are used instead.
    In the second case, the variable levels contains blanks.
    To avoid blanks, the levels are re-indexed here.
    This has no effect if `.orderedvarnames` appears in the file.

    DDDMP files are dumped by [CUDD](
        http://vlsi.colorado.edu/~fabio/CUDD/).
    """
    parser = Parser()
    bdd_succ, n_vars, levels, roots = parser.parse(fname)
    # reindex to ensure no blanks
    perm = {k: var for var, k in levels.items()}
    perm = {i: perm[k] for i, k in enumerate(sorted(perm))}
    new_levels = {var: k for k, var in perm.items()}
    old2new = {levels[var]: new_levels[var] for var in levels}
    # convert
    bdd = _bdd.BDD(new_levels)
    umap = {-1: -1, 1: 1}
    for j in range(len(new_levels) - 1, -1, -1):
        for u, (k, v, w) in bdd_succ.items():
            # terminal ?
            if v is None:
                if w is not None:
                    raise AssertionError(w)
                continue
            # non-terminal
            i = old2new[k]
            if i != j:
                continue
            p, q = umap[abs(v)], umap[w]
            if v < 0:
                p = -p
            r = bdd.find_or_add(i, p, q)
            umap[abs(u)] = r
    bdd.roots.update(roots)
    return bdd


def _rewrite_tables(
        outputdir:
            str='./'
        ) -> None:
    """Write the parser table file, even if it exists."""
    astutils.rewrite_tables(Parser, TABMODULE, outputdir)


if __name__ == '__main__':
    _rewrite_tables()
