# `dd` documentation


## Design principles

The interface is in Python. The representation depends on what you want and have installed. For solving small to medium size problems, say for teaching, or develop algorithms using BDDs, you will likely want to use pure Python. For working with larger problems, you need to install [CUDD](https://vlsi.colorado.edu/~fabio/), which is written in C. Lets call these “backends”.

The same user code can run with both the Python and C backends.
You only need to modify an `import dd.autoref as _bdd` to `import.cudd as _bdd`, or import conditionally, e.g.,

```python
try:
    import dd.cudd as _bdd
except ImportError:
    import dd.autoref as _bdd
```

The following sections describe how to use the high level interface (almost identical in `autoref` and `cudd`). The lower level interface to the pure-Python implementation in `dd.bdd` is also described, for those interested in refined control of the diagrams.


## Create and plot a binary decision diagram

The starting point for using a BDD library is a *shared* reduced ordered binary decision diagram. Implementations call this *manager*. The adjectives mean:

- binary: a node represents a set, interpreting a propositional formula
- ordered: variables have a fixed order that can change only when instructed to do so
- reduced: a unique BDD is associated to each set
- shared: different sets are represented using common elements in memory.

The manager is a directed graph, with each node representing a set.
Each such set is understood as a collection of assignments to variables.
As mentioned above, the variables are ordered.
The *level* of a variable is its index in this order, starting from 0.
The *terminal* nodes correspond to true and false, with maximal index.

Each manager is a `BDD` class, residing in a different module:

- `dd.autoref.BDD`: high-level interface to pure Python implementation
- `dd.cudd.BDD`: same high-level interface to C implementation
- `dd.bdd.BDD`: low-level interface to pure Python implementation (wrapped by `dd.autoref.BDD`.

Besides the class `BDD`, each module contains also related functions that are compatible with the interface implemented there.
The difference between these modules is how a BDD node is represented.
In `autoref` and `cudd`, a `Function` class represents a node.
In `bdd`, a signed integer represents a node.

All representations use negated edges, so logical negation takes *constant* time.


### Initialize a `BDD` manager

First, instantiate a manager with variables

```python
from dd import autoref as _bdd

bdd = _bdd.BDD()
bdd.add_var('x')
```

The keyword arguments of `BDD.add_var` differ between `autoref` and `cudd`, see the docstring.
The BDD node for variable `x` is

```python
u = bdd.var('x')
```

This does not invoke the parser, so it is more efficient (inside intensive loops).
An alternative that invokes the parser is

```python
u = bdd.var('x')
```

What type `u` has depends on the module used:

- `autoref`: `autoref.Function`
- `cudd`: `cudd.Function`
- `bdd`: `int`

To confirm consistency, we can check whether

```python
assert u in bdd, u
```

The number of (referenced) nodes in the manager `bdd` is `len(bdd)`.
As noted earlier, each variable corresponds to a level, which is an index in the variable order. This mapping can be obtained with

```python
level = bdd.level_of_var('x')
var = bdd.var_at_level(level)
assert var == 'x', var
```

The `dict` that maps each defined variable to its corresponding level can be obtained also from the attribute `BDD.vars`

```python
bdd = _bdd.BDD()
bdd.add_var('x')
bdd.add_var('y')
bdd.add_var('z')
>>> bdd.vars
{'x': 0, 'y': 1, 'z': 2}
```

The Boolean constants are `bdd.false` and `bdd.true`.
These attributes return a BDD node equal to the selected constant.
In `dd.bdd.BDD`, this node is `+1` (true) or `-1` (false).
But in `dd.autoref` and `dd.cudd` this is not the case, which is why these attributes exist.


### Working with BDDs

The methods available can be loosely distinguished by purpose.
Below, this is implicit in the order of presentation.

Most frequently, you will use Boolean operators.
There are three ways to do this:

- overloaded Python operators `~, |, &` between `Function` objects (not in `dd.bdd`)
- `BDD.apply()`
- `BDD.add_expr()`

If you do not use the first variant, then your code will most likely run with any of `dd.autoref`, `dd.cudd`, or `dd.bdd`.
Otherwise, it will not run with `dd.bdd`, because nodes there are plain `int`.

For example:

```python
from dd import autoref as _bdd

bdd = _bdd.BDD()
for var in ('x', 'y'):
	bdd.add_var(var)

x = bdd.var('x')
y = bdd.var('y')

u = x & y
u = bdd.apply('and', x, y)
u = bdd.apply('&', x, y)
u = bdd.add_expr('x & y')
```

Note that the last variant does invoke the [`ply.yacc`](https://github.com/dabeaz/ply)-generated parser.
The inverse of `BDD.add_expr` is `BDD.to_expr`:

```python
u = bdd.add_expr('x & y')
s = bdd.to_expr(u)
>>> s
'ite(x, y, False)'
```

Lets create the BDD of a more colorful Boolean formula

```python
bdd.add_var('z')
s = '(x & y) <-> (! z | (y ^ x))'
v = bdd.add_expr(s)
```

In natural language, the expression `s` reads: “(x and y) if and only if ( (not z) or (y xor x) )”.
Besides the method `apply`, there is also an if-then-else method `ite`, but that is more commonly used internally to the package, rather than externally.

A node represents a set of assignments of values to variables.
An assignment of values to (all the) variables is also called a *model*.
A model is represented as a `dict` that maps variable names to values.
It doesn't have to mention all variables, just enough for that node.

Lets look closer at this with an example.

```python
[bdd.add_var(var) for var in ['x', 'y', 'z']]

u = bdd.add_expr('x | y')
support = bdd.support(u)
>>> support
{'x', 'y'}
```

This tells us that membership in the set described by the expression `x | y` depends on the values of the variables `x` and `y`.
The values of other variables, like `z`, are irrelevant to evaluating the expression `x | y`.

This brings up the matter of function domain, a common pitfall when implementing symbolic algorithms.
To each set corresponds an “indicator function”, which maps each member of the set to true, and everything else to false.
For the set described by the expression `x | y`, the indicator function is described by the same expression.

A function has a domain.
Two functions can be described by the same expression, but have different domains.
For example, the function `x & y` with domain (all the assignments to) the variables `{'x', 'y', 'z'}` is different from the function `x & y` with domain (all the assignments to) the variables `{'x', 'y'}`.
The first function contains the elements `dict(x=True, y=True, z=True)` and `dict(x=True, y=True, z=False)`, whereas the second function contains only the element `dict(x=True, y=True)`.

The choice of domain does not frequently come up, but when it does, it can be difficult to explain the resulting bug.
It does matter when enumerating the assignments in the set corresponding to node `u`.
For example:

```python
[bdd.add_var(var) for var in ['x', 'y']]

u = bdd.add_expr('x')
n = bdd.sat_len(u)
>>> n
2
models = list(bdd.sat_iter(u))
>>> models
[{'x': True}]
```

Notice that `sat_len` says that there are two models, but the generator returned by `sat_iter` produces only one, `dict(x=True)`.
Where did the other model go?

As the docstring of `sat_iter` explains, by default, it returns partially enumerated models.
In other words, it enumerates only variables in the support of `u`, here `x`, because the expression `x` does not depend on variable `y`.
We can request a full enumeration (over all bits, or only `care_bits` more):

```python
models = list(bdd.sat_iter(u, full=True))
>>> models
[{'x': True, 'y': False}, {'x': True, 'y': True}]
```

A convenience method for creating a BDD from an assignment `dict` is

```python
d = dict(x=True, y=False, z=True)
u = bdd.cube(d)
v = bdd.add_expr('x & !y & z')
assert u == v, (u, v)
```

To substitute some variables for some other variables

```python

[bdd.add_var(var) for var in ['x', 'p', 'y', 'q', 'z']]
u = bdd.add_expr('x | y & z')
d = dict(x='p', y='q')
v = bdd.rename(u, d)
>>> bdd.support(v)
{'p', 'q', 'z'}
```

In `autoref`, renaming is supported between adjacent variables.
To copy a node from one BDD manager to another manager

```python
a = _bdd.BDD()
[a.add_var(var) for var in ['x', 'y', 'z']]
u = a('(x & y) | z')

b = _bdd.BDD()
_bdd.copy_vars(a, b)
v = a.copy(u, b)
```

Some less frequently used `BDD` methods are `assert_consistent`, `evaluate`, `compose`, `cofactor`, and `collect_garbage`.

In `autoref`, a few functions (not methods) are available for efficient operations that arise naturally in fixpoint algorithms when transition relations are involved:

- `image`, `preimage`: rename some variables, conjoin, existentially quantify, and rename some variables, all at once
- `copy_vars`: copy the variables of one BDD manager to another manager

and deprecated (use the methods `BDD.rename`, `BDD.copy`):

- `rename`: substitute some variables for some other variables
- `copy_bdd`: copy a node from one BDD manager to another manager (deprecated.

For the curious, the attribute `dd.autoref.BDD._bdd` is the `dd.bdd.BDD` wrapped by `dd.autoref.BDD`.


### Quantified formulae

You can create BDDs from quantified formulae

```python
bdd.add_var('x')
bdd.add_var('y')
bdd.add_var('z')

# there exists x, such that (x and y)
u = bdd.add_expr('\E x: x & y')
y = bdd.var('y')
assert u == y, (u, y)

# forall x, there exists y, such that (y or x)
u = bdd.add_expr('\A x: \E y: y | z')
assert u == bdd.true, u
```

Besides variable identifiers, integers that are BDD nodes can be used too.
Currently, reference to a BDD node as an integer is only availabel for `dd.bdd.BDD`, because of the internal representation there.

```python
from dd.bdd import BDD

bdd = BDD()
u = bdd.add_var('x')
x = bdd.var('x')
y = bdd.var('y')

s = 'x & {r}'.format(r=y)
u = bdd.add_expr(s)
u_ = bdd.add_expr('x & y')
assert u == u_
```

This approach is useful for writing more readable library code.
However, it invokes the parser. Inside intensive loops, this can add a considerable overhead. In those cases, use `BDD.apply` or `~, &, |`, and `BDD.quantify`.
In the future, a compiler may be added, to compile expressions into functions that can be called multiple times, without invoking again the parser.


### Plotting

With `pydot` present (or by using `dd.bdd.to_nx` and then some `networkx` plotting), you can dump a PDF of all nodes in the manager:

```python
from dd import autoref as _bdd

bdd = _bdd.BDD()
bits = ('x', 'y', 'z')
for var in bits:
	bdd.add_var(var)
u = bdd.add_expr('(x & y) | !z')
bdd.collect_garbage()
bdd.dump('awesome.pdf')
```

The result is show below, with the legend:

- integers on the left signify levels (thus variables)
- each node is annotated with a variable name (like `x`) dash the node index in `dd.bdd.BDD._succ` (mainly for debugging purposes)
- solid arcs represent the “if” branches
- dashed arcs the “else” branches
- only an “else” branch can be negated, signified by a `-1` annotation

Negated edges mean that logical negation, i.e., `!`, is applied to the node that is pointed to.
Negated edges and BDD theory won't be discussed here, please refer to a reference from those listed in the `dd.bdd` module's docstring, like [this document](https://www.ecs.umass.edu/ece/labs/vlsicad/ece667/reading/somenzi99bdd.pdf) by Fabio Somenzi (CUDD's author).

![example_bdd](https://rawgithub.com/johnyf/binaries/master/dd/awesome.png)

It is instructive to dump the `bdd` with, and without collecting garbage after `add_expr`.


### Pickle

The `dd.autoref` and `dd.bdd` modules can dump the manager to a [pickle file](https://en.wikipedia.org/wiki/Pickle_%28Python%29) and load it back

```python
bdd.dump('manager.p')
```

and later, or in another run:

```python
bdd = BDD.load('manager.p')
```


### Nodes as `Function` objects

As mentioned earlier, the main difference between the main `dd` modules is what type of object the user sees as a “node”:

- `dd.bdd` gives to the user signed integers as nodes
- `dd.autoref` and `dd.cudd` give her `Function` objects as nodes.

Seldom should this make a difference to the user.
However, for integers, the meaning of the Python operators `~`, `&`, `|`, `^` is unrelated to the BDD manager.
So, if `u = -3` and `v = 25` are nodes in the `dd.bdd.BDD` manager `bdd`, you cannot write `w = u & v` to get the correct result.
You have to use either:

- `BDD.apply('and', u, v)` or
- `BDD.add_expr('{u} & {v}'.format(u=u, v=v))`.

Unlike `dd.bdd`, the nodes in `autoref` and `cudd` are of class `Function`.
This abstracts away the underlying node representation, so that you can run the same code in both pure Python (with `dd.bdd.BDD` underneath as manager), as well as C (with the `struct` named [`DdManager`](https://github.com/johnyf/cudd/blob/80c9396b7efcb24c33868aeffb89a557af0dc356/cudd/cudd/cudd.h#L281) in `cudd.h` underneath as manager).

The [magic methods](https://github.com/RafeKettler/magicmethods) for `~`, `&`, `|`, `^` implemented by `Function` are its most frequently used aspect.
Two methods called `implies` and `bimplies` are available.
But it is more readable to use `bdd.apply` or `bdd.add_expr`, or just `v | ~ u` for `u.implies(v)` and `~ (u ^ v)` for `u.bimplies(v)`.


#### BDD equality

If `u` and `v` are instances of `Function`, and `u == v`, then `u` represents the same BDD as `v`.

This is **NOT** true for nodes in `dd.bdd`, because `u` and `v` may be nodes from *different* manager instances.
So, that `u == -3 == v` does not suffice to deduce that `u` and `v` represent the same BDD.
In this case, we have to ensure that `u` and `v` originate from the same manager.
Thus, using `dd.bdd` offers less protection against subtle errors that will go undetected.


#### Other methods

Information about a node `u` can be read with a few attributes and magic:

- `len(u)` is the number of nodes in the graph that represents `u` in memory
- `u.var` is the name (`str`) of the variable in `BDD.support(u)` with minimal level (recall that variables are ordered)
- `u.level` is the level of `u.var`
- `u.ref` is the reference count of `u`, meaning the number of other nodes `v` with an edge `(v, u)`, plus external references to `u` by the user.

We say that the node `u` is “labeled” with variable `u.var`.
At this point, recall that these diagrams track *decisions*.
At each node, we decide where to go next, depending on the value of `u.var`.
If `u.var` is true, then we go to node `u.high`, else to node `u.low`.
For this reason, `u.high` is also called the “then” child of `u`, and `u.low` the “else” child.

This object-oriented appearance is only an external interface for the user's convenience.
Typically, the bulk of the nodes aren't referenced externally.
Internally, the nodes are managed efficiently en masse, no `Function`s there.
A `Function.to_expr` method is present, but using `BDD.to_expr` looks tidier.


## CUDD interface: `dd.cudd`

We said earlier that you can develop with `autoref`, deferring usage of `CUDD` for when really needed.
This raises two questions:

1. Why not use `cudd` from the start ?
2. When should you switch from `autoref` to `cudd` ?

The answer to the second question is simple: when your problem takes more time and memory than you are willing to invest.
For light to moderate use, `cudd` probably won't be needed.

Regarding the first question, `dd.cudd` requires to:

- *compile* CUDD, and
- *cythonize, compile, and link* `dd/cudd.pyx`.

The `setup.py` of `dd` can do these for you, as described in the file [`README.md`](https://github.com/johnyf/dd/blob/master/README.md#cython-bindings).
However, this may require more attention than appropriate for the occassion.
An example is teaching BDDs in a class on data structures, with the objective for students to play with BDDs, not with [`gcc`](https://en.wikipedia.org/wiki/GNU_Compiler_Collection) and [linking](https://en.wikipedia.org/wiki/Linker_%28computing%29) errors (that's enlightening too, but in the realm of a slightly different class).

If you are interested in tuning CUDD to get most out of it (or because some problem demands it due to its size), then use:

- `BDD.statistics` to obtain the information described in [CUDD Programmer's manual / Gathering and interpreting statistics](https://vlsi.colorado.edu/~fabio/CUDD/node4.html#SECTION00048000000000000000).
- `BDD.configure` to read and set the parameters 	“max memory”, “loose up to”, “max cache hard”, “min hit”, and “max growth”.

Due to how CUDD manages variables, `add_var` takes as keyword argument the variable index, *not* the level (which `autoref` does).
The level can still be set with the method `insert_var`.
For now, these are two separate methods.
They may be unified or modified in the future, to improve the interface.

The methods `dump` and `load` store the BDD of a selected node in a DDDMP file.
Pickling and PDF plotting are not available yet in `dd.cudd`.

Some methods present in `autoref.BDD` are not (yet) implemented in the `cudd.BDD` interface.
These are:
- `evaluate` (use `cofactor`)
- `ite`
- `sat_len`
- `collect_garbage` (shouldn't need this if automated reordering enabled).
With time, most of these will appear.

An interface to the BuDDy C libary also exists, as `dd.buddy`.
However, experimentation suggests that BuDDy does not contain as successful heuristics for deciding *when* to invoke reordering.

CUDD is initialized with a `memory_estimate` of 1 GB. If the machine has RAM, then `cudd.BDD` will raise an error. In this case, pass a smaller initial memory estimate, for example `cudd.BDD(memory_estimate=0.5 * 2**30)`.


### Functions

The functions `and_exists`, `or_forall`, and `rename` in `dd.cudd` offer the functionality of relational products (meaning neighboring variable substitution, conjunction, and quantification, all at one pass over BDDs).
This functionality is implemented with `image`, `preimage` and `rename` in `dd.autoref`.
Note that (pre)image contains substitution, unlike `and_exists`.

Renaming in `autoref` is more efficient.
The function `cudd.rename` handles renames to variables not in the support.
The function `cudd.compose` handles arbitrary renames, with the associated complexity of vector composition within CUDD.

The function `cudd.reorder` is similar to `autoref.reorder`, but does not default to invoking automated reordering.
Typical use of CUDD enables dynamic reordering.


## Lower level: `dd.bdd`

We discuss now some more details about the pure Python implementation in `dd.bdd`.
To avoid running out of memory, a BDD manager deletes nodes when they are not used anymore.
This is called [garbage collection](https://en.wikipedia.org/wiki/Garbage_collection_%28computer_science%29).
So, two things have to happen:

1. keep track of node “usage”
2. invoke garbage collection

Garbage collection is invoked automatically only in `dd.cudd`.
Node usage is tracked with reference counting, for each node.
In `autoref`, the reference counts are maintained by the constructor and destructor methods of `Function` (hence the “auto”).
These methods are invoked when the `Function` object is not referenced any more by variables, so [Python decides](https://docs.python.org/2/glossary.html#term-garbage-collection) to delete it.

In `dd.bdd`, you have to perform the reference counting, by suitably adding to and subtracting from the counter associated to the node you reference.
Also, garbage collection has to be explicitly invoked (or as a side-effect of explicitly invoking reordering).
So, if you don't need to collect garbage, then you can skip the reference counting.


### Reference counting

The reference counters live inside [`dd.bdd.BDD._ref`](https://github.com/johnyf/dd/blob/cbbc96f93da68d3d10f161ef27ccc5e3756c5ae2/dd/bdd.py#L81).
To guard against corner cases, like attempting to decrement a zero counter, use

- [`BDD.incref(u)`](https://github.com/johnyf/dd/blob/cbbc96f93da68d3d10f161ef27ccc5e3756c5ae2/dd/bdd.py#L126): +1 to the counter of node `u`
- [`BDD.decref(u)`](https://github.com/johnyf/dd/blob/cbbc96f93da68d3d10f161ef27ccc5e3756c5ae2/dd/bdd.py#L130): -1 to the same counter.

The method names `incref` and `decref` originate from the [Python reference counting](https://docs.python.org/2/c-api/refcounting.html) implementation.
If we want node `u` to persist after garbage collection, then it needs to be actively referenced at least once

```python
u = bdd.add_expr(s)
bdd.incref(u)
```

Revisiting an earlier example, manual reference counting looks like:

```python
from dd import bdd as _bdd

bdd = _bdd.BDD()
bits = ['x', 'y', 'z']
for var in bits:
	bdd.add_var(var)
s = '(x & y) | !z'
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
u = bdd.add_expr('x & y')

c = 'x' in bdd.support(u)  # more readable
c_ = bdd.is_essential(u, 'x')  # slightly more efficient
assert c == True, c
assert c == c_, (c, c_)

c = 'z' in bdd.support(u)
assert c == False, c
```


### Reordering

Given a BDD, the size of its graph representation depends on the variable order.
Reordering changes the variable order.
Reordering *optimization* searches for a variable order better than the current one.
*Dynamic* reordering is the automated invocation of reordering optimization.
The time of invocation is decided with heuristics, because it is [NP-hard](https://en.wikipedia.org/wiki/NP-hardness) to find the variable order that minimizes a given BDD.

[Rudell's sifting algorithm](http://www.eecg.toronto.edu/~ece1767/project/rud.pdf) is implemented in the function `dd.bdd.reorder`.
This is the most commonly used reordering heuristic, also in CUDD.
For now, if you want to reorder, then you have to explicitly call the function `reorder`.
It will not be invoked automatically.
For example

```python
from dd import bdd as _bdd

bdd = _bdd.BDD()
vars = ['x{i}'.format(i=i) for i in range(3)]
vars.extend('y{i}'.format(i=i) for i in range(3))
for var in vars:
    bdd.add_var(var)
>>> bdd.vars
{'x0': 0, 'x1': 1, 'x2': 2, 'y0': 3, 'y1': 4, 'y2': 5}

s = '(x0 & y0) | (x1 & y1) | (x2 & y2)'
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

In the future, a heuristic for automated invocation will be added, which requires minor modifications to make computation re-entrant.

Instead, if you want to obtain a particular order, then give it as a `dict` to the function `reorder`.

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
You can turn [`logging`](https://docs.python.org/2/library/logging.html) to `DEBUG`, if you want to watch reordering in action.

In some cases you might want to make some pairs of variables adjacent to each other, but don't care about the location of each pair in the variable order (e.g., this is enables efficient variable renaming).
Use `reorder_to_pairs`.

All reordering algorithms rely on the elementary operation of swapping two adjacent levels in the manager.
You can do this by calling `BDD.swap`, so you can implement some reordering optimization algorithm different than Rudell's.
The difficult part to implement is `swap`, not the optimization heuristic.

The garbage collector in [`dd.bdd.BDD.collect_garbage`](https://github.com/johnyf/dd/blob/cbbc96f93da68d3d10f161ef27ccc5e3756c5ae2/dd/bdd.py#L614) works by scanning all nodes, marking the unreferenced ones, then collecting those (mark-and-sweep).

The function `dd.bdd.to_nx(bdd, roots)` converts the subgraph of `bdd` rooted at `roots` to a [`networkx.MultiDiGraph`](http://networkx.github.io/documentation/latest/tutorial/tutorial.html#multigraphs).

The function `to_pydot(bdd)` converts the manager `bdd` to a [`pydot`](https://github.com/erocarrera/pydot) graph.
Currently, `pydot` is registered, but not uploaded to PyPI, so it has to be fetched from its development site.


### Other methods

The remaining methods of `dd.bdd.BDD` will be of interest more to developers of algorithms that manipulate or read the graph of BDD nodes itself.
For example, say you wanted to write a little function that explores the BDD graph rooted at node `u`.

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
Always use this method to make a new node, because it first checks in the *unique table* `BDD._pred` whether the node at `level` with successors `(low, high)` already exists.
This uniqueness is at the heart of reduced ordered BDDs, the reason of their efficiency.

Throughout `dd.bdd`, nodes are frequently referred to as *edges*.
The reason is that all nodes stored are positive integers.
Negative integers signify negation, and appear only as either edges to successors (negated edges), or references given to the user (because a negation is popped to above the root node, for reasons of [representation uniqueness](https://dx.doi.org/10.1145/123186.123222)).

The method `BDD.levels` returns a generator of tuples `(u, i, v, w)`, over all nodes `u` in `BDD._succ`, where:

- `u` is a node in the iteration
- `i` is the level that `u` lives at
- `v` is the low (“else”) successor
- `w` is the high (“then”) successor

The iteration starts from the bottom (largest level), just above the terminal node for “true” and “false” (which is `-1` in `dd.bdd`).
It scans each level, moving upwards, until it reaches the top level (indexed with 0).

The nodes contained in the graph rooted at node `u` are `bdd.descendants([u])`.
An efficient implementation of cofactor that works only for variables with level <= the level of any variable in the support of node `u` is `_top_cofactor(u, level)`.

Finally, `BDD.reduction` is of only academic interest.
It takes a binary decision diagram that contains redundancy in its graph representation, and *reduces* it to the non-redundant, canonical form that corresponds to the chosen variable order.
This is the function described originally [by Bryant](https://dx.doi.org/10.1109/TC.1986.1676819).

It is never used, because all BDD graphs are *constructed* bottom-up to be reduced.
To observe `reduction` in action, you have to manually create a BDD graph that is not reduced.


## Example: Reachability analysis

We have been talking about BDDs, but you're probably here because you want to *use* them.
A common application is manipulation of Boolean functions in the context of relations that represent dynamics, sometimes called transition relations.

Suppose that we have an elevator that moves between three floors.
We are interested in the elevator's location, which can be at one of the three floors.
So, we can pretend that 0, 1, 2 are the three floors.

Using bits, we need at least two bits to represent the triple `{0, 1, 2}`.
Two bits can take a few too many values, so we should tell the computer that 3 is not possible in our model of the three floors.

Suppose that now the elevator is at floor `x0`, `x1`, and next at floor `x0'`, `x1'` (read “x prime”).
The identifiers `["x0", "x1", "x0'", "x1'"]` are just four bits.
The elevator can move as follows

```python
from dd import autoref as _bdd

bdd = _bdd.BDD()
dvars = ["x0", "x0'", "x1", "x1'"]
for var in dvars:
    bdd.add_var(var)
s = (
    "((!x0 & !x1) -> ( (!x0' & !x1') | (x0' & !x1') )) & "
    "((x0 & !x1) -> ! (x0' & x1')) & "
    "((!x0 & x1) -> ( (!x0' & !x1') | (x0' & x1') )) & "
    "! (x0 & x1)")
transitions = bdd.add_expr(s)
```

We can now find from which floors the elevator can reach floor 2.
To compute this, we find the floors that either:

- are already inside the set `{2}`, or
- can reach `q` after one transition.

This looks for existence of floors, hence the existential quantification.
We enlarge `q` by the floors we found, and repeat.
We continue this backward iteration, until reaching a [least fixpoint](https://en.wikipedia.org/wiki/Knaster%E2%80%93Tarski_theorem) (meaning that two successive iterates are equal).

```python
# target is the set {2}
target = bdd.add_expr('!x0 & x1')
# start from empty set
q = bdd.false
qold = None
prime = {"x0": "x0'", "x1": "x1'"}
qvars = {"x0'", "x1'"}
# fixpoint reached ?
while q != qold:
    qold = q
    next_q = _bdd.rename(q, bdd, prime)
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

which is the set `{0, 1, 2}` (it does not contain 3, because that would evaluate to `! ite(True, True, False) = ! True = False`).

More about building symbolic algorithms, together with infrastructure for arithmetic and automata, and examples, can be found in the package [`omega`](https://github.com/johnyf/omega/blob/master/doc/doc.md).


## Syntax for quantified Boolean formulae

The method `BDD.add_expr` parses the following grammar.

```
       # first-order
expr ::= '\A' names ':' expr  # universal quantification (forall)
         '\E' names ':' expr  # existential quantification (exists)
         '\S' pairs ':' expr  # renaming of variables (substitution)

       # propositional
       | '!' expr         # negation (not)
       | expr '&' expr    # conjunction (and)
       | expr '|' expr    # disjunction (or)
       | expr '^' expr    # xor (exclusive disjunction)
       | expr '->' expr   # implication (implies)
       | expr '<->' expr  # equivalence (if and only if)
       | 'ite' '(' expr ',' expr ',' expr ')'
                          # ternary conditional (if-then-else)
       | expr '=' expr    #
       | expr '!=' expr   #
       | '(' expr ')'     # parentheses
       | NAME             # identifier (bit variable)
       | INTEGER          # BDD node (only for `dd.bdd.BDD`)
       | 'False'          # Boolean constant
       | 'True'           # Boolean constant

pairs ::= [pairs] ',' pair
pair ::= NAME '/' NAME

names ::= [names] ',' name
name ::= NAME

NAME ::= [A-Za-z_][A-za-z0-9_.']*
INTEGER ::= [0-9]*
```

Trailing comments can be added using a hashmark, for example `# this is comment`.

The token precedence (lowest to highest) and associativity (r = right, l = left, n = none) is:

- `:` (l)
- `<->` (l)
- `->` (l)
- `-` (l)
- `^` (l)
- `|` (l)
- `&` (l)
- `=`, `!=` (l)
- `!` (r)
- `-` (r) unary minus, as in `-5`

Both and `setup.py`, and a developer may want to force a rebuild of the parser table.
For this purpose, each module that contains a parser, also has a function `_rewrite_tables` that deletes and rewrites the tables.
If the module is run as a script, then the `__main__` stanza calls this function to delete and the write the parser tables to the current directory.
The parsers use [`astutils`](https://pypi.python.org/pypi/astutils).


## Multi-valued decision diagrams (MDD)

A representation for functions from integer variables to Boolean values.
The primary motivation for implementing MDDs was to produce more readable string and graphical representations of BDDs.
MDDs are implemented in pure Python.
The interface is “low”, similar to `dd.bdd`, with reference counting managed by the user.
A core of necessary methods have been implemented, named as the `BDD` methods with the same functionality in other `dd` modules.
Complemented edges are used here too.

BDDs are predicates over binary variables (two-valued).
MDDs are predicates over integer variables (multi-valued).
As expected, the data structure and algorithms for representing an MDD are a slight generalization of those for BDDs.
For example, compare the body of `dd.mdd.MDD.find_or_add` with `dd.bdd.BDD.find_or_add`.

The variables are defined by a `dict` argument to the constructor (in the future, dynamic variable addition may be implemented, by adding a method `MDD.add_var`)

```python
from dd import mdd as _mdd

dvars = dict(
    x=dict(level=0, len=4),
    y=dict(level=1, len=2))
mdd = _mdd.MDD(dvars)
```

So, variable `x` is an integer that can take values in `range(4)`.

Currently, the main use of an MDD is for more comprehensive representation of a predicate stored in a BDD.
This is achieved with the function `dd.mdd.bdd_to_mdd` that takes a `dd.bdd.BDD` and a mapping from MDD integers to BDD bits.
Referencing of BDD nodes is necessary, because `bdd_to_mdd` invokes garbage collection on the BDD.

```python
from dd.bdd import BDD
from dd import mdd as _mdd

bits = dict(x=0, y0=1, y1=2)
bdd = BDD(bits)
u = bdd.add_expr('x | (!y0 & y1)')
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
pd = _mdd.to_pydot(mdd)
pd.write_pdf('mdd.pdf')
```

Note that the `MDD` node `v` is complemented (-3 < 0), so the predicate in the negated value computed for node `y-3` in the next image.

![example_bdd](https://rawgithub.com/johnyf/binaries/master/dd/mdd.png)


## Footnotes

If you are interested in exploring other decision diagram packages, you can find [a list at `github.com/johnyf/tool_lists/`](https://github.com/johnyf/tool_lists/blob/master/bdd.md).
