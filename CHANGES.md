# dd changelog


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