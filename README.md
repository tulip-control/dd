[![Build Status][build_img]][travis]
[![Coverage Status][coverage]][coveralls]


About
=====

A pure-Python (2 and 3) package for manipulating:

- [Binary decision diagrams](https://en.wikipedia.org/wiki/Binary_decision_diagram) (BDDs).
- [Multi-valued decision diagrams](http://dx.doi.org/10.1109/ICCAD.1990.129849) (MDDs).

as well as [Cython](http://cython.org/) bindings to the C libraries:

- [CUDD](http://vlsi.colorado.edu/~fabio/CUDD/)
- [BuDDy](http://buddy.sourceforge.net)

These bindings expose almost identical interfaces as the Python implementation.
The intended workflow is:

- develop your algorithm in pure Python (easy to debug and introspect),
- use the bindings to benchmark and deploy

Your code remains the same.

An ordered BDD is represented using dictionaries for the successors,
unique table, and reference counts. Nodes are positive integers, and
edges signed integers. A complemented edge is represented as a negative integer.
Garbage collection uses reference counting.

Contains:

- All the standard functions defined, e.g.,
  by [Bryant](https://www.cs.cmu.edu/~bryant/pubdir/ieeetc86.pdf).
- [Rudell's sifting algorithm](http://www.eecg.toronto.edu/~ece1767/project/rud.pdf)
  for variable reordering.
- Reordering to obtain a given order.
- Quantified Boolean expression parser that creates BDD nodes.
- Pre/Image computation (relational product).
- Renaming variables to their neighbors.
- Conversion from BDDs to MDDs.
- Conversion functions to [`networkx`](https://networkx.github.io/) and
  [`pydot`](https://pypi.python.org/pypi/pydot) graphs.
- BDDs have methods to `dump` and `load` them as nested `dict`s using `pickle`.
- BDDs dumped by CUDD can be loaded using a
  [PLY](https://github.com/dabeaz/ply/)-based parser for the header, and
  a fast simple by-line parser for the main body of nodes.
- Cython bindings to CUDD
- Cython bindings to BuDDy


Documentation
=============

In the [Markdown](https://en.wikipedia.org/wiki/Markdown) file
[`doc.md`](https://github.com/johnyf/dd/blob/master/doc.md).


Examples
========

Two interfaces are available:

- convenience: the module
  [`dd.autoref`](https://github.com/johnyf/dd/blob/master/dd/autoref.py) wraps
  `dd.bdd` and takes care of reference counting,
  using [`__del__`](https://docs.python.org/2/reference/datamodel.html#object.__del__).

- "low level": the module
  [`dd.bdd`](https://github.com/johnyf/dd/blob/master/dd/bdd.py) requires that
  the user in/decrement the reference counters associated with nodes that
  are used outside of a `BDD`.


## Automated reference counting

The module `dd.autoref` wraps the pure-Python BDD implementation in `dd.bdd`.
A `Function` object wraps a node and decrements its reference count when
disposed by Python's garbage collector:

```python
from dd.autoref import BDD, Function

bdd = BDD()
[bdd.add_var(var) for var in ['x', 'y']
u = bdd.add_expr('x -> y')

# alternative
x = bdd.var('x')
not_x = ~ x
y = bdd.var('y')
v = not_x | y
assert u == v
```


## CUDD

The interface to CUDD in `dd.cudd` looks similar to `dd.autoref`,
including automated reference counting:

```python
from dd import cudd

bdd = cudd.BDD()
[bdd.add_var(var) for var in ['x', y'']]
u = bdd.add_expr('\E x, y: x & y')
assert u == bdd.true, u

# longer alternative
xy = bdd.add_expr('x & y')
u = bdd.exist(['x', 'y'], xy)
assert u == bdd.true, u
```


## Reference counting by the user

The pure-Python module `dd.bdd` can be used directly,
which allows access more extensive than `dd.autoref`.
The `n` variables in a `dd.bdd.BDD` are ordered
from `0` (top level) to `n-1` (bottom level).
The terminal node `1` is at level `n`.

```python
from dd.bdd import BDD

ordering = dict(x=0, y=1)
bdd = BDD(ordering)
bdd.add_var('z')
```

Boolean expressions can be added with the method `BDD.add_expr`:

```python
u = bdd.add_expr('x | y')
v = bdd.add_expr('!x | z')
w = bdd.apply('and', u, v)
w = bdd.apply('&', u, v)
r = bdd.apply('->', u, w)
```

Garbage collection is triggered either explicitly by the user, or
when invoking the reordering algorithm.
If we invoked garbage collection next,
then the nodes `u`, `v`, `w` would be deleted.
To prevent this from happening, their reference counts should be incremented.
For example, if we want to prevent `w` from being collected as garbage, then

```python
bdd.incref(w)
```

To decrement the reference count:

```python
bdd.decref(w)
```

The more useful functions in `dd.bdd` are:
`rename`, `image`, `preimage`, `reorder`, `to_nx`, `to_pydot`.

Use the method `BDD.dump` to write a `BDD` to a `pickle` file, and
`BDD.load` to load it back. A CUDD dddmp file can be loaded using
the function `dd.dddmp.load`.

Examples of how `dd` can be used to implement symbolic algorithms can be
found in the [`omega` package](https://github.com/johnyf/omega/blob/master/doc/doc.md).


Installation
============


## pure-Python

Recommended to use `pip`, because the latest version will install
dependencies before `dd`:

```shell
pip install dd
```

Otherwise:

```shell
python setup.py install
```

If you use the latter, remember to install `ply` before `dd`.
If `ply` is absent, then the parser tables will not be cached, affecting performance.
For graph layout with `pydot`,
[graphviz](http://graphviz.org/) needs to be installed.


## Cython bindings


### `dd` fetching CUDD

By default, the package installs only the Python modules.
You can select to install either or both Cython extensions by
the `setup.py` options `--cudd` and `--buddy`.

Pass `--fetch` to `setup.py` to tell it to download, unpack, and `make` CUDD.
If building from the repository, then first install `cython`.
For example:

```shell
pip install cython  # not needed if building from PyPI distro
python setup.py install --fetch --cudd
```

These options can be passed to `pip` too, using the
[`--install-option`](https://pip.pypa.io/en/latest/reference/pip_install.html#per-requirement-overrides)
in a requirements file, for example:

```
dd >= 0.1.1 --install-option="--fetch" --install-option="--cudd"
```

The command line behavior of `pip` [is currently different](https://github.com/pypa/pip/issues/1883), so

```shell
pip install --install-option="--fetch" dd
```

will propagate option `--fetch` to dependencies, and so raise an error.


### User fetching build dependencies

If you build and install CUDD or BuDDy yourself, then ensure that:

- the header files and libraries of either CUDD or BuDDy are present, and
- suitable compiler, include, linking, and library flags are passed,
either by setting [environment variables](https://en.wikipedia.org/wiki/Environment_variable)
prior to calling `pip`, or by editing the file [`download.py`](https://github.com/johnyf/dd/blob/master/download.py).


Tests
=====

Require [`nose`](https://pypi.python.org/pypi/nose) and the extras. Run with:

```shell
cd tests/
nosetests
```

If the extension module `dd.cudd` has not been compiled and installed,
then the CUDD tests will fail.


License
=======
[BSD-3](http://opensource.org/licenses/BSD-3-Clause), see file `LICENSE`.


[build_img]: https://travis-ci.org/johnyf/dd.svg?branch=master
[travis]: https://travis-ci.org/johnyf/dd
[coverage]: https://coveralls.io/repos/johnyf/dd/badge.svg?branch=master
[coveralls]: https://coveralls.io/r/johnyf/dd?branch=master
