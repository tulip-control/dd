# `dd` documentation


# Table of Contents

- [Design principles](#design-principles)
- [Create and plot a binary decision diagram](#create-and-plot-a-binary-decision-diagram)
    - [Using a `BDD` manager](#using-a-bdd-manager)
    - [Plotting](#plotting)
    - [Alternatives](#alternatives)
    - [Reminders about the implementation beneath](#reminders-about-the-implementation-beneath)
    - [Pickle](#pickle)
    - [Nodes as `Function` objects](#nodes-as-function-objects)
        - [BDD equality](#bdd-equality)
        - [Other methods](#other-methods)
- [CUDD interface: `dd.cudd`](#cudd-interface-ddcudd)
    - [Functions](#functions)
- [Lower level: `dd.bdd`](#lower-level-ddbdd)
    - [Reference counting](#reference-counting)
    - [Reordering](#reordering)
    - [Other methods](#other-methods)
- [Example: Reachability analysis](#example-reachability-analysis)
- [Syntax for quantified Boolean formulas](#syntax-for-quantified-boolean-formulas)
- [Multi-valued decision diagrams (MDD)](#multi-valued-decision-diagrams-mdd)
- [Installation of C extension modules](#installation-of-c-extension-modules)
    - [Environment variables that activate C extensions](#environment-variables-that-activate-c-extensions)
    - [Alternative: directly running `setup.py`](#alternative-directly-running-setuppy)
    - [Using the package `build`](#using-the-package-build)
    - [Customizing the C compilation](#customizing-the-c-compilation)
- [Installing the development version](#installing-the-development-version)
- [Footnotes](#footnotes)
- [Copying](#copying)


## Design principles

The interface is in Python. The representation depends on what you want and
have installed. For solving small to medium size problems, say for teaching,
or prototyping new algorithms, pure Python can be more convenient.
To work with larger problems, it works better if you install the C library
[CUDD](https://web.archive.org/web/http://vlsi.colorado.edu/~fabio/CUDD/html/index.html).
Let's call these “backends”.

The same user code can run with both the Python and C backends.
You only need to modify an `import dd.autoref as _bdd` to
`import dd.cudd as _bdd`, or import the best available interface:

```python
try:
    import dd.cudd as _bdd
except ImportError:
    import dd.autoref as _bdd
```

The following sections describe how to use the high level interface
(almost identical in `autoref` and `cudd`). The lower level interface to
the pure-Python implementation in `dd.bdd` is also described,
for those interested in more details.


## Create and plot a binary decision diagram

The starting point for using a BDD library is a *shared* reduced ordered
binary decision diagram. Implementations call this *manager*.
The adjectives mean:

- binary: each node represents a propositional formula
- ordered: variables have a fixed order that changes in a controlled way
- reduced: given variable order, equivalent propositional formulas are
  represented by a unique diagram
- shared: common subformulas are represented using common elements in memory.

The manager is a directed graph, with each node representing a formula.
Each formula can be understood as a collection of assignments to variables.
As mentioned above, the variables are ordered.
The *level* of a variable is its index in this order, starting from 0.
The *terminal* nodes correspond to `TRUE` and `FALSE`, with maximal index.

Each manager is a `BDD` class, residing in a different module:

- `dd.autoref.BDD`: high-level interface to pure Python implementation
- `dd.cudd.BDD`: same high-level interface to a C implementation
- `dd.sylvan.BDD`: interface to another C implementation (multi-core)
- `dd.bdd.BDD`: low-level interface to pure Python implementation
  (wrapped by `dd.autoref.BDD`).

The main difference between these modules is how a BDD node is represented:

- `autoref`: `autoref.Function`
- `cudd`: `cudd.Function`
- `sylvan`: `sylvan.Function`
- `bdd`: `int`

In `autoref` and `cudd`, a `Function` class represents a node.
In `bdd`, a signed integer represents a node.

All implementations use negated edges,
so logical negation takes *constant* time.


### Using a `BDD` manager


Roughly four kinds of operations suffice to perform most tasks:

- creating BDDs from formulas
- quantification (`forall`, `exist`)
- substitution (`let`)
- enumerating models that satisfy a BDD

First, instantiate a manager and declare variables

```python
from dd import autoref as _bdd

bdd = _bdd.BDD()
bdd.declare('x', 'y', 'z')
```

To create a BDD node for a propositional formula, call the parser

```python
u = bdd.add_expr(r'x /\ y')  # conjunction
v = bdd.add_expr(r'z \/ ~ y')  # disjunction and negation
w = u & ~ v
```

The formulas above are in [TLA+](https://en.wikipedia.org/wiki/TLA%2B) syntax.
If you prefer the syntax `&, |, !`, the parser recognizes those operators too.
The inverse of `BDD.add_expr` is `BDD.to_expr`:

```python
s = bdd.to_expr(u)
>>> s
'ite(x, y, False)'
```

Lets create the BDD of a more colorful Boolean formula

```python
s = r'(x /\ y) <=> (~ z \/ ~ (y <=> x))'
v = bdd.add_expr(s)
```

In natural language, the expression `s` reads:
“(x and y) if and only if ( (not z) or (y xor x) )”.
The Boolean constants are `bdd.false` and `bdd.true`, and in syntax
`FALSE` and `TRUE`.

Variables can be quantified by calling the methods `exist` and `forall`

```python
u = bdd.add_expr(r'x /\ y')
v = bdd.exist(['x'], u)
```

or by writing quantified formulas

```python
# there exists a value of x, such that (x and y)
u = bdd.add_expr(r'\E x:  x /\ y')
y = bdd.add_expr('y')
assert u == y, (u, y)

# forall x, there exists y, such that (y or x)
u = bdd.add_expr(r'\A x:  \E y:  y \/ z')
assert u == bdd.true, u
```

`dd` supports "inline BDD references" via the `@` operator. Each BDD node `u`
has an integer representation `int(u)` and a string representation `str(u)`.
For example, if the integer representation is `5`, then the string
representation is `@5`. These enable you to mention existing BDD nodes
in formulas, without the need to expand them as formulas. For example:

```python
u = bdd.add_expr(r'y \/ z')
s = rf'x /\ {u}'
v = bdd.add_expr(s)
v_ = bdd.add_expr(r'x /\ (y \/ z)')
assert v == v_
```

Substitution comes in several forms:

- replace some variable names by other variable names
- replace some variable names by Boolean constants
- replace some variable names by BDD nodes, so by arbitrary formulas

All these kinds of substitution are performed via the method `let`,
which takes a `dict` that maps the variable names to replacements.
To substitute some variables for some other variables

```python
bdd.declare('x', 'p', 'y', 'q', 'z')
u = bdd.add_expr(r'x  \/  (y /\ z)')
# substitute variables for variables (rename)
d = dict(x='p', y='q')
v = bdd.let(d, u)
>>> v.support
{'p', 'q', 'z'}
```

The other forms are similar

```python
# substitute constants for variables (cofactor)
values = dict(x=True, y=False)
v = bdd.let(values, u)
# substitute BDDs for variables (compose)
d = dict(x=bdd.add_expr(r'z \/ w'))
v = bdd.let(d, u)
```

A BDD represents a formula, a syntactic object. Semantics is about how
syntax is used to describe the world. We could interpret the same formula
using different semantics and reach different conclusions.

A formula is usually understood as describing some assignments of values to
variables. Such an assignment is also called a *model*.
A model is represented as a `dict` that maps variable names to values.

```python
u = bdd.add_expr(r'x \/ y')
>>> bdd.pick(u)  # choose an assignment, `u.pick()` works too
{'x': False, 'y': True}
```

When working with BDDs, two issues arise:

- which variable names are present in an assignment?
- what values do the variables take?

The values are Boolean, because BDD machinery is designed to reason for
that case only, so `1 /\ 5` is a formula outside the realm of BDD reasoning.
The choice of variable names is a matter we discuss below.

Consider the example

```python
bdd.declare('x', 'y', 'z')
u = bdd.add_expr(r'x \/ y')
>>> u.support
{'x', 'y'}
```

This tells us that the variables `x` and `y` occur in the formula that the
BDD node `u` represents. Knowing what (Boolean) values a model assigns to
the variables `x` and `y` suffices to decide whether the model satisfies `u`.
In other words, the values of other variables, like `z`, are irrelevant to
evaluating the expression `x \/ y`.

The choice of semantics is yours. Which variables you want an assignment to
mention depends on what you are doing with the assignment in your algorithm.

```python
u = bdd.add_expr('x')
# default: variables in support(u)
models = list(bdd.pick_iter(u))
>>> models
[{'x': True}]
# variables in `care_vars`
models = list(bdd.pick_iter(u, care_vars=['x', 'y']))
>>> models
[{'x': True, 'y': False}, {'x': True, 'y': True}]
```

By default, `pick_iter` returns assignments to all variables in the support
of the BDD node `u` given as input.
In this example, the support of `u` contains one variable: `x`
(because the value of the expression `'x'` is independent of variable `y`).

We can use the argument `care_vars` to specify the variables that we want
the assignment to include. The assignments returned will include all variables
in `care_vars`, plus the variables that appear along each path traversed in
the BDD. Variables in `care_vars` that are unassigned along each path will
be exhaustively enumerated (i.e., all combinations of `True` and `False`).

For example, if `care_vars == []`, then the assignments will contain only
those variables that appear along the recursive traversal of the BDD.
If `care_vars == support(u)`, then the result equals the default result.
For `care_vars > support(u)` we will observe more variables in each assignment
than the variables in the support.


We can also count how many assignments satisfy a BDD. The number depends on
how many variables occur in an assignment. The default number is as many
variables are contained in the support of that node. You can pass a larger
number

```python
bdd.declare('x', 'y')
u = bdd.add_expr('x')
>>> u.count()
1
models = list(bdd.pick_iter(u))
>>> models
[{'x': True}]
# pass a larger number of variables
>>> u.count(nvars=3)
4
models = list(bdd.pick_iter(u, ['x', 'y', 'z']))
>>> models
[{'x': True, 'y': False, 'z': False},
 {'x': True, 'y': True, 'z': False},
 {'x': True, 'y': False, 'z': True},
 {'x': True, 'y': True, 'z': True}]
```

A convenience method for creating a BDD from an assignment `dict` is

```python
d = dict(x=True, y=False, z=True)
u = bdd.cube(d)
v = bdd.add_expr(r'x /\ ~ y /\ z')
assert u == v, (u, v)
```

The interface is specified in the module `dd._abc`. Although [internal](
    https://www.python.org/dev/peps/pep-0008/#descriptive-naming-styles),
you may want to take a look at the `_abc` module.

Above we discussed semantics from a [proof-theoretic viewpoint](
    https://en.wikipedia.org/wiki/Metamathematics).
The same discussion can be rephrased in terms of function domains containing
assignments to variables, so a [model-theoretic viewpoint](
    https://en.wikipedia.org/wiki/Model_theory).


### Plotting


You can dump a PDF of all nodes in the manager as follows

```python
from dd import autoref as _bdd

bdd = _bdd.BDD()
bdd.declare('x', 'y', 'z')
u = bdd.add_expr(r'(x /\ y) \/ ~ z')
bdd.collect_garbage()  # optional
bdd.dump('awesome.pdf')
```

The result is shown below, with the meaning:

- integers on the left signify levels (thus variables)
- each node is annotated with a variable name (like `x`) dash the
  node index in `dd.bdd.BDD._succ` (mainly for debugging purposes)
- solid arcs represent the “if” branches
- dashed arcs the “else” branches
- only an “else” branch can be negated, signified by a `-1` annotation

Negated edges mean that logical negation, i.e., `~`, is applied to the node
that is pointed to.
Negated edges and BDD theory won't be discussed here, please refer to
a reference from those listed in the docstring of the module `dd.bdd`.
For example, [this document](
    http://www.ecs.umass.edu/ece/labs/vlsicad/ece667/reading/somenzi99bdd.pdf)
by Fabio Somenzi (CUDD's author).

In the following diagram, the BDD rooted at node `x-7` represents the
Boolean function `(x /\ y) \/ ~ z`. For example, for the assignment
`dict(x=False)`, the dashed arc from node `x-7` leads to the negation
(due to the negated edge, signified by a `-1`) of the node `z-5`.
The BDD rooted at `z-5` represents the Boolean function `z`,
so its negation is `~ z`.

The nodes `x-2`, `x-4`, `y-3` are intermediate results that result while
constructing the BDD for the Boolean function `(x /\ y) \/ ~ z`.
The BDD rooted at node `x-2` represents the Boolean function `x`, and the
BDD rooted at node `x-4` represents the Boolean function `x /\ y`.

![example_bdd](https://rawgithub.com/johnyf/binaries/main/dd/awesome.png)

An external reference to a BDD is an arc that points to a node.
For example, `u` above is an external reference. An external reference can be
a complemented arc. External references can be included in a BDD diagram by
using the argument `roots` of the method `BDD.dump`. For example

```python
from dd import autoref as _bdd

bdd = _bdd.BDD()
bdd.declare('x', 'y', 'z')
u = bdd.add_expr(r'(x /\ y) \/ ~ z')
print(u.negated)
v = ~ u
print(v.negated)
bdd.collect_garbage()
bdd.dump('rooted.pdf', roots=[v])
```

The result is the following diagram, where the node `@-7` is the external
reference `v`, which is a complemented arc.

![example_bdd](https://rawgithub.com/johnyf/binaries/main/dd/rooted.png)


It is instructive to dump the `bdd` with and without collecting garbage.


### Alternatives


As mentioned above, there are various ways to apply propositional operators

```python
x = bdd.var('x')
y = bdd.var('y')
u = x & y
u = bdd.apply('and', x, y)
u = bdd.apply('/\\', x, y)  # TLA+ syntax
u = bdd.apply('&', x, y)  # Promela syntax
```

Infix Python operators work for BDD nodes in `dd.autoref` and `dd.cudd`,
not in `dd.bdd`, because nodes there are plain integers (`int`).
Besides the method `apply`, there is also the ternary conditional method `ite`,
but that is more commonly used internally.

For single variables, the following are equivalent

```python
u = bdd.add_expr('x')
u = bdd.var('x')  # faster
```

In `autoref`, a few functions (not methods) are available for efficient
operations that arise naturally in fixpoint algorithms when transition
relations are involved:

- `image`, `preimage`: rename some variables, conjoin, existentially quantify,
  and rename some variables, all at once
- `copy_vars`: copy the variables of one BDD manager to another manager


### Reminders about the implementation beneath


The Python syntax for Boolean operations (`u & v`) and the method `apply`
are faster than the method `add_expr`, because the latter invokes the
parser (generated using [`ply.yacc`](https://github.com/dabeaz/ply)).
Using `add_expr` is generally quicker and more readable.
In practice, prototype new algorithms using `add_expr`,
then profile, and if it matters convert the code to use `~`, `&`, `|`,
and to call directly `apply`, `exist`, `let`, and other methods.

In the future, a compiler may be added, to compile expressions into
functions that can be called multiple times, without invoking again the parser.


The number of nodes in the manager `bdd` is `len(bdd)`.
As noted earlier, each variable corresponds to a level, which is an index in
the variable order. This mapping can be obtained with

```python
level = bdd.level_of_var('x')
var = bdd.var_at_level(level)
assert var == 'x', var
```

In `autoref.BDD`, the `dict` that maps each defined variable to its
corresponding level can be obtained also from the attribute `BDD.vars`

```python
>>> bdd.vars
{'x': 0, 'y': 1, 'z': 2}
```

To copy a node from one BDD manager to another manager

```python
a = _bdd.BDD()
a.declare('x', 'y', 'z')
u = a.add_expr(r'(x /\ y) \/ z')
# copy to another BDD manager
b = _bdd.BDD()
b.declare(*a.vars)
v = a.copy(u, b)
```

In each of the modules `dd.autoref` and `dd.cudd`, references to BDD nodes
are represented with a class named `Function`. When `Function` objects are
not referenced by any Python variable, CPython deallocates them, thus in
the next BDD garbage collection, the relevant BDD nodes can be deallocated.

For this reason, it is useful to avoid unnecessary references to nodes.
This includes the [underscore variable `_`](
    https://docs.python.org/3/reference/lexical_analysis.html#reserved-classes-of-identifiers),
for example:

```python
import dd.autoref

bdd = dd.autoref.BDD()
bdd.declare('x', 'y')
c = [bdd.add_expr(r'x /\ y'), bdd.add_expr(r'x \/ ~ y')]
u, _ = c  # `_` is assigned the `Function` that references
    # the root of the BDD that represents x \/ ~ y
c = list()  # Python deallocates the `list` object created above
# so `u` refers to the root of the BDD that represents x /\ y,
# as expected,
# but `_` still refers to the BDD that represents x \/ ~ y
print(bdd.to_expr(_))
```

The Python reference by `_` in the previous example can be avoided
by indexing, i.e., `u = c[0]`.


### Pickle

The `dd.autoref` and `dd.bdd` modules can dump the manager to a
[pickle file](https://en.wikipedia.org/wiki/Pickle_%28Python%29) and
load it back

```python
bdd.dump('manager.p')
```

and later, or in another run:

```python
bdd = BDD.load('manager.p')
```


### Nodes as `Function` objects

As mentioned earlier, the main difference between the main `dd` modules is
what type of object appears at the user interface as a “node”:

- `dd.bdd` gives to the user signed integers as nodes
- `dd.autoref` and `dd.cudd` give her `Function` objects as nodes.

Seldom should this make a difference to the user.
However, for integers, the meaning of the Python operators `~`, `&`, `|`, `^`
is *unrelated* to the BDD manager.
So, if `u = -3` and `v = 25` are nodes in the `dd.bdd.BDD` manager `bdd`,
you cannot write `w = u & v` to get the correct result.
You have to use either:

- `BDD.apply('and', u, v)` or
- `BDD.add_expr(rf'{u} /\ {v}')`.

Unlike `dd.bdd`, the nodes in `autoref` and `cudd` are of class `Function`.
This abstracts away the underlying node representation, so that you can run
the same code in both pure Python (with `dd.bdd.BDD` underneath as manager),
as well as C (with the `struct` named [`DdManager`](
    https://github.com/johnyf/cudd/blob/80c9396b7efcb24c33868aeffb89a557af0dc356/cudd/cudd/cudd.h#L281)
in `cudd.h` underneath as manager).

The [magic methods](https://github.com/RafeKettler/magicmethods) for
`~`, `&`, `|`, `^` implemented by `Function` are its most frequently used aspect.
Two methods called `implies` and `equiv` are available.
But it is more readable to use `bdd.apply` or `bdd.add_expr`,
or just `v | ~ u` for `u.implies(v)` and `~ (u ^ v)` for `u.equiv(v)`.


#### BDD equality

If `u` and `v` are instances of `Function`, and `u == v`, then `u` represents
the same BDD as `v`.

This is **NOT** true for nodes in `dd.bdd`, because `u` and `v` may be nodes
from *different* manager instances.
So, that `u == -3 == v` does not suffice to deduce that `u` and `v`
represent the same BDD. In this case, we have to ensure that `u` and `v`
originate from the same manager. Thus, using `dd.bdd` offers less protection
against subtle errors that will go undetected.


#### Other methods

Information about a node `u` can be read with a few attributes and magic:

- `len(u)` is the number of nodes in the graph that represents `u` in memory
- `u.var` is the name (`str`) of the variable in `BDD.support(u)` with
  minimal level (recall that variables are ordered)
- `u.level` is the level of `u.var`
- `u.ref` is the reference count of `u`, meaning the number of other nodes
  `v` with an edge `(v, u)`, plus external references to `u` by the user.

We say that the node `u` is “labeled” with variable `u.var`.
At this point, recall that these diagrams track *decisions*.
At each node, we decide where to go next, depending on the value of `u.var`.
If `u.var` is true, then we go to node `u.high`, else to node `u.low`.
For this reason, `u.high` is also called the “then” child of `u`,
and `u.low` the “else” child.

This object-oriented appearance is only an external interface for the user's
convenience. Typically, the bulk of the nodes aren't referenced externally.
Internally, the nodes are managed efficiently en masse, no `Function`s there.
A `Function.to_expr` method is present, but using `BDD.to_expr` looks tidier.


## CUDD interface: `dd.cudd`

We said earlier that you can develop with `autoref`, deferring usage of
`CUDD` for when really needed. This raises two questions:

1. Why not use `cudd` from the start ?
2. When should you switch from `autoref` to `cudd` ?

The answer to the second question is simple: when your problem takes more
time and memory than available.
For light to moderate use, `cudd` probably won't be needed.

Regarding the first question, `dd.cudd` requires to:

- *compile* CUDD, and
- *cythonize, compile, and link* `dd/cudd.pyx`.

The `setup.py` of `dd` can do these for you, as described in the file
[`README.md`](
    https://github.com/tulip-control/dd/blob/main/README.md#cython-bindings).
However, this may require more attention than appropriate for the occassion.
An example is teaching BDDs in a class on data structures, with the objective
for students to play with BDDs, not with [`gcc`](
    https://en.wikipedia.org/wiki/GNU_Compiler_Collection)
and [linking](
    https://en.wikipedia.org/wiki/Linker_%28computing%29)
errors (that's enlightening too, but in the realm of a slightly different class).


If you are interested in tuning CUDD to get most out of it (or because some
problem demands it due to its size), then use:

- `BDD.statistics` to obtain the information described in
  [CUDD Programmer's manual / Gathering and interpreting statistics](
    https://www.cs.rice.edu/~lm30/RSynth/CUDD/cudd/doc/node4.html#SECTION00048000000000000000).
- `BDD.configure` to read and set the parameters “max memory”, “loose up to”,
  “max cache hard”, “min hit”, and “max growth”.

Due to how CUDD manages variables, the method `add_var` takes as keyword
argument the variable index, *not* the level (which `autoref` does).
The level can still be set with the method `insert_var`.

The methods `dump` and `load` store the BDD of a selected node in a DDDMP file.
Pickling and PDF plotting are not available yet in `dd.cudd`.

An interface to the BuDDy C libary also exists, as `dd.buddy`.
However, experimentation suggests that BuDDy does not contain as successful
heuristics for deciding *when* to invoke reordering.

CUDD is initialized with a `memory_estimate` of 1 GiB (1 [gibibyte](
    https://en.wikipedia.org/wiki/Gibibyte)).
If the machine has less RAM, then `cudd.BDD` will raise an error. In this case,
pass a smaller initial memory estimate, for example

```python
cudd.BDD(memory_estimate=0.5 * 2**30)
```

The package [`humanize`](https://pypi.org/project/humanize/) is useful for
reading memory sizes, for example
`humanize.naturalsize(1073741824, binary=True)` returns `'1.0 GiB'`.
Relevant reading about [gigabyte](https://en.wikipedia.org/wiki/Gigabyte),
[IEC prefixes for binary multiples](
    https://en.wikipedia.org/wiki/Binary_prefix#IEC_prefixes), and
the [ISO/IEC 80000 standard](
    https://en.wikipedia.org/wiki/ISO/IEC_80000#Information_science_and_technology).


### Functions

The functions `and_exists`, `or_forall` in `dd.cudd` offer the functionality of
relational products (meaning neighboring variable substitution, conjunction,
and quantification, all at one pass over BDDs).
This functionality is implemented with `image`, `preimage` in `dd.autoref`.
Note that (pre)image contains substitution, unlike `and_exists`.

The function `cudd.reorder` is similar to `autoref.reorder`,
but does not default to invoking automated reordering.
Typical use of CUDD enables dynamic reordering.


### Checking for reference counting errors

When a BDD manager `dd.cudd.BDD` is deallocated, it asserts that no BDD nodes
have nonzero reference count in CUDD. By default, this assertion should never
fail, because automated reference counting makes it impossible.

If the assertion fails, then the exception is ignored and a message is printed
instead, and Python continues execution (read also the Cython documentation of
[`__dealloc__`](
    https://cython.readthedocs.io/en/latest/src/userguide/special_methods.html#finalization-method-dealloc),
the Python documentation of
["Finalization and De-allocation"](
    https://docs.python.org/3/extending/newtypes.html#finalization-and-de-allocation),
and of [`tp_dealloc`](
    https://docs.python.org/3/c-api/typeobj.html#c.PyTypeObject.tp_dealloc)).

In case the user decides to explicitly modify the reference counts,
ignoring exceptions can make it easier for reference counting errors
to go unnoticed. To make Python exit when reference counting errors exist
before a BDD manager is deallocated, use:

```python
from dd import cudd

bdd = cudd.BDD()
# ... statements ...
# raise `AssertionError` if any nodes have nonzero reference count
# just before deallocating the BDD manager
assert len(bdd) == 0, len(bdd)
```

Note that the meaning of `len` for the class `dd.autoref.BDD` is slightly
different. As a result, the code for checking that no BDD nodes have nonzero
reference count in `dd.autoref` is:

```python
from dd import autoref

bdd = autoref.BDD()
# ... statements ...
# raise `AssertionError` if any nodes have nonzero reference count
# just before deallocating the BDD manager
bdd._bdd.__del__()  # directly calling `__del__` does raise
    # any exception raised inside `__del__`
```

Note that if an assertion fails inside `__del__`, then
[the exception is ignored and a message is printed to `sys.stderr` instead](
    https://docs.python.org/3/reference/datamodel.html#object.__del__),
and Python continues execution. This is similar to what happens with
exceptions raised inside `__dealloc__` of extension types in Cython.
When `__del__` is called directly, exceptions raised inside it are not ignored.


## Lower level: `dd.bdd`

We discuss now some more details about the pure Python implementation
in `dd.bdd`. Two interfaces are available:

- convenience: the module
  [`dd.autoref`](https://github.com/tulip-control/dd/blob/main/dd/autoref.py) wraps
  `dd.bdd` and takes care of reference counting
  using [`__del__`](https://docs.python.org/3/reference/datamodel.html#object.__del__).

- "low level": the module
  [`dd.bdd`](https://github.com/tulip-control/dd/blob/main/dd/bdd.py) requires that
  the user in/decrement the reference counters associated with nodes that
  are used outside of a `BDD`.

The pure-Python module `dd.bdd` can be used directly,
which allows access more extensive than `dd.autoref`.
The `n` variables in a `dd.bdd.BDD` are ordered
from `0` (top level) to `n - 1` (bottom level).
The terminal node `1` is at level `n`.
The constant `TRUE` is represented by `+1`, and `FALSE` by `-1`.

To avoid running out of memory, a BDD manager deletes nodes when they are not
used anymore. This is called [garbage collection](
    https://en.wikipedia.org/wiki/Garbage_collection_%28computer_science%29).
So, two things need to happen:

1. keep track of node “usage”
2. invoke garbage collection

Garbage collection is triggered either explicitly by the user, or
when invoking the reordering algorithm.
To prevent nodes from being garbage collected, their reference counts should
be incremented, which is discussed in the next section.

Node usage is tracked with reference counting, for each node.
In `autoref`, the reference counts are maintained by the constructor and
destructor methods of `Function` (hence the “auto”).
These methods are invoked when the `Function` object is not referenced any
more by variables, so [Python decides](
    https://docs.python.org/3/glossary.html#term-garbage-collection)
to delete it.

In `dd.bdd`, you have to perform the reference counting by suitably adding to
and subtracting from the counter associated to the node you reference.
Also, garbage collection is invoked either explicitly or by reordering
(explicit or dynamic). So if you don't need to collect garbage, then you
can skip the reference counting (not recommended).


### Reference counting

The reference counters live inside [`dd.bdd.BDD._ref`](
    https://github.com/tulip-control/dd/blob/cbbc96f93da68d3d10f161ef27ccc5e3756c5ae2/dd/bdd.py#L81).
To guard against corner cases, like attempting to decrement a zero counter, use

- [`BDD.incref(u)`](
    https://github.com/tulip-control/dd/blob/cbbc96f93da68d3d10f161ef27ccc5e3756c5ae2/dd/bdd.py#L126):
  +1 to the counter of node `u`
- [`BDD.decref(u)`](
    https://github.com/tulip-control/dd/blob/cbbc96f93da68d3d10f161ef27ccc5e3756c5ae2/dd/bdd.py#L130):
  -1 to the same counter.

The method names `incref` and `decref` originate from the
[Python reference counting](https://docs.python.org/3/c-api/refcounting.html)
implementation. If we want node `u` to persist after garbage collection,
then it needs to be actively referenced at least once

```python
u = bdd.add_expr(s)
bdd.incref(u)
```

Revisiting an earlier example, manual reference counting looks like:

```python
from dd import bdd as _bdd

bdd = _bdd.BDD()
bdd.declare('x', 'y', 'z')
s = r'(x /\ y) \/ ~ z'  # TLA+ syntax
s = '(x & y) | ! z'  # Promela syntax
u = bdd.add_expr(s)
bdd.incref(u)
bdd.dump('before_collections.pdf')
bdd.collect_garbage()
bdd.dump('middle.pdf')
bdd.decref(u)
bdd.collect_garbage()
bdd.dump('after_collections.pdf')
```

A formula may depend on a variable, or not.
There are two ways to find out

```python
u = bdd.add_expr(r'x /\ y')  # TLA+ syntax
u = bdd.add_expr('x & y')  # Promela syntax

c = 'x' in bdd.support(u)  # more readable
c_ = bdd.is_essential(u, 'x')  # slightly more efficient
assert c == True, c
assert c == c_, (c, c_)

c = 'z' in bdd.support(u)
assert c == False, c
```


### Reordering

Given a BDD, the size of its graph representation depends on the variable order.
Reordering changes the variable order. Reordering *optimization* searches for
a variable order better than the current one.
*Dynamic* reordering is the automated invocation of reordering optimization.
BDD managers use heuristics to decide when to invoke reordering,
because it is [NP-hard](https://en.wikipedia.org/wiki/NP-hardness) to
find a variable order that minimizes a given BDD.

The function `dd.bdd.reorder` implements [Rudell's sifting algorithm](
    http://www.eecg.toronto.edu/~ece1767/project/rud.pdf).
This reordering heuristic is the most commonly used, also in CUDD.
Dynamic variable reordering can be enabled by calling:

```python
from dd import bdd as _bdd

bdd = _bdd.BDD()
bdd.configure(reordering=True)
```

By default, dynamic reordering in `dd.bdd.BDD` is disabled.
This default is unlike `dd.cudd` and will change in the future to enabled.

You can also invoke reordering explicitly when desired, besides dynamic
invocation. For example:

```python
from dd import bdd as _bdd

bdd = _bdd.BDD()
vrs = [f'x{i}' for i in range(3)]
vrs.extend(f'y{i}' for i in range(3))
bdd.declare(*vrs)
>>> bdd.vars
{'x0': 0, 'x1': 1, 'x2': 2, 'y0': 3, 'y1': 4, 'y2': 5}

s = r'(x0 /\ y0) \/ (x1 /\ y1) \/ (x2 /\ y2)'  # TLA+ syntax
s = '(x0 & y0) | (x1 & y1) | (x2 & y2)'  # Promela syntax
u = bdd.add_expr(s)
bdd.incref(u)
>>> len(bdd)
22

# collect intermediate results produced while making u
bdd.collect_garbage()
>>> len(bdd)
15
bdd.dump('before_reordering.pdf')

# invoke variable order optimization by sifting
_bdd.reorder(bdd)
>>> len(bdd)
7
>>> bdd.vars
{'x0': 0, 'x1': 3, 'x2': 5, 'y0': 1, 'y1': 2, 'y2': 4}
bdd.dump('after_reordering.pdf')
```

If you want to obtain a particular variable order, then give the
desired variable order as a `dict` to the function `reorder`.

```python
my_favorite_order = dict(
    x0=0, x1=1, x2=2,
    y0=3, y1=4, y2=5)
>>> len(bdd)
7
_bdd.reorder(bdd, my_favorite_order)
>>> len(bdd)
15
```

(Request such inefficient reordering only if you have some special purpose.)
You can turn [`logging`](https://docs.python.org/3/library/logging.html) to
`DEBUG`, if you want to watch reordering in action.

In some cases you might want to make some pairs of variables adjacent to
each other, but don't care about the location of each pair in the
variable order (e.g., this enables efficient variable renaming).
Use `reorder_to_pairs`.

All reordering algorithms rely on the elementary operation of swapping two
adjacent levels in the manager. You can do this by calling `BDD.swap`,
so you can implement some reordering optimization algorithm different
than Rudell's.
The difficult part to implement is `swap`, not the optimization heuristic.

The garbage collector in
[`dd.bdd.BDD.collect_garbage`](
    https://github.com/tulip-control/dd/blob/cbbc96f93da68d3d10f161ef27ccc5e3756c5ae2/dd/bdd.py#L614)
works by scanning all nodes, marking the unreferenced ones,
then collecting those (mark-and-sweep).

The function `dd.bdd.to_nx(bdd, roots)` converts the subgraph of `bdd` rooted
at `roots` to a [`networkx.MultiDiGraph`](
    https://networkx.org/documentation/stable/tutorial.html#multigraphs).

The function `dd.bdd.to_pydot(roots, bdd)` converts the BDD manager nodes
that are reachable from the BDD references in `roots` in manager `bdd` to an
instance of the class [`pydot.Dot`](https://github.com/erocarrera/pydot).


### Other methods

The remaining methods of `dd.bdd.BDD` will be of interest more to developers
of algorithms that manipulate or read the graph of BDD nodes itself.
For example, say you wanted to write a little function that explores the
BDD graph rooted at node `u`.

```python
def print_descendants_forgetful(bdd, u):
    i, v, w = bdd._succ[abs(u)]
    print(u)
    # u is terminal ?
    if v is None:
        return
    print_descendants_forgetful(bdd, v)
    print_descendants_forgetful(bdd, w)
```

In the worst case, this can take time exponential in the nodes of `bdd`.
To make sure that it takes linear time, we have to remember visited nodes

```python
def print_descendants(bdd, u, visited):
    p = abs(u)
    i, v, w = bdd._succ[p]
    # visited ?
    if p in visited:
        return
    # remember
    visited.add(p)
    print(u)
    # u is terminal ?
    if v is None:
        return
    print_descendants(bdd, v, visited)
    print_descendants(bdd, w, visited)
```

Run it with `visited = set()`.

New nodes are created with `BDD.find_or_add(level, low, high)`.
Always use this method to make a new node, because it first checks in
the *unique table* `BDD._pred` whether the node at `level` with successors
`(low, high)` already exists. This uniqueness is at the heart of reduced
ordered BDDs, the reason of their efficiency.

Throughout `dd.bdd`, nodes are frequently referred to as *edges*.
The reason is that all nodes stored are positive integers.
Negative integers signify negation, and appear only as either edges to
successors (negated edges), or references given to the user (because
a negation is popped to above the root node, for reasons of
[representation uniqueness](https://dx.doi.org/10.1145/123186.123222)).

The method `BDD.levels` returns a generator of tuples `(u, i, v, w)`,
over all nodes `u` in `BDD._succ`, where:

- `u` is a node in the iteration
- `i` is the level that `u` lives at
- `v` is the low (“else”) successor
- `w` is the high (“then”) successor

The iteration starts from the bottom (largest level), just above the terminal
node for “true” and “false” (which is `-1` in `dd.bdd`).
It scans each level, moving upwards, until it reaches the top level
(indexed with 0).

The nodes contained in the graph rooted at node `u` are `bdd.descendants([u])`.
An efficient implementation of `let` that works only for variables with
level <= the level of any variable in the support of node `u` is
`_top_cofactor(u, level)`.

Finally, `BDD.reduction` is of only academic interest.
It takes a binary decision diagram that contains redundancy in its graph
representation, and *reduces* it to the non-redundant, canonical form that
corresponds to the chosen variable order.
This is the function described originally [by Bryant](
    https://dx.doi.org/10.1109/TC.1986.1676819).

It is never used, because all BDD graphs are *constructed* bottom-up
to be reduced. To observe `reduction` in action, you have to manually
create a BDD graph that is not reduced.


## Example: Reachability analysis

We have been talking about BDDs, but you're probably here because you
want to *use* them. A common application is manipulation of Boolean functions
in the context of relations that represent dynamics, sometimes called
transition relations.

Suppose that we have an elevator that moves between three floors.
We are interested in the elevator's location, which can be at one of
the three floors. So, we can pretend that 0, 1, 2 are the three floors.

Using bits, we need at least two bits to represent the triple `{0, 1, 2}`.
Two bits can take a few too many values, so we should tell the computer that
3 is not possible in our model of the three floors.

Suppose that now the elevator is at floor `x0`, `x1`, and next at floor
`x0'`, `x1'` (read “x prime”).
The identifiers `["x0", "x1", "x0'", "x1'"]` are just four bits.
The elevator can move as follows

```python
from dd import autoref as _bdd

bdd = _bdd.BDD()
bdd.declare("x0", "x0'", "x1", "x1'")
# TLA+ syntax
s = (
    r"((~ x0 /\ ~ x1) => ( (~ x0' /\ ~ x1') \/ (x0' /\ ~ x1') )) /\ "
    r"((x0 /\ ~ x1) => ~ (x0' /\ x1')) /\ "
    r"((~ x0 /\ x1) => ( (~ x0' /\ x1') \/ (x0' /\ ~ x1') )) /\ "
    r" ~ (x0 /\ x1)")
transitions = bdd.add_expr(s)
```

We can now find from which floors the elevator can reach floor 2.
To compute this, we find the floors that either:

- are already inside the set `{2}`, or
- can reach `q` after one transition.

This looks for existence of floors, hence the existential quantification.
We enlarge `q` by the floors we found, and repeat.
We continue this backward iteration, until reaching a [least fixpoint](
    https://en.wikipedia.org/wiki/Knaster%E2%80%93Tarski_theorem)
(meaning that two successive iterates are equal).

```python
# target is the set {2}
target = bdd.add_expr(r'~ x0 /\ x1')
# start from empty set
q = bdd.false
qold = None
prime = {"x0": "x0'", "x1": "x1'"}
qvars = {"x0'", "x1'"}
# fixpoint reached ?
while q != qold:
    qold = q
    next_q = bdd.let(prime, q)
    u = transitions & next_q
    # existential quantification over x0', x1'
    pred = bdd.quantify(u, qvars, forall=False)
    q = q | pred | target
```

At the end, we obtain

```python
>>> q.to_expr()
'(! ite(x0, x1, False))'
```

which is the set `{0, 1, 2}` (it does not contain 3, because that would
evaluate to `! ite(True, True, False)` which equals `! True`, so `False`).

More about building symbolic algorithms, together with infrastructure for
arithmetic and automata, and examples, can be found in the package [`omega`](
    https://github.com/tulip-control/omega/blob/main/doc/doc.md).


## Syntax for quantified Boolean formulas

The method `BDD.add_expr` parses the following grammar.

```
       # predicate logic
expr ::= '\A' names ':' expr  # universal quantification (forall)
         '\E' names ':' expr  # existential quantification (exists)
         '\S' pairs ':' expr  # renaming of variables (substitution)

       # propositional

       # TLA+ syntax
       | '~' expr         # negation (not)
       | expr '/\' expr   # conjunction (and)
       | expr '\/' expr   # disjunction (or)
       | expr '=>' expr   # implication (implies)
       | expr '<=>' expr  # equivalence (if and only if)
       | expr '#' expr    # difference (negation of `<=>`)

       # Promela syntax
       | '!' expr         # negation
       | expr '&' expr    # conjunction
       | expr '|' expr    # disjunction
       | expr '->' expr   # implication
       | expr '<->' expr  # equivalence

       # other
       | expr '^' expr    # xor (exclusive disjunction)
       | 'ite' '(' expr ',' expr ',' expr ')'
                          # ternary conditional (if-then-else)
       | expr '=' expr    #
       | '(' expr ')'     # parentheses
       | NAME             # identifier (bit variable)
       | '@' INTEGER      # BDD node reference
       | 'FALSE' | 'False' # Boolean constant
       | 'TRUE' | 'True'   # Boolean constant

pairs ::= [pairs] ',' pair
pair ::= NAME '/' NAME

names ::= [names] ',' name
name ::= NAME

NAME ::= [A-Za-z_][A-za-z0-9_.']*
INTEGER ::= [-][0-9]*
```

Comments are written using TLA+ syntax:
- `(* this is a doubly-delimited comment *)`
- `\* this is a trailing comment`

Doubly-delimited comments can span multiple lines.

The token precedence (lowest to highest) and associativity
(r = right, l = left, n = none) is:

- `:` (l)
- `<=>, <->` (l)
- `=>, ->` (l)
- `-` (l)
- `#`, `^` (l)
- `\/, |` (l)
- `/\, &` (l)
- `=` (l)
- `~, !` (r)
- `-` (r) unary minus, as in `-5`

Both and `setup.py`, and a developer may want to force a rebuild of the
parser table. For this purpose, each module that contains a parser,
also has a function `_rewrite_tables` that deletes and rewrites the tables.
If the module is run as a script, then the `__main__` stanza calls this
function to delete and the write the parser tables to the current directory.
The parsers use [`astutils`](https://pypi.org/project/astutils/).


## Multi-valued decision diagrams (MDD)

A representation for functions from integer variables to Boolean values.
The primary motivation for implementing MDDs was to produce more readable
string and graphical representations of BDDs.
MDDs are implemented in pure Python.
The interface is “low”, similar to `dd.bdd`, with reference counting
managed by the user.
A core of necessary methods have been implemented, named as the `BDD` methods
with the same functionality in other `dd` modules.
Complemented edges are used here too.

BDDs are predicates over binary variables (two-valued).
MDDs are predicates over integer variables (multi-valued).
As expected, the data structure and algorithms for representing an MDD are
a slight generalization of those for BDDs.
For example, compare the body of `dd.mdd.MDD.find_or_add` with
`dd.bdd.BDD.find_or_add`.

The variables are defined by a `dict` argument to the constructor
(in the future, dynamic variable addition may be implemented,
by adding a method `MDD.add_var`)

```python
from dd import mdd as _mdd

dvars = dict(
    x=dict(level=0, len=4),
    y=dict(level=1, len=2))
mdd = _mdd.MDD(dvars)
```

So, variable `x` is an integer that can take values in `range(4)`.

Currently, the main use of an MDD is for more comprehensive representation of
a predicate stored in a BDD. This is achieved with the function
`dd.mdd.bdd_to_mdd` that takes a `dd.bdd.BDD` and a mapping from
MDD integers to BDD bits. Referencing of BDD nodes is necessary,
because `bdd_to_mdd` invokes garbage collection on the BDD.

```python
from dd.bdd import BDD
from dd import mdd as _mdd

bits = dict(x=0, y0=1, y1=2)
bdd = BDD(bits)
u = bdd.add_expr(r'x \/ (~ y0 /\ y1)')
bdd.incref(u)

# convert BDD to MDD
ints = dict(
    x=dict(level=1, len=2, bitnames=['x']),
    y=dict(level=0, len=4, bitnames=['y0', 'y1']))
mdd, umap = _mdd.bdd_to_mdd(bdd, ints)

# map node `u` from BDD to MDD
v = umap[abs(u)]
# complemented ?
if u < 0:
    v = - v
>>> v
    -3
s = mdd.to_expr(v)
>>> print(s)
    (! if (y in set([0, 1, 3])): (if (x = 0): 1,
    elif (x = 1): 0),
    elif (y = 2): 0)

# plot MDD with graphviz
mdd.dump('mdd.pdf')
```

Note that the `MDD` node `v` is complemented (-3 < 0), so the predicate
in the negated value computed for node `y-3` in the next image.

![example_bdd](https://rawgithub.com/johnyf/binaries/main/dd/mdd.png)


## Installation of C extension modules


### Environment variables that activate C extensions

By default, the package `dd` installs only its Python modules.
You can select to install Cython extensions using
environment variables:

- `DD_FETCH=1`: download CUDD v3.0.0 sources from the internet,
  check the tarball's hash, unpack the tarball, and `make` CUDD.
- `DD_CUDD=1`: build module `dd.cudd`, for CUDD BDDs
- `DD_CUDD_ZDD=1`: build module `dd.cudd_zdd`, for CUDD ZDDs
- `DD_SYLVAN=1`: build module `dd.sylvan`, for Sylvan BDDs
- `DD_BUDDY=1`: build module `dd.buddy`, for BuDDy BDDs

Example scripts are available that fetch and install
the Cython bindings:
- [`examples/install_dd_cudd.sh`](
    https://github.com/tulip-control/dd/blob/main/examples/install_dd_cudd.sh)
- [`examples/install_dd_sylvan.sh`](
    https://github.com/tulip-control/dd/blob/main/examples/install_dd_sylvan.sh)
- [`examples/install_dd_buddy.sh`](
    https://github.com/tulip-control/dd/blob/main/examples/install_dd_buddy.sh)


### Alternative: Directly running `setup.py`

Activating the Cython build by directly running
`python setup.py` is an alternative to
using environment variables (e.g., `export DD_CUDD=1` etc).
The relevant command-line options of `setup.py` are:

- `--fetch`: same effect as `DD_FETCH=1`
- `--cudd`: same effect as `DD_CUDD=1`
- `--cudd_zdd`: same effect as `DD_CUDD_ZDD=1`
- `--sylvan`: same effect as `DD_SYLVAN=1`
- `--buddy`: same effect as `DD_BUDDY=1`

These options work for `python setup.py sdist` and
`python setup.py install`, but directly running
`python setup.py` is deprecated by `setuptools >= 58.3.0`.

Example:

```shell
pip download dd --no-deps
tar xzf dd-*.tar.gz
pushd dd-*/
    # `pushd` means `cd`
python setup.py install --fetch --cudd --cudd_zdd
popd
```

[`pushd directory`](
    https://en.wikipedia.org/wiki/Pushd_and_popd)
is akin to `stack.append(directory)` in
Python, and `popd` to `stack.pop()`.

The path to an existing CUDD build directory
can be passed as an argument, for example:

```shell
python setup.py install \
    --fetch \
    --cudd="/home/user/cudd"
```


### Using the package `build`

The following also works for building source tarballs and wheels:

```sh
pip install cython
export DD_FETCH=1 DD_CUDD=1
python -m build --no-isolation
```

To build a source tarball:

```sh
DD_CUDD=1 python -m build --sdist --no-isolation
```


### Customizing the C compilation

If you build and install CUDD, Sylvan, or BuDDy yourself, then ensure that:

- the header files and libraries are present, and
- the compiler is configured appropriately (include,
  linking, and library configuration),

either by setting [environment variables](
    https://en.wikipedia.org/wiki/Environment_variable)
prior to calling `pip`, or by editing the file [`download.py`](
    https://github.com/tulip-control/dd/blob/main/download.py).

Currently, `download.py` expects to find Sylvan under `dd/sylvan` and
built with [Autotools](
    https://en.wikipedia.org/wiki/GNU_Build_System)
(for an example, read `.github/workflows/setup_build_env.sh`).
If the path differs in your environment, remember to update it.

If you prefer defining installation directories, then follow
[Cython's instructions](
    https://cython.readthedocs.io/en/latest/src/tutorial/clibraries.html#compiling-and-linking)
to define `CFLAGS` and `LDFLAGS` before installing.
You need to have copied `CuddInt.h` to the installation's include location
(CUDD omits it).


## Installing the development version

For installing the development version of `dd` from the `git` repository,
an alternative to cloning the repository and installing from the cloned
repository is to [use `pip` for doing so](
    https://pip.pypa.io/en/stable/cli/pip_install/#argument-handling):

```shell
pip install https://github.com/tulip-control/dd/archive/main.tar.gz
```

or with [`pip` using `git`](
    https://pip.pypa.io/en/stable/topics/vcs-support/#git)
(this alternative requires that `git` be installed):

```shell
pip install git+https://github.com/tulip-control/dd
```

A `git` URL can be passed also to [`pip download`](
    https://pip.pypa.io/en/stable/cli/pip_download/#overview),
for example:

```shell
pip download --no-deps https://github.com/tulip-control/dd/archive/main.tar.gz
```

The extension `.zip` too can be used for the name of the [archive file](
    https://en.wikipedia.org/wiki/Archive_file)
in the URL. Analogously, with `pip` using `git`:

```shell
pip download --no-deps git+https://github.com/tulip-control/dd
```

Note that the naming of paths *within* the archive file downloaded from
GitHub in this way will differ, depending on whether `https://` or
`git+https://` is used.


## Footnotes

- The `Makefile` contains the rules `sdist` and `wheel` that
  create distributions for uploading to PyPI with `twine`.

- Press `Ctrl + \` on Linux and Darwin to quit the Python process when
  CUDD computations take a long time. Read `stty -a` for your settings.

- To use `Ctrl + C` (`KeyboardInterrupt`) to interrupt CUDD computations
  that take a long time, install `cysignals`, then build `dd.cudd`.

- If you are interested in exploring other decision diagram packages,
  you can find [a list at `github.com/johnyf/tool_lists/`](
    https://github.com/johnyf/tool_lists/blob/main/bdd.md).


## Copying

This document is copyright 2015-2021 by California Institute of Technology.
All rights reserved. Licensed under 3-clause BSD.
