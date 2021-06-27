"""Tests of the module `dd.cudd_zdd`."""
import inspect
import os
import subprocess
import sys

from dd import cudd
from dd import cudd_zdd
from dd import _copy
import pytest

import common
import common_cudd


class Tests(common.Tests):
    def setup_method(self):
        self.DD = cudd_zdd.ZDD


class CuddTests(common_cudd.Tests):
    def setup_method(self):
        self.DD = cudd_zdd.ZDD
        self.MODULE = cudd_zdd


def test_str():
    bdd =  cudd_zdd.ZDD()
    with pytest.warns(UserWarning):
        s = str(bdd)
    s + 'must be a string'


def test_false():
    zdd = cudd_zdd.ZDD()
    u = zdd.false
    assert len(u) == 0, len(u)


def test_true():
    zdd = cudd_zdd.ZDD()
    zdd.declare('x', 'y', 'z', 'w')
    u = zdd.true
    assert u.low is not None
    assert u.high is not None
    assert len(u) == 4, len(u)


def test_true_node():
    zdd = cudd_zdd.ZDD()
    zdd.declare('x', 'y')
    u = zdd.true_node
    assert u.low is None
    assert u.high is None
    assert len(u) == 0, len(u)


def test_index_at_level():
    zdd = cudd_zdd.ZDD()
    zdd.add_var('x', 1)
    level = zdd.level_of_var('x')
    assert level == 1, (
        level, zdd.index_of_var, zdd.vars)
    level_to_index = {
        -20: None,
        -1: None,
        0: 0,
        1: 1,
        2: None,
        3: None,
        100: None}
    for level, index_ in level_to_index.items():
        index = zdd._index_at_level(level)
        assert index == index_, (
            level, index, index_,
            zdd.index_of_var, zdd.vars)
    # no `dd.cudd_zdd.ZDD` variable declared at level 0
    # CUDD indices range from 0 to 1
    with pytest.raises(ValueError):
        zdd.level_of_var(0)
    # no CUDD variable at level 2
    with pytest.raises(ValueError):
        zdd.level_of_var(2)


def test_var_level_gaps():
    zdd = cudd_zdd.ZDD()
    zdd.add_var('x', 2)
    n_vars = len(zdd.vars)
    assert n_vars == 1, n_vars
    max_var_level = _max_var_level(zdd)
    assert max_var_level == 2, max_var_level


def _max_var_level(zdd):
    """Return the maximum level in `zdd`.

    The indices of variables in CUDD can span more
    levels than the variables declared in `zdd`.
    This happens when declaring variables with
    noncontiguous levels, using `ZDD.add_var()`.

    Nonetheless, `ZDD.add_var()` ensures that there
    exists a variable in `ZDD.vars` whose level equals
    the maximum level over CUDD indices.
    """
    if not zdd.vars:
        return None
    return max(
        zdd.level_of_var(var)
        for var in zdd.vars)


def test_gt_var_levels():
    zdd = cudd_zdd.ZDD()
    zdd.add_var('x', 1)
    level_to_value = {
        0: False,
        1: False,
        2: True,
        3: True,
        100: True}
    for level, value_ in level_to_value.items():
        value = zdd._gt_var_levels(level)
        assert value == value_, (
            level, value, value_,
            zdd.index_of_var, zdd.vars)
    with pytest.raises(ValueError):
        zdd._gt_var_levels(-1)


def test_number_of_cudd_vars_without_gaps():
    zdd = cudd_zdd.ZDD()
    # no variables
    _assert_n_vars_max_level(0, 0, None, zdd)
    # 1 declared variable
    # 1 variable index in CUDD
    zdd.declare('x')
    _assert_n_vars_max_level(1, 1, 0, zdd)
    # 2 declared variables
    # 2 variable indices in CUDD
    zdd.declare('y')
    _assert_n_vars_max_level(2, 2, 1, zdd)


def test_number_of_cudd_vars_with_gaps():
    zdd = cudd_zdd.ZDD()
    # no variables
    _assert_n_vars_max_level(0, 0, None, zdd)
    # 1 declared variable
    # 2 variable indices in CUDD
    zdd.add_var('x', 1)
    _assert_n_vars_max_level(2, 1, 1, zdd)
    # 2 declared variables
    # 15 variable indices in CUDD
    zdd.add_var('y', 14)
    _assert_n_vars_max_level(15, 2, 14, zdd)


def _assert_n_vars_max_level(
        n_cudd_vars:
            int,
        n_zdd_vars:
            int,
        max_var_level:
            int,
        zdd):
    n_cudd_vars_ = zdd._number_of_cudd_vars()
    assert n_cudd_vars_ == n_cudd_vars, (
        n_cudd_vars_, n_cudd_vars)
    n_zdd_vars_ = len(zdd.vars)
    assert n_zdd_vars_ == n_zdd_vars, (
        zdd.vars, n_zdd_vars)
    max_var_level_ = _max_var_level(zdd)
    assert max_var_level_ == max_var_level, (
        max_var_level_, max_var_level)


def test_var():
    zdd = cudd_zdd.ZDD()
    zdd.declare('x', 'y', 'z')
    x = zdd.var('x')
    x_ = zdd._var_cudd('x')
    assert x == x_, len(x)
    y = zdd.var('y')
    y_ = zdd._var_cudd('y')
    assert y == y_, len(y)
    z = zdd.var('z')
    z_ = zdd._var_cudd('z')
    assert z == z_, len(z)


def test_support_cudd():
    # support implemented by CUDD
    zdd = cudd_zdd.ZDD()
    zdd.declare('x', 'y')
    zdd._add_bdd_var(0)
    zdd._add_bdd_var(1)
    u = zdd.add_expr('~ x')
    s = zdd._support_cudd(u)
    assert s == {'y'}, s  # `{'x'}` is expected


def test_cudd_cofactor():
    zdd = cudd_zdd.ZDD()
    zdd.declare('x', 'y')
    u = zdd.add_expr(r'x /\ ~ y')
    r = zdd._cofactor_cudd(u, 'y', False)
    r_ = zdd.add_expr(r'x /\ ~ y')
    assert r == r_, len(r)
    u = zdd.add_expr(r'x /\ y')
    r = zdd._cofactor_cudd(u, 'x', True)
    r_ = zdd.add_expr(r'~ x /\ y')  # no node at x
    assert r == r_


def test_find_or_add():
    bdd = cudd_zdd.ZDD()
    bdd.declare('x', 'y', 'z')
    v = bdd.add_expr(r'~ x /\ y /\ ~ z')
    w = bdd.add_expr(r'~ x /\ ~ y /\ z')
    u = bdd.find_or_add('x', v, w)
    assert u.low == v, len(u)
    assert u.high == w, len(u)
    assert u.var == 'x', u.var
    assert u.level == 0, u.level


def test_count():
    zdd = cudd_zdd.ZDD()
    zdd.declare('x', 'y')
    # FALSE
    u = zdd.false
    n = zdd.count(u, 2)
    assert n == 0, n
    # TRUE
    u = zdd.true
    n = zdd.count(u, 1)
    assert n == 2, n
    n = zdd.count(u, 2)
    assert n == 4, n


def test_bdd_to_zdd_copy():
    zdd = cudd_zdd.ZDD()
    zdd.declare('x', 'y', 'z')
    bdd = cudd.BDD()
    bdd.declare('x', 'y', 'z')
    u = bdd.add_expr('x')
    v = bdd.copy(u, zdd)
    x = zdd.var('x')
    assert v == x, len(v)
    print_size(v, 'v')
    # copy `y`
    u = bdd.var('y')
    y = bdd.copy(u, zdd)
    y_ = zdd.var('y')
    assert y == y_, (y, y_)


def test_len():
    zdd = cudd_zdd.ZDD()
    zdd.declare('x', 'y', 'z')
    # x
    x = zdd.var('x')
    assert len(x) == 3, len(x)
    # y
    y = zdd.var('y')
    assert len(y) == 3, len(y)
    # x /\ y /\ ~ z
    u = x & y & ~ zdd.var('z')
    assert len(u) == 2, len(u)
    # ~ x
    u = zdd.add_expr('~ x')
    assert len(u) == 2, len(u)


def test_ith_var_without_gaps():
    zdd = cudd_zdd.ZDD()
    zdd.declare('x', 'y', 'z')
    u = cudd_zdd._ith_var('x', zdd)
    # check ZDD for variable x
    assert u.var == 'x', u.var
    assert u.level == 0, u.level
    assert u.low == zdd.false, (
        u, u.low, zdd.false)
    v = u.high
    assert v.var == 'y', v.var
    assert v.level == 1, v.level
    assert v.low == v.high, (
        v, v.low, v.high)
    w = v.low
    assert w.var == 'z'
    assert w.level == 2, w.level
    assert w.low == w.high, (
        w, w.low, w.high)
    assert w.low == zdd.true_node, (
        w, w.low, zdd.true_node)
    # check ZDD for variable y
    u = cudd_zdd._ith_var('y', zdd)
    assert u.var == 'x', u.var
    assert u.level == 0, u.level
    assert u.low == u.high, (
        u, u.low, u.high)
    v = u.low
    assert v.var == 'y', v.var
    assert v.level == 1, v.level
    assert v.low == zdd.false, (
        v, v.low, zdd.false)
    w = v.high
    assert w.var == 'z', w.var
    assert w.level == 2, w.level
    assert w.low == w.high, (
        w, w.low, w.high)
    assert w.low == zdd.true_node, (
        w, w.low, zdd.true_node)
    # check ZDD for variable z
    u = cudd_zdd._ith_var('z', zdd)
    assert u.var == 'x', u.var
    assert u.level == 0, u.level
    assert u.low == u.high, (
        u, u.low, u.high)
    v = u.low
    assert v.var == 'y', v.var
    assert v.level == 1, v.level
    assert v.low == v.high, (
        v, v.low, v.high)
    w = v.low
    assert w.var == 'z', w.var
    assert w.level == 2, w.level
    assert w.low == zdd.false, (
        w, w.low, zdd.false)
    assert w.high == zdd.true_node, (
        w, w.high, zdd.true_node)


def test_ith_var_with_gaps():
    zdd = cudd_zdd.ZDD()
    zdd.add_var('x', 1)
    with pytest.raises(AssertionError):
        # because 1 declared variable,
        # but 2 CUDD variable indices
        cudd_zdd._ith_var('x', zdd)
    zdd.vars.update(dict(y=0, z=3))
    with pytest.raises(AssertionError):
        cudd_zdd._ith_var('x', zdd)


def test_disjunction():
    zdd = cudd_zdd.ZDD()
    zdd.declare('w', 'x', 'y')
    # x \/ TRUE
    v = zdd.add_expr('x')
    w = zdd.true
    u = zdd._disjoin_root(v, w)
    assert u == w, len(u)
    # x \/ FALSE
    w = zdd.false
    u = zdd._disjoin_root(v, w)
    assert u == v, len(u)
    # x \/ y
    v = zdd.add_expr('x')
    w = zdd.add_expr('y')
    u = zdd._disjoin_root(v, w)
    u_ = zdd.add_expr(r'x \/ y')
    assert u == u_, len(u)
    # (~ w /\ x) \/ y
    v = zdd.add_expr(r'~ w /\ x')
    w = zdd.add_expr('y')
    u = zdd._disjoin_root(v, w)
    u_ = zdd.add_expr(r'(~ w /\ x) \/ y')
    assert u == u_, len(u)


def test_conjunction():
    zdd = cudd_zdd.ZDD()
    zdd.declare('x', 'y', 'z')
    v = zdd.var('x')
    w = zdd.var('y')
    u = zdd._conjoin_root(v, w)
    u_ = zdd.add_expr(r'x /\ y')
    assert u == u_, len(u)
    u = zdd._conjoin_root(v, ~ w)
    u_ = zdd.add_expr(r'x /\ ~ y')
    assert u == u_, len(u)


def test_methods_disjoin_conjoin_gaps_opt():
    run_python_with_optimization(
        test_methods_disjoin_conjoin_gaps)


def test_methods_disjoin_conjoin_gaps():
    import dd.cudd_zdd as _zdd
    import pytest
    zdd = _zdd.ZDD()
    zdd.add_var('x', 20)
    u = zdd.find_or_add(
        'x', zdd.false, zdd.true_node)
    level = 1
    with pytest.raises(ValueError):
        _zdd._call_method_disjoin(
            zdd, level, u, ~ u, cache=dict())
    with pytest.raises(ValueError):
        _zdd._call_method_conjoin(
            zdd, level, ~ u, u, cache=dict())


def test_method_disjoin():
    zdd = cudd_zdd.ZDD()
    zdd.declare('x')
    v = zdd.var('x')
    level = 1
    with pytest.raises(ValueError):
        cudd_zdd._call_method_disjoin(
            zdd, level, v, v, dict())


def test_methods_disjoin_conjoin_with_opt():
    run_python_with_optimization(
        test_methods_disjoin_conjoin)


def test_methods_disjoin_conjoin():
    import dd.cudd_zdd as _zdd
    import pytest
    zdd = _zdd.ZDD()
    zdd.declare('x')
    v = zdd.var('x')
    true = zdd.true_node
    level = 1
    with pytest.raises(ValueError):
        _zdd._call_method_disjoin(
            zdd, level, v, true, dict())
    with pytest.raises(ValueError):
        _zdd._call_method_conjoin(
            zdd, level, v, true, dict())
    with pytest.raises(ValueError):
        _zdd._call_method_conjoin(
            zdd, level, v, ~ v, dict())


def run_python_with_optimization(
        function):
    """Run `function` with `python -O`.

    Start new `python` process
    because Python's optimization level
    cannot be changed at runtime.
    """
    name = function.__name__
    function_src = inspect.getsource(function)
    assertion_src = inspect.getsource(_assert)
    src = f'{function_src}\n{assertion_src}\n{name}()'
    assert sys.executable, sys.executable
    cmd = [
        sys.executable,
        '-O', '-c',
        src]
    proc = subprocess.run(
        cmd, capture_output=True, text=True)
    if proc.returncode == 0:
        return
    raise AssertionError(
        f'The function `{name}`, when run with '
        f'`{cmd[:-1]}`, resulted in exiting with '
        f'return code {proc.returncode}.\n'
        f'The `stdout` was:\n{proc.stdout}\n'
        f'The `stderr` was:\n{proc.stderr}')


def _assert(test):
    if test:
        return
    raise AssertionError(test)


def test_c_disjunction():
    zdd = cudd_zdd.ZDD()
    zdd.declare('w', 'x', 'y')
    v = zdd.add_expr(r'~ w /\ x')
    w = zdd.add_expr('y')
    u = cudd_zdd._c_disjoin(v, w)
    u_ = zdd.add_expr(r'(~ w /\ x) \/ y')
    assert u == u_, len(u)


def test_c_conjunction():
    zdd = cudd_zdd.ZDD()
    zdd.declare('x', 'y', 'z')
    x = zdd.var('x')
    y = zdd.var('y')
    u = cudd_zdd._c_conjoin(x, y)
    u_ = zdd.add_expr(r'x /\ y')
    assert u == u_, len(u)


def test_c_exist():
    zdd = cudd_zdd.ZDD()
    zdd.declare('x', 'y', 'z')
    # \E x:  (x /\ ~ y) \/ ~ z
    u = zdd.add_expr(r'(x /\ ~ y) \/ ~ z')
    qvars = ['x']
    r = cudd_zdd._c_exist(qvars, u)
    r_ = zdd.exist(qvars, u)
    assert r == r_, len(r)
    # \E x:  x
    u = zdd.add_expr('x')
    qvars = ['x']
    r = cudd_zdd._c_exist(qvars, u)
    r_ = zdd.exist(qvars, u)
    assert r == r_, len(r)


def test_dump():
    zdd = cudd_zdd.ZDD()
    zdd.declare('x', 'y', 'w')
    u = zdd.add_expr('~ w')
    fname = 'not_w.pdf'
    if os.path.isfile(fname):
        os.remove(fname)
    assert not os.path.isfile(fname)
    zdd.dump(fname, [u])
    assert os.path.isfile(fname)


def test_dict_to_zdd():
    zdd = cudd_zdd.ZDD()
    zdd.declare('x', 'y', 'z')
    qvars = {'x', 'z'}
    u = cudd_zdd._dict_to_zdd(qvars, zdd)
    assert len(u) == 2, len(u)
    assert u.var == 'x', u.var
    assert u.low == u.high
    v = u.low
    assert v.var == 'z', v.var
    assert v.low == v.high
    assert v.low == zdd.true_node


def print_size(u, msg):
    n = len(u)
    print('Dag size of {msg}: {n}'.format(
        msg=msg, n=n))


if __name__ == '__main__':
    Tests().test_support()
    # test_compose()
