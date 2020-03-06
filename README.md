[![Build Status][build_img]][travis]
[![Coverage Status][coverage]][coveralls]


About
=====

A pure-Python (3 and 2) package for manipulating:

- [Binary decision diagrams](https://en.wikipedia.org/wiki/Binary_decision_diagram) (BDDs).
- [Multi-valued decision diagrams](http://dx.doi.org/10.1109/ICCAD.1990.129849) (MDDs).

as well as [Cython](http://cython.org/) bindings to the C libraries:

- [CUDD](https://web.archive.org/web/20180127051756/http://vlsi.colorado.edu/~fabio/CUDD/html/index.html) (also read [the introduction](https://web.archive.org/web/20150317121927/http://vlsi.colorado.edu/~fabio/CUDD/node1.html), and note that the original link for CUDD is <http://vlsi.colorado.edu/~fabio/CUDD/>)
- [Sylvan](https://github.com/utwente-fmt/sylvan) (multi-core parallelization)
- [BuDDy](https://sourceforge.net/projects/buddy/)

These bindings expose almost identical interfaces as the Python implementation.
The intended workflow is:

- develop your algorithm in pure Python (easy to debug and introspect),
- use the bindings to benchmark and deploy

Your code remains the same.


Contains:

- All the standard functions defined, e.g.,
  by [Bryant](https://www.cs.cmu.edu/~bryant/pubdir/ieeetc86.pdf).
- Dynamic variable reordering using [Rudell's sifting algorithm](http://www.eecg.toronto.edu/~ece1767/project/rud.pdf).
- Reordering to obtain a given order.
- Parser of quantified Boolean expressions in either
  [TLA+](https://en.wikipedia.org/wiki/TLA%2B) or
  [Promela](https://en.wikipedia.org/wiki/Promela) syntax.
- Pre/Image computation (relational product).
- Renaming variables.
- Conversion from BDDs to MDDs.
- Conversion functions to [`networkx`](https://networkx.github.io/) and
  [`pydot`](https://pypi.python.org/pypi/pydot) graphs.
- BDDs have methods to `dump` and `load` them using `pickle`.
- BDDs dumped by CUDD's DDDMP can be loaded using fast iterative parser.
- Garbage collection using reference counting


If you prefer to work with integer variables instead of Booleans, and have
BDD computations occur underneath, then use the module
[`omega.symbolic.fol`](
    https://github.com/tulip-control/omega/blob/master/omega/symbolic/fol.py)
from the [`omega` package](
    https://github.com/tulip-control/omega/blob/master/doc/doc.md).


Documentation
=============

In the [Markdown](https://en.wikipedia.org/wiki/Markdown) file
[`doc.md`](https://github.com/tulip-control/dd/blob/master/doc.md).


Examples
========


The module `dd.autoref` wraps the pure-Python BDD implementation `dd.bdd`.
The API of `dd.cudd` is almost identical to `dd.autoref`.
You can skip details about `dd.bdd`, unless you want to implement recursive
BDD operations at a low level.


```python
from dd.autoref import BDD

bdd = BDD()
bdd.declare('x', 'y', 'z', 'w')

# conjunction (in TLA+ syntax)
u = bdd.add_expr('x /\ y')  # operators `&, |` are supported too
print(u.support)
# substitute variables for variables (rename)
rename = dict(x='z', y='w')
v = bdd.let(rename, u)
# substitute constants for variables (cofactor)
values = dict(x=True, y=False)
v = bdd.let(values, u)
# substitute BDDs for variables (compose)
d = dict(x=bdd.add_expr('z \/ w'))
v = bdd.let(d, u)
# infix operators
v = bdd.var('z') & bdd.var('w')
v = ~ v
# quantify
u = bdd.add_expr('\E x, y:  x \/ y')
# less readable but faster alternative
u = bdd.var('x') | bdd.var('y')
u = bdd.exist(['x', 'y'], u)
assert u == bdd.true, u
# inline BDD references
u = bdd.add_expr('x /\ {v}'.format(v=v))
# satisfying assignments (models)
d = bdd.pick(u, care_vars=['x', 'y'])
for d in bdd.pick_iter(u):
    print(d)
n = bdd.count(u)
```

To run the same code with CUDD installed, change the first line to:

```python
from dd.cudd import BDD
```

Most useful functionality is available via method of the class `BDD`.
A few of the functions can prove handy too, mainly `to_nx`, `to_pydot`.
Use the method `BDD.dump` to write a `BDD` to a `pickle` file, and
`BDD.load` to load it back. A CUDD dddmp file can be loaded using
the function `dd.dddmp.load`.

A `Function` object wraps each BDD node and decrements its reference count
when disposed by Python's garbage collector. Lower-level details are
discussed in the documentation.


Installation
============


## pure-Python

From PyPI:

```shell
pip install dd
```

Locally:

```shell
pip install .
```

For graph layout with `pydot`, install also [graphviz](http://graphviz.org/).


## Cython bindings


### Wheel files with compiled CUDD


As of `dd` version 0.5.3, [`manylinux1_x86_64`](
    https://www.python.org/dev/peps/pep-0513/)
[wheel files](https://www.python.org/dev/peps/pep-0427/) are
[available from PyPI](https://pypi.org/project/dd/#files) for some Python
versions. These wheel files contain the module `dd.cudd` with the CUDD
library compiled and linked.
If you have a Linux system and Python version compatible with one of the
available wheels, then `pip install dd` will install `dd.cudd`, so you need
not compile CUDD. Otherwise, see below.


### `dd` fetching CUDD

By default, the package installs only the Python modules.
You can select to install any Cython extensions using
the `setup.py` options:

- `--cudd`
- `--sylvan`
- `--buddy`

Pass `--fetch` to `setup.py` to tell it to download, unpack, and
`make` CUDD v3.0.0. For example:

```shell
pip download dd --no-deps
tar xzf dd-*.tar.gz
cd dd-*
python setup.py install --fetch --cudd
```

The path to an existing CUDD build directory can be passed as an argument:

```shell
python setup.py install --cudd="/home/user/cudd"
```

If you prefer defining installation directories, then follow [Cython's instructions](
    http://cython.readthedocs.io/en/latest/src/tutorial/clibraries.html#compiling-and-linking)
to define `CFLAGS` and `LDFLAGS` before running `setup.py`.
You need to have copied `CuddInt.h` to the installation's include location
(CUDD omits it).

If building from the repository, then first install `cython`. For example:

```shell
git clone git@github.com:tulip-control/dd
cd dd
pip install cython  # not needed if building from PyPI distro
python setup.py install --fetch --cudd
```

The above options can be passed to `pip` too, using the [`--install-option`](
    https://pip.pypa.io/en/latest/reference/pip_install.html#per-requirement-overrides)
in a requirements file, for example:

```
dd >= 0.1.1 --install-option="--fetch" --install-option="--cudd"
```

The command line behavior of `pip` [is currently different](
    https://github.com/pypa/pip/issues/1883), so

```shell
pip install --install-option="--fetch" dd
```

will propagate option `--fetch` to dependencies, and so raise an error.


### User installing build dependencies

If you build and install CUDD, Sylvan, or BuDDy yourself, then ensure that:

- the header files and libraries are present, and
- suitable compiler, include, linking, and library flags are passed,
either by setting [environment variables](
    https://en.wikipedia.org/wiki/Environment_variable)
prior to calling `pip`, or by editing the file [`download.py`](https://github.com/tulip-control/dd/blob/master/download.py).

Currently, `download.py` expects to find Sylvan under `dd/sylvan` and built with [Autotools](https://en.wikipedia.org/wiki/GNU_Build_System)
(for an example, see `.travis.yml`).
If the path differs in your environment, remember to update it.


Tests
=====

Require [`nose`](https://pypi.python.org/pypi/nose). Run with:

```shell
cd tests/
nosetests
```

Tests of Cython modules that were not installed will fail.


License
=======
[BSD-3](http://opensource.org/licenses/BSD-3-Clause), see file `LICENSE`.


[build_img]: https://travis-ci.org/tulip-control/dd.svg?branch=master
[travis]: https://travis-ci.org/tulip-control/dd
[coverage]: https://coveralls.io/repos/tulip-control/dd/badge.svg?branch=master
[coveralls]: https://coveralls.io/r/tulip-control/dd?branch=master
