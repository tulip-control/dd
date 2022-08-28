[![Build Status][build_img]][ci]


About
=====

A pure-Python (Python >= 3.11) package for manipulating:

- [Binary decision diagrams](
    https://en.wikipedia.org/wiki/Binary_decision_diagram) (BDDs).
- [Multi-valued decision diagrams](
    https://dx.doi.org/10.1109/ICCAD.1990.129849) (MDDs).

as well as [Cython](https://cython.org) bindings to the C libraries:

- [CUDD](
    https://web.archive.org/web/20180127051756/http://vlsi.colorado.edu/~fabio/CUDD/html/index.html)
  (also read [the introduction](
    https://web.archive.org/web/20150317121927/http://vlsi.colorado.edu/~fabio/CUDD/node1.html),
  and note that the original link for CUDD is <http://vlsi.colorado.edu/~fabio/CUDD/>)
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
- Dynamic variable reordering using [Rudell's sifting algorithm](
    http://www.eecg.toronto.edu/~ece1767/project/rud.pdf).
- Reordering to obtain a given order.
- Parser of quantified Boolean expressions in either
  [TLA+](https://en.wikipedia.org/wiki/TLA%2B) or
  [Promela](https://en.wikipedia.org/wiki/Promela) syntax.
- Pre/Image computation (relational product).
- Renaming variables.
- Zero-omitted binary decision diagrams (ZDDs) in CUDD
- Conversion from BDDs to MDDs.
- Conversion functions to [`networkx`](https://networkx.org) and
  [`pydot`](https://pypi.org/project/pydot) graphs.
- BDDs have methods to `dump` and `load` them using [JSON](
    https://wikipedia.org/wiki/JSON), or [`pickle`](
    https://docs.python.org/3/library/pickle.html).
- BDDs dumped by CUDD's DDDMP can be loaded using fast iterative parser.
- [Garbage collection](
    https://en.wikipedia.org/wiki/Garbage_collection_(computer_science))
  that combines reference counting and tracing


If you prefer to work with integer variables instead of Booleans, and have
BDD computations occur underneath, then use the module
[`omega.symbolic.fol`](
    https://github.com/tulip-control/omega/blob/main/omega/symbolic/fol.py)
from the [`omega` package](
    https://github.com/tulip-control/omega/blob/main/doc/doc.md).

If you are interested in computing minimal covers (two-level logic minimization)
then use the module `omega.symbolic.cover` of the `omega` package.
The method `omega.symbolic.fol.Context.to_expr` converts BDDs to minimal
formulas in disjunctive normal form (DNF).


Documentation
=============

In the [Markdown](https://en.wikipedia.org/wiki/Markdown) file
[`doc.md`](https://github.com/tulip-control/dd/blob/main/doc.md).

The [changelog](https://en.wiktionary.org/wiki/changelog) is in
the file [`CHANGES.md`](
    https://github.com/tulip-control/dd/blob/main/CHANGES.md).


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
u = bdd.add_expr(r'x /\ y')
    # symbols `&`, `|` are supported too
    # note the "r" before the quote,
    # which signifies a raw string and is
    # needed to allow for the backslash
print(u.support)
# substitute variables for variables (rename)
rename = dict(x='z', y='w')
v = bdd.let(rename, u)
# substitute constants for variables (cofactor)
values = dict(x=True, y=False)
v = bdd.let(values, u)
# substitute BDDs for variables (compose)
d = dict(x=bdd.add_expr(r'z \/ w'))
v = bdd.let(d, u)
# as Python operators
v = bdd.var('z') & bdd.var('w')
v = ~ v
# quantify universally ("forall")
u = bdd.add_expr(r'\A x, y:  (x /\ y) => y')
# quantify existentially ("exist")
u = bdd.add_expr(r'\E x, y:  x \/ y')
# less readable but faster alternative,
# (faster because of not calling the parser;
# this may matter only inside innermost loops)
u = bdd.var('x') | bdd.var('y')
u = bdd.exist(['x', 'y'], u)
assert u == bdd.true, u
# inline BDD references
u = bdd.add_expr(rf'x /\ {v}')
# satisfying assignments (models):
# an assignment
d = bdd.pick(u, care_vars=['x', 'y'])
# iterate over all assignments
for d in bdd.pick_iter(u):
    print(d)
# how many assignments
n = bdd.count(u)
# write to and load from JSON file
filename = 'bdd.json'
bdd.dump(filename, roots=dict(res=u))
other_bdd = BDD()
roots = other_bdd.load(filename)
print(other_bdd.vars)
```

To run the same code with CUDD installed, change the first line to:

```python
from dd.cudd import BDD
```

Most useful functionality is available via methods of the class `BDD`.
A few of the functions can prove handy too, mainly `to_nx`, `to_pydot`.
Use the method `BDD.dump` to write a `BDD` to a `pickle` file, and
`BDD.load` to load it back. A CUDD dddmp file can be loaded using
the function `dd.dddmp.load`.

A `Function` object wraps each BDD node and decrements its reference count
when disposed by Python's garbage collector. Lower-level details are
discussed in the documentation.

For using ZDDs, change the first line to

```python
from dd.cudd_zdd import ZDD as BDD
```


Installation
============


## pure-Python

From the [Python Package Index (PyPI)](https://pypi.org) using the
package installer [`pip`](https://pip.pypa.io):

```shell
pip install dd
```

or from the directory of source files:

```shell
pip install .
```

For graph layout, install also [graphviz](https://graphviz.org).

The `dd` package requires Python 3.11 or later.
For Python 2.7, use `dd == 0.5.7`.


## Cython bindings

To compile also the module `dd.cudd` (which interfaces to CUDD)
when installing from PyPI, run:

```shell
pip install --upgrade wheel cython
export DD_FETCH=1 DD_CUDD=1
pip install dd -vvv --use-pep517 --no-build-isolation
```

(`DD_FETCH=1 DD_CUDD=1 pip install dd` also works,
when the source tarball includes cythonized code.)

To confirm that the installation succeeded:

```shell
python -c 'import dd.cudd'
```

The [environment variables](
    https://en.wikipedia.org/wiki/Environment_variable)
above mean:
- `DD_FETCH=1`: download CUDD v3.0.0 sources from the internet,
  unpack the tarball (after checking its hash), and `make` CUDD.
- `DD_CUDD=1`: build the Cython module `dd.cudd`

More about environment variables that configure the
C extensions of `dd` is described in the file [`doc.md`](
    https://github.com/tulip-control/dd/blob/main/doc.md)


## Wheel files with compiled CUDD

[Wheel files](
    https://www.python.org/dev/peps/pep-0427/)
are [available from PyPI](
    https://pypi.org/project/dd/#files),
which contain the module `dd.cudd`,
with the CUDD library compiled and linked.
If you have a Linux system and Python version compatible with
one of the PyPI wheels,
then `pip install dd` will install also `dd.cudd`.


### Licensing of the compiled modules `dd.cudd` and `dd.cudd_zdd` in the wheel

These notes apply to the compiled modules `dd.cudd` and `dd.cudd_zdd` that are
contained in the [wheel file](https://www.python.org/dev/peps/pep-0427/) on
PyPI (namely the files `dd/cudd.cpython-39-x86_64-linux-gnu.so` and
`dd/cudd_zdd.cpython-39-x86_64-linux-gnu.so` in the [`*.whl` file](
    https://pypi.org/project/dd/#files), which can
be obtained using [`unzip`](http://infozip.sourceforge.net/UnZip.html)).
These notes do not apply to the source code of the modules
`dd.cudd` and `dd.cudd_zdd`.
The source distribution of `dd` on PyPI is distributed under a 3-clause BSD
license.

The following libraries and their headers were used when building the modules
`dd.cudd` and `dd.cudd_zdd` that are included in the wheel:

- Python: <https://www.python.org/ftp/python/3.A.B/Python-3.A.B.tgz>
  (where `A` and `B` the numerals of
   the corresponding Python version used;
   for example `10` and `2` to signify Python 3.10.2).
  CPython releases are described at:
    <https://www.python.org/downloads/>
- [CUDD](https://sourceforge.net/projects/cudd-mirror/files/cudd-3.0.0.tar.gz/download).

The licenses of Python and CUDD are included in the wheel archive.

Cython [does not](https://github.com/cython/cython/blob/master/COPYING.txt)
add its license to C code that it generates.

GCC was used to compile the modules `dd.cudd` and `dd.cudd_zdd` in the wheel,
and the GCC [runtime library exception](
    https://github.com/gcc-mirror/gcc/blob/master/COPYING.RUNTIME#L61-L66)
applies.

The modules `dd.cudd` and `dd.cudd_zdd` in the wheel dynamically link to the:

- Linux kernel (in particular [`linux-vdso.so.1`](
    https://man7.org/linux/man-pages/man7/vdso.7.html)),
  which allows system calls (read the kernel's file [`COPYING`](
    https://github.com/torvalds/linux/blob/master/COPYING) and the explicit
  syscall exception in the file [`LICENSES/exceptions/Linux-syscall-note`](
    https://github.com/torvalds/linux/blob/master/LICENSES/exceptions/Linux-syscall-note))
- [GNU C Library](https://www.gnu.org/software/libc/) (glibc) (in particular
  `libpthread.so.0`, `libc.so.6`, `/lib64/ld-linux-x86-64.so.2`), which uses
  the [LGPLv2.1](https://sourceware.org/git/?p=glibc.git;a=blob_plain;f=COPYING.LIB;hb=HEAD)
  that allows dynamic linking, and other [licenses](
    https://sourceware.org/git/?p=glibc.git;a=blob_plain;f=LICENSES;hb=HEAD).
  These licenses are included in the wheel file and apply to the GNU C Library
  that is dynamically linked.


Tests
=====

Use [`pytest`](https://pypi.org/project/pytest). Run with:

```shell
cd tests/
pytest -v --continue-on-collection-errors .
```

Tests of Cython modules that were not installed will fail.
The code is covered well by tests.


License
=======
[BSD-3](https://opensource.org/licenses/BSD-3-Clause), read file `LICENSE`.


[build_img]: https://github.com/tulip-control/dd/actions/workflows/main.yml/badge.svg?branch=main
[ci]: https://github.com/tulip-control/dd/actions
