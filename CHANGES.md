# dd changelog


## 0.6.1

- DEP: rm module `dd._compat`


## 0.6.0

- REL: require Python >= 3.11
- REL: require `cython >= 3.0.0`
- REL: require `astutils >= 0.0.5`
- DEP: deprecate hidden module `dd._compat`

API:

- use TLA+ syntax for comments:
  - `(* this is a doubly-delimited comment *)`
  - `\* this is a trailing comment`
- use symbol `#` as operator that means
  the logical negation of `<=>`.
  The symbol `#` no longer signifies comments.
- return `list` of loaded roots of BDDs,
  when loading BDDs from Pickle files in:
  - `dd.autoref.BDD.load()`
  - `dd.bdd.BDD.load()`
- in `dd.cudd`, `dd.cudd_zdd`
  check available memory only in systems where
  both `SC_PAGE_SIZE` and `SC_PHYS_PAGES` are
  defined (read `sysconf(3)`).
- raise `ValueError` from:
  - `dd.autoref.BDD.level_of_var()`
  - `dd.bdd.BDD.level_of_var()`
  whenever unknown values are given as arguments
- rename:
  - method `dd.buddy.BDD.level()` to `dd.buddy.BDD.level_of_var()`
  - method `dd.buddy.BDD.at_level()` to `dd.buddy.BDD.var_at_level()`
  as the naming convention in other `dd` modules
- raise `ValueError` from:
  - `dd.buddy.BDD.level_of_var()`
  - `dd.buddy.BDD.var_at_level()`
  whenever unknown values are given as arguments,
  as done in other `dd` modules too
- several `assert` statements replaced by `raise`,
  with more specific exceptions, e.g.,
  `ValueError`, `TypeError`, `RuntimeError`
- strings returned by methods:
  - `dd.cudd.Function.__repr__()`
  - `dd.cudd_zdd.Function.__repr__()`
  changed to follow specification of `object.__repr__()`
  (delimited by `<` and `>`).
  Now also includes the object `id` as `hex` number.


## 0.5.7

- require `pytest >= 4.6.11`, instead of `nose`, for Python 3.10 compatibility
- support for dumping and loading BDDs to and from JSON files
  now requires Python 3
- test using GitHub Actions

API:

- return memory size in bytes from methods `dd.cudd.BDD.statistics` and
  `dd.cudd_zdd.ZDD.statistics`
  (the value of key `'mem'` in the returned `dict`)
- print used memory in bytes in the methods `dd.cudd.BDD.__str__` and
  `dd.cudd_zdd.ZDD.__str__`
- remove the now obsolete constants `dd.cudd.GB`, `dd.cudd_zdd.GB`
- remove the unused constant `dd.sylvan.GB`
- method `dd.cudd_zdd.ZDD.dump`:
  - support PNG and SVG formats, in addition to PDF
  - allow more than one references to ZDD nodes in the argument `roots`
- add method `apply` to the class `dd.mdd.MDD`
- several `assert` statements replaced by `raise` with
  exceptions more specific than `AssertionError`
- set `dd.cudd.Function.node` and `dd.cudd_zdd.Function.node`
  to `NULL` when the (local) reference count becomes zero


## 0.5.6

- distribute `manylinux2014_x86_64` wheel via PyPI

API:

- require `cython >= 0.29.15`
- add module `dd.cudd_zdd`
- allow empty support variable names in DDDMP files in function `dd.dddmp.load`
- methods `dump` and `load` of the classes
  `dd.cudd.BDD` and `dd.autoref.BDD`:
  - add JSON to file types
  - load by file extension
- change return type of method `dd.cudd.BDD.load`
  to `list` of `dd.cudd.Function`
- multiple roots supported in `dd.cudd.BDD.dump` for
  file types other than DDDMP
- method `count` of the classes
  `dd.cudd.BDD` and `dd.cudd_zdd.ZDD`:
  - make optional the argument `nvars`
- `dd.autoref.BDD.load`:
  require file extension `.p` for pickle files


## 0.5.5

API:

- require `networkx <= 2.2` on Python 2
- class `dd.bdd.BDD`:
  - remove argument `debug` from method `_next_free_int`
  - add method `undeclare_variables`
- plot nodes for external BDD references in function `dd.bdd.to_pydot`,
  which is used by the methods `BDD.dump` of the modules
  `dd.cudd`, `dd.autoref`, and `dd.bdd`
- function `dd._copy.load_json`:
  rename argument from `keep_order` to `load_order`
- add unused keyword arguments to method `autoref.BDD.decref`


## 0.5.4

- enable `KeyboardInterrupt` on POSIX systems for `cudd`
  when `cysignals >= 1.7.0` is present at installation

API:

- change signature of method `cudd.BDD.dump`
- add GraphViz as an option of `cudd.BDD.dump`
- allow copying between managers with different variable orders
- allow simultaneous substitution in `bdd.BDD.let`
- add property `BDD.var_levels`
- add method `BDD.reorder` to `cudd` and `autoref`
- add method `cudd.BDD.group` for grouping variables
- add `autoref.BDD` methods `incref` and `decref`
- change signatures of `cudd.BDD` methods `incref` and `decref`
- change default to `recursive=False` in method `cudd.BDD.decref`
- add property `Function.dag_size`
- add module `dd._copy`
- rm function `dd.bdd.copy_vars`, use method `BDD.declare` instead,
  and separately copy variable order, if needed.
  This function has moved to `_copy.copy_vars`.
- rm method `bdd.BDD.evaluate`, use method `dd.BDD.let`


## 0.5.3

- distribute `manylinux1_x86_64` wheel via PyPI

API:

- update to `networkx >= 2.0` (works with `< 2.0` too)
- class `BDD` in modules `autoref`, `bdd`, `cudd`, `sylvan`:
  - remove deprecated methods (where present):
    `compose`, `cofactor`, `rename`, `evaluate`,
    `sat_iter`, `sat_len`


## 0.5.2

API:

- require `networkx < 2.0.0`
- add module `dd._abc` that defines API implemented by other modules.
- add method `declare` to `BDD` classes
- add methods `implies` and `equiv` to class `cudd.Function`
- change BDD node reference syntax to "@ INTEGER"
- change `Function.__str__` to include `@` in modules `cudd` and `autoref`
- deprecate `BDD` methods `compose`, `cofactor`, `rename`, `evaluate`,
  instead use `BDD.let`
- class `BDD` in modules `autoref`, `bdd`, `cudd`, `sylvan`:
  - methods `pick`, `pick_iter`:
    rename argument from `care_bits` to `care_vars`
- class `BDD` in modules `autoref`, `bdd`:
  - method `count`:
    rename argument from `n` to `nvars`
- class `BDD` in modules `bdd`, `cudd`:
  - allow swapping variables in method `rename`,
    accept only variable names, not levels
- rm argument `bdd` from functions:
  - `image`, `preimage` in module `autoref`
  - `and_exists`, `or_forall`, `dump` in module `cudd`
  - `and_exists`, `or_forall` in module `sylvan`
- rm argument `roots` from method `autoref.BDD.collect_garbage`
- rm argument `source` from function:
  `copy_bdd` in modules `autoref`, `cudd`
- rm function `cudd.rename`, use method `cudd.BDD.let`
- rm function `autoref.rename`, use method `autoref.BDD.let`
- rm method `autoref.Function.__xor__`
- add TLA constants "TRUE" and "FALSE" to syntax,
  use these in method `BDD.to_expr`


## 0.5.1

API:

- classes `cudd.BDD`, `autoref.BDD`, `bdd.BDD`:
  - add method `let`, which will replace `compose`, `cofactor`, `rename`
  - add method `pick`
  - add method `pick_iter`, deprecate `sat_iter`
  - add method `count`, deprecate `sat_len`
  - allow copying node to same manager, but log warning
- class `sylvan.BDD`:
  - add method `let`
- classes `cudd.Function`, `autoref.Function`:
  - implement all comparison methods (`__le__`, `__lt__`)


## 0.5.0

API:

- dynamic variable reordering in `dd.bdd.BDD` (by default disabled)
- method `bdd.BDD.sat_len`: count only levels in support (similar to CUDD)
- class `autoref.Function`:
  - rename attribute `bdd` to `manager`
- classes `cudd.Function`, `autoref.Function`, `sylvan.Function`:
  - add attributes `var, support, bdd`
  - add method `__hash__`
- classes `cudd.Function` and `sylvan.Function`:
  - hide attribute `index` as `_index`
- classes `cudd.BDD` and `sylvan.BDD`:
  - do not memoize attributes `false` and `true`
- classes `cudd.BDD` and `autoref.BDD`:
  - add method `find_or_add`
- method `BDD.sat_iter`:
  - rm arg `full`
  - `care_bits = support` as default
  - `care_bits < support` allowed
- function `bdd.to_pydot`: plot only levels in support of given node
- add function `autoref.reorder`


## 0.4.3

API:

- build `dd.cudd` using CUDD v3.0.0
  (an older CUDD via an older `download.py` should work too)


## 0.4.2

API:

- classes `bdd.BDD`, `autoref.BDD`:
  - rm attribute `ordering`, use `vars`
  - rename `__init__` argument `ordering` to `levels`
- allow passing path to CUDD during installation via `--cudd`


## 0.4.1

- add Cython interface `dd.sylvan` to Sylvan
- support TLA+ syntax

BUG:

- in Python 2 use `sys.maxint` for `bdd.BDD.max_nodes`

API:

- classes `bdd.BDD` and `cudd.BDD`:
  - method `apply`: rm `"bimplies"` value
  - raise `AssertionError` if `care_bits < support` in method `sat_iter`
- rm unused operator `!=` from parser grammar
- class `autoref.Function`:
  - rename method `bimplies` to `equiv`


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
  - read node count without removing unused nodes
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
