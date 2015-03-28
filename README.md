[![Build Status][build_img]][travis]
[![Coverage Status][coverage]][coveralls]


About
=====

A pure-Python package for manipulating decision diagrams, for now [binary decision diagrams](https://en.wikipedia.org/wiki/Binary_decision_diagram) (BDDs).

An ordered BDD is represented using dictionaries for the successors, unique table, and reference counts. Nodes are positive integers, and edges signed integers. A complemented edge is represented as a negative integer. Garbage collection uses reference counting.

All the standard functions defined, e.g., by [Bryant](https://www.cs.cmu.edu/~bryant/pubdir/ieeetc86.pdf) are supported, as well as [Rudell's sifting algorithm](http://www.eecg.toronto.edu/~ece1767/project/rud.pdf) for dynamic variable reordering.
Conversion functions to [`networkx`](https://networkx.github.io/) and [`pydot`](http://pypi.python.org/pydot) graphs are included. BDDs have methods to `dump` and `load` them as nested `dict`s using `pickle`.

BDDs dumped by [CUDD](http://vlsi.colorado.edu/~fabio/CUDD/) can be loaded using a [PLY](https://github.com/dabeaz/ply/)-based parser for the header, and a fast simple by-line parser for the main body of nodes.


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


Installation
============

Using `setuptools`:

```
python setup.py install
```

or using `pip >= 6.0.8`:

```
pip install dd
```

Two optional extras are available:

- `dot` for graph layout (requires [`pydot`](http://pypi.python.org/pydot) and [graphviz](http://graphviz.org/)).
- `nx` for conversion of BDDs to [`networkx`](https://github.com/networkx/networkx) graphs (requires `networkx`).

These can be [specified when installing with `pip`](https://pip.pypa.io/en/latest/reference/pip_install.html#examples) as, for example:

```
pip install dd[dot]
```

Successfully running the tests requires the above extra dependencies.


License
=======
[BSD-3](http://opensource.org/licenses/BSD-3-Clause), see `LICENSE` file.


[build_img]: https://travis-ci.org/johnyf/dd.svg?branch=master
[travis]: https://travis-ci.org/johnyf/dd
[coverage]: https://coveralls.io/repos/johnyf/dd/badge.svg?branch=master
[coveralls]: https://coveralls.io/r/johnyf/dd?branch=master