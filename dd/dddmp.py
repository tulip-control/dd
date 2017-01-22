"""Parser for DDDMP file format.

CUDD exports Binary Decision Diagrams (BDD) in DDDMP.
For more details on the Decision Diagram DuMP (DDDMP) package,
read the file [1] included in the CUDD distribution [2].
The text file format details can be found
by reading the source code [3].

For the `slugs` exporter, see [4].


References
==========

[1] Gianpiero Cabodi and Stefano Quer
    "DDDMP: Decision Diagram DuMP package"
    `cudd-X.Y.Z/dddmp/doc/dddmp-2.0-Letter.ps`, 2004

[2] http://vlsi.colorado.edu/~fabio/CUDD/

[3] `cudd-X.Y.Z/dddmp/dddmpStoreBdd.c`, lines: 329--331, 345, 954

[4] `src/BFAbstractionLibrary/BFCuddManager.cpp`
    method: `BFBddManager.writeBDDToFile`
"""
# Copyright 2014 by California Institute of Technology
# All rights reserved. Licensed under BSD-3.
#
import logging
import ply.lex
import ply.yacc
import astutils
from dd.bdd import BDD
from dd._compat import items


logger = logging.getLogger(__name__)
TABMODULE = 'dd.dddmp_parsetab'
LEX_LOG = 'dd.dddmp.lex_logger'
YACC_LOG = 'dd.dddmp.yacc_logger'
PARSER_LOG = 'dd.dddmp.parser_logger'


class Lexer(object):
    """Token rules to build LTL lexer."""

    reserved = {
        'ver': 'VERSION',
        'add': 'ADD',
        'mode': 'FILEMODE',
        'varinfo': 'VARINFO',
        'dd': 'DD',
        'nnodes': 'NNODES',
        'nvars': 'NVARS',
        'orderedvarnames': 'ORDEREDVARNAMES',
        'nsuppvars': 'NSUPPVARS',
        'suppvarnames': 'SUPPVARNAMES',
        'ids': 'IDS',
        'permids': 'PERMIDS',
        'auxids': 'AUXIDS',
        'nroots': 'NROOTS',
        'rootids': 'ROOTIDS',
        'rootnames': 'ROOTNAMES',
        # 'nodes': 'NODES',
        # 'end': 'END'
        }
    reserved = {'.{k}'.format(k=k): v for k, v in items(reserved)}
    misc = ['MINUS', 'DOT', 'NAME', 'NUMBER']
    # token rules
    t_MINUS = r'-'
    t_DOT = r'\.'
    t_NUMBER = r'\d+'
    t_ignore = ' \t'

    def __init__(self, debug=False):
        self.tokens = self.misc + list(self.reserved.values())
        self.build(debug=debug)

    def t_KEYWORD(self, t):
        r"\.[a-zA-Z][a-zA-Z]*"
        t.type = self.reserved.get(t.value, 'NAME')
        return t

    def t_NAME(self, t):
        r"[a-zA-Z_][a-zA-Z_@0-9\'\.]*"
        t.type = self.reserved.get(t.value, 'NAME')
        return t

    def t_comment(self, t):
        r'\#.*'
        return

    def t_newline(self, t):
        r'\n+'
        t.lexer.lineno += t.value.count("\n")

    def t_error(self, t):
        raise Exception('Illegal character "{t}"'.format(t=t.value[0]))

    def build(self, debug=False, debuglog=None, **kwargs):
        """Create a lexer.

        @param kwargs: Same arguments as C{{ply.lex.lex}}:

          - except for C{{module}} (fixed to C{{self}})
          - C{{debuglog}} defaults to the logger C{{"{logger}"}}.
        """
        if debug and debuglog is None:
            debuglog = logging.getLogger(LEX_LOG)
        self.lexer = ply.lex.lex(
            module=self,
            debug=debug,
            debuglog=debuglog,
            **kwargs)


class Parser(object):
    """Production rules to build LTL parser."""

    tabmodule = TABMODULE

    def __init__(self):
        self.lexer = Lexer()
        self.tokens = self.lexer.tokens
        self.build()
        self.reset()

    def build(self,
              tabmodule=None,
              outputdir=None,
              write_tables=False,
              debug=False,
              debuglog=None):
        if tabmodule is None:
            tabmodule = self.tabmodule
        self.lexer.build(debug=debug)
        self.parser = ply.yacc.yacc(
            module=self,
            start='file',
            tabmodule=tabmodule,
            outputdir=outputdir,
            write_tables=write_tables,
            debug=debug,
            debuglog=debuglog)

    def parse(self, filename, debuglog=None):
        """Parse DDDMP file containing BDD."""
        levels, roots = self._parse_header(filename, debuglog)
        self._parse_body(filename)
        return self.bdd, self.n_vars, levels, roots

    def _parse_header(self, filename, debuglog):
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
            lexer = self.lexer.lexer
            lexer.input(s)
            r = self.parser.parse(lexer=lexer, debug=debuglog)
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
        # ok ?
        if r is None:
            raise Exception('failed to parse')

        # support_var_ord_ids = {
        #     d['var_index'] for u, d in g.nodes_iter(data=True)}
        # assert len(support_var_ord_ids) == self.n_support_vars
        # prepare levels
        if self.ordered_vars is None:
            permid2var = {
                k: var for k, var in zip(self.permuted_var_ids,
                                         self.support_vars)}
            levels = {
                permid2var[k]: k for k in sorted(self.permuted_var_ids)}
        else:
            levels = {var: k for k, var in enumerate(self.ordered_vars)}
        roots = set(self.rootids)
        return levels, roots

    def _parse_body(self, filename):
        # parse nodes (large but very uniform)
        with open(filename, 'r') as f:
            for line in f:
                if '.nodes' in line:
                    break
            for line in f:
                if '.end' in line:
                    break
                try:
                    u, info, index, v, w = map(int, line.split(' '))
                except ValueError:
                    u, info, index, v, w = line.split(' ')
                    assert info == 'T', info
                    u, index, v, w = map(int, (u, index, v, w))
                self._add_node(u, info, index, v, w)
        assert len(self.bdd) == self.n_nodes

    def _add_node(self, u, info, index, v, w):
        """Add new node to BDD.

        @type u, index, v, w: `int`
        @type info: `int` or `"T"`
        """
        if v == 0:
            v = None
        else:
            assert v >= 0, 'only "else" edges can be complemented'
        if w == 0:
            w = None
        # map fixed var index to level among all vars
        level = self.info2permid[info]
        # dddmp stores (high, low)
        # swap to (low, high), as used in `dd.bdd`
        self.bdd[u] = (level, w, v)

    def reset(self):
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

    def _assert_consistent(self):
        """Check that the loaded attributes are reasonable."""
        assert len(self.support_vars) == self.n_support_vars
        if self.ordered_vars is not None:
            assert len(self.ordered_vars) == self.n_vars
        assert len(self.var_ids) == self.n_support_vars
        assert len(self.permuted_var_ids) == self.n_support_vars
        if self.aux_var_ids is not None:
            assert len(self.aux_var_ids) == self.n_support_vars
        assert len(self.rootids) == self.n_roots, self.rootids

    def p_file(self, p):
        """file : lines"""
        p[0] = True

    def p_lines_iter(self, p):
        """lines : lines line"""

    def p_lines_end(self, p):
        """lines : line"""

    def p_line(self, p):
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

    def p_version(self, p):
        """version : VERSION name MINUS number DOT number"""

    def p_text_mode(self, p):
        """mode : FILEMODE NAME"""
        f = p[2]
        if f == 'A':
            logger.debug('text mode')
        elif f == 'B':
            logger.debug('binary mode')
            raise Exception('This parser supports only text DDDMP format.')
        else:
            raise Exception('unknown DDDMP format: {f}'.format(f=f))

    def p_varinfo(self, p):
        """varinfo : VARINFO number"""
        self.var_extra_info = p[2]

    def p_dd_name(self, p):
        """diagram_name : DD name"""
        self.bdd_name = p[2]

    def p_num_nodes(self, p):
        """nnodes : NNODES number"""
        self.n_nodes = p[2]

    def p_num_vars(self, p):
        """nvars : NVARS number"""
        self.n_vars = p[2]

    def p_nsupport_vars(self, p):
        """nsupportvars : NSUPPVARS number"""
        self.n_support_vars = p[2]

    def p_support_varnames(self, p):
        """supportvars : SUPPVARNAMES varnames"""
        self.support_vars = p[2]

    def p_ordered_varnames(self, p):
        """orderedvars : ORDEREDVARNAMES varnames"""
        self.ordered_vars = p[2]

    def p_varnames_iter(self, p):
        """varnames : varnames varname"""
        p[1].append(p[2])
        p[0] = p[1]

    def p_varnames_end(self, p):
        """varnames : varname"""
        p[0] = [p[1]]

    def p_varname(self, p):
        """varname : name
                   | number
        """
        p[0] = p[1]

    def p_var_ids(self, p):
        """varids : IDS integers"""
        self.var_ids = p[2]

    def p_permuted_ids(self, p):
        """permids : PERMIDS integers"""
        self.permuted_var_ids = p[2]

    def p_aux_ids(self, p):
        """auxids : AUXIDS integers"""
        self.aux_var_ids = p[2]

    def p_integers_iter(self, p):
        """integers : integers number"""
        p[1].append(p[2])
        p[0] = p[1]

    def p_integers_end(self, p):
        """integers : number"""
        p[0] = [p[1]]

    def p_num_roots(self, p):
        """nroots : NROOTS number"""
        self.n_roots = p[2]

    def p_root_ids(self, p):
        """rootids : ROOTIDS integers"""
        self.rootids = p[2]

    def p_root_names(self, p):
        """rootnames : ROOTNAMES varnames"""
        raise NotImplementedError

    def p_algebraic_dd(self, p):
        """algdd : ADD"""
        self.algebraic_dd = True

    def p_number(self, p):
        """number : NUMBER"""
        p[0] = int(p[1])

    def p_neg_number(self, p):
        """number : MINUS NUMBER"""
        p[0] = -int(p[2])

    def p_expression_name(self, p):
        """name : NAME"""
        p[0] = p[1]

    def p_error(self, p):
        raise Exception('Syntax error at "{p}"'.format(p=p))


def load(fname):
    """Return a `BDD` loaded from DDDMP file `fname`.

    If no `.orderedvarnames` appear in the file,
    then `.suppvarnames` and `.permids` are used instead.
    In the second case, the variable levels contains blanks.
    To avoid blanks, the levels are re-indexed here.
    This has no effect if `.orderedvarnames` appears in the file.

    DDDMP files are dumped by [CUDD](http://vlsi.colorado.edu/~fabio/CUDD/).
    """
    parser = Parser()
    bdd_succ, n_vars, levels, roots = parser.parse(fname)
    # reindex to ensure no blanks
    perm = {k: var for var, k in items(levels)}
    perm = {i: perm[k] for i, k in enumerate(sorted(perm))}
    new_levels = {var: k for k, var in items(perm)}
    old2new = {levels[var]: new_levels[var] for var in levels}
    # convert
    bdd = BDD(new_levels)
    umap = {-1: -1, 1: 1}
    for j in range(len(new_levels) - 1, -1, -1):
        for u, (k, v, w) in items(bdd_succ):
            # terminal ?
            if v is None:
                assert w is None, w
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


def _rewrite_tables(outputdir='./'):
    """Write the parser table file, even if it exists."""
    astutils.rewrite_tables(Parser, TABMODULE, outputdir)


if __name__ == '__main__':
    _rewrite_tables()
