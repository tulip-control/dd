# dd changelog


## 0.4.0

- require `pydot >= 1.2.2`


API:

- change quantification syntax to `\E x, y: x`
- add renaming syntax `\S x / y,  z / w: y & w`
- class `BDD` in `dd.bdd`, `dd.autoref`, `dd.cudd`:
  - add operators `'ite', '\E', '\A'` to method `apply`
  - add methods `forall` and `exist` as wrappers of `quantify`
  - add method `_add_int` for checking presence of
    a BDD node represented as an integer
  - add method `succ` to obtain `(level, low, high)`
- class `cudd.BDD`:
  - add method `compose`
  - add method `ite`
  - add method `to_expr`
- class `cudd.Function`:
  - add method `__int__` to represent CUDD nodes
    uniquely as integers (by shifting the C pointer value to
    avoid possible conflicts with reserved values)
  - add method `__str__` to return integer repr as `str`
  - add attribute `level`
  - add attribute `negated`
- module `cudd`:
  - add function `restrict`
  - add function `count_nodes`
- remove "extra" named `dot`, because `pydot` is now required


## 0.3.1

BUG:

- `dd.bdd.BDD.dump`: if argument `roots is None` (default),
  then dump all nodes
- `dd.autoref.BDD.compose`: call wrapped method correctly


## 0.3.0

API:

- `dd.bdd.BDD.rename`, `dd.bdd.image`, `dd.bdd.preimage`: allow non-adjacent variable levels
- `dd.bdd.BDD.descendants`:
  - arg `roots` instead of single node `u`
  - iteration instead of recursion
  - breadth-first instead of depth-first search
- `dd.bdd.BDD.dump`:
  - dump nodes reachable from given roots
  - dump only variable levels and nodes to pickle file
  - correct error that ignored explicit file type for PDF, PNG, SVG
- `dd.bdd.BDD.load`:
  - instance method to load nodes
- `dd.bdd.to_pydot`:
  - add arg `roots`
- hide methods that dump and load entire manager
  - `dd.bdd.BDD._dump_manager` and `_load_manager`
- remove `dd.autoref.Function.from_expr`


## 0.2.2

- install without extensions by default
- try to read git information, but assume release if this fails for any reason


## 0.2.1

- optionally import `gitpython` in `setup.py` to retrieve
  version info from `git` repo.
- version identifier when `git` available:
  `X.Y.Z.dev0+SHA[.dirty]`
- require `psutil >= 3.2.2`
- require `setuptools >= 19.6` to avoid `cython` affecting `psutil` build
- detect 64-bit system using `ctypes.sizeof` for CUDD flags

API:

- `dd.cudd.BDD.__cinit__`:
  - rename arg `memory` -> `memory_estimate`
  - assert memory estimate less than `psutil.virtual_memory().total`
  - add arg `initial_cache_size`
- `dd.cudd.BDD.statistics`:
  - distinguish between peak and live nodes
  - cache statistics
  - unique table statistics
  - read node count w/o removing dead nodes
- `dd.cudd.BDD.configure`:
  - accept keyword args, instead of `dict`
  - first read config (returned `dict`), then set given values
  - reordering
  - garbage collection
  - max cache soft
  - max swaps
  - max variables per reordering
- `dd.bdd`, `dd.autoref`, `dd.cudd`:
  - add method `BDD.copy` for copying nodes between managers
  - add method `BDD.rename` for substituting variables
  - deprecate functions `rename` and `copy_bdd`
- add method `dd.cudd.BDD.sat_iter`
- add function `dd.cudd.count_nodes_per_level`
- add functions that track variable order when saving:
  - `dd.cudd.dump`
  - `dd.cudd.load`


## 0.2.0

- add user documentation
- support Python 3
- require `pydot3k` in Python 3, `pydot` in Python 2
- expose more control over CUDD configuration

API:

- add `dd.cudd.BDD.configure`
- do not set manager parameters in `__cinit__`
- rename `BDD.False` -> `BDD.false` (same for “true”), to avoid syntax errors in Python 3
- remove `dd.bdd.BDD.add_ast`
- `dd.cudd.reorder` invokes sifting if variable order is `None`
- default to pickle protocol 2


## 0.1.3

Bugfix release to add file `download.py` missing from MANIFEST.

API:

- add `dd.cudd.BDD.statistics`
- add functions `copy_vars` and `copy_bdd`
- remove `dd.bdd.BDD.level_to_variable`


## 0.1.2

- add Cython interface `dd.cudd` to CUDD
- add Cython interface `dd.buddy` to BuDDy


## 0.1.1

- dynamic variable addition in `dd.bdd.BDD`
- add `dd.autoref` wrapper around `dd.bdd`
- avoid randomization inside `sat_iter`

API:

- add `BDD.True` and `BDD.False`
- move `Function` interface to `dd.autoref`
- move parser to `dd._parser`
- rename `BDD.level_to_variable` -> `var_at_level`
- deprecate `BDD.ordering` in favor of `BDD.vars`


## 0.0.4

- add `dd.mdd` for multi-terminal decision diagrams
- add quantifiers to syntax
- add complemented edges to syntax
- require `networkx`

API:

- add `dd.bdd.BDD.cube`
- add `dd.bdd.BDD.descendants`
- add function `reorder_pairs`


## 0.0.3

- add PLY parser for Boolean expressions
- require `astutils`

API:

- add `dd.bdd.BDD.ref`
- assign `bool` as model values


## 0.0.2

- test on Travis

API:

- add `"diff"` operator to `dd.bdd.BDD.apply`


## 0.0.1

Initial release.
