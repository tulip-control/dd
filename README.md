[![Build Status][build_img]][travis]
[![Coverage Status][coverage]][coveralls]


About
=====

A pure-Python package for manipulating:

- [Binary decision diagrams](https://en.wikipedia.org/wiki/Binary_decision_diagram) (BDDs).
- [Multi-valued decision diagrams](http://dx.doi.org/10.1109/ICCAD.1990.129849) (MDDs).

as well as [Cython](http://cython.org/) bindings to the C libraries:

- [CUDD](http://vlsi.colorado.edu/~fabio/CUDD/)
- [BuDDy](http://buddy.sourceforge.net)

These bindings expose almost identical interfaces as the Python implementation. The intended workflow is:

- develop your algorithm in pure Python (easy to debug and introspect),
- use the bindings to benchmark and deploy

Your code remains the same.

An ordered BDD is represented using dictionaries for the successors, unique table, and reference counts. Nodes are positive integers, and edges signed integers. A complemented edge is represented as a negative integer. Garbage collection uses reference counting.

Contains:

- All the standard functions defined, e.g., by [Bryant](https://www.cs.cmu.edu/~bryant/pubdir/ieeetc86.pdf).
- [Rudell's sifting algorithm](http://www.eecg.toronto.edu/~ece1767/project/rud.pdf) for variable reordering.
- Reordering to obtain a given order.
- Quantified Boolean expression parser that creates BDD nodes.
- Pre/Image computation (relational product).
- Renaming variables to their neighbors.
- Conversion from BDDs to MDDs.
- Conversion functions to [`networkx`](https://networkx.github.io/) and [`pydot`](http://pypi.python.org/pydot) graphs.
- BDDs have methods to `dump` and `load` them as nested `dict`s using `pickle`.
- BDDs dumped by CUDD can be loaded using a [PLY](https://github.com/dabeaz/ply/)-based parser for the header, and a fast simple by-line parser for the main body of nodes.
- Cython bindings to CUDD
- Cython bindings to BuDDy


Examples
========
Two interfaces are available:

- "low level": requires that the user in/decrement the reference counters associated to nodes that they are using outside of a `BDD`
- convenience: the class `Function` wraps nodes and takes care of reference counting.

The `n` variables are ordered from `0` (top level) to `n-1` (bottom level). The terminal node `1` is at level `n`.

```python
from dd.bdd import BDD

ordering = {'x': 0, 'y': 1, 'z': 2}
bdd = BDD(ordering)
```

To add Boolean functions using the `BDD` interface directly (assuming the optional dependency `tulip` is present):

```python
u = bdd.add_expr('x | y')
v = bdd.add_expr('!x | z')
w = bdd.apply('and', u, v)
w = bdd.apply('&', u, v)
r = bdd.apply('->', u, w)
```

Garbage collection is triggered either explicitly by the user, or when invoking the reordering algorithm.
The nodes `u`, `v`, `w` will be deleted if next garbage collection is invoked. To prevent this from happening, their reference counts must be increased. For example, if we want to keep `w` from being collected as gargabe, then

```python
bdd.incref(w)
```

The absolute value is used, because `w` may be a negative integer representing a complemented edge that points to the node `abs(w)` that is present in `bdd`.
To decrement the reference count:

```python
bdd.decref(w)
```

`Function` objects can be used to avoid having to manually keep track of incrementing and decrementing the reference counts. Using `Function`s, the above becomes:

```python
from dd.bdd import Function

u = Function.from_expr('x & y', bdd)
v = Function.from_expr('(! x) | z', bdd)
w = u & y
```

The functions `rename`, `image`, `preimage`, `reorder`, `to_nx`, `to_pydot` in `dd.bdd` can be invoked to use the algorithms with the corresponding names.

Use the method `BDD.dump` to write a `BDD` to a `pickle` file, and `BDD.load` to load it back. A CUDD dddmp file can be loaded using the function `dd.dddmp.load`.


CUDD
----

Some elementary usage:

```python
from dd import cudd

bdd = cudd.BDD()
bdd.add_var('x')
x = bdd.var('x')
bdd.add_var('y')
xy = bdd.add_expr('x & y')
u = bdd.quantify(xy, {'x', 'y'}, forall=False)
assert u == bdd.True, u
```


Installation
============


pure-Python
-----------

Recommended to use `pip`, because the latest version will install dependencies first:

```shell
pip install dd
```

Otherwise:

```shell
python setup.py install
```

If you use the latter, remember to install `ply` before `dd`. If `ply` is absent, then the parser tables will not be cached. You can 

Optional: For graph layout, [`pydot`](http://pypi.python.org/pydot) and [graphviz](http://graphviz.org/) are required. Using `pip`, these can be installed as [extra](https://pip.pypa.io/en/latest/reference/pip_install.html#examples) called `dot`:

```shell
pip install dd[dot]
```


Cython bindings
---------------

By default, the package will try to compile the Cython bindings to CUDD. If it fails, then it installs the Python modules only. You can select either or both extensions by the `setup.py` options `--cudd` and `--buddy`.

Pass `--fetch` to `setup.py` to tell it to download, unpack, and `make` CUDD. For example:

```shell
python setup.py install --fetch
```

These options can be passed also to `pip`, via the [`--install-option`](https://pip.pypa.io/en/latest/reference/pip_install.html#cmdoption--install-option). For example,

```shell
pip install --install-option="--fetch"
```

Otherwise, ensure that:

- the header files and libraries of either CUDD or BuDDy are present, and
- suitable compiler, include, linking, and library flags are passed, either with an `export` prior to calling `pip`, or by editing the file `download.py`.


Tests
=====

Require `nose` and the extras. Run with:

```shell
cd tests/
nosetests
```


License
=======
[BSD-3](http://opensource.org/licenses/BSD-3-Clause), see `LICENSE` file.


[build_img]: https://travis-ci.org/johnyf/dd.svg?branch=master
[travis]: https://travis-ci.org/johnyf/dd
[coverage]: https://coveralls.io/repos/johnyf/dd/badge.svg?branch=master
[coveralls]: https://coveralls.io/r/johnyf/dd?branch=master