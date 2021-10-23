The examples are:

- `variable_substitution.py`: rename variables that a BDD depends on

- `boolean_satisfiability.py`: solving the
  [propositional satisfiability problem](
    https://en.wikipedia.org/wiki/Boolean_satisfiability_problem)

- `reachability.py`: compute the states reachable from some
  starting set of states.

- `queens.py`: solve the [N-queens problem](
    https://en.wikipedia.org/wiki/Eight_queens_puzzle).

- `bdd_traversal.py`: breadth-first and depth-first iteration over nodes

- `reordering.py`: activate dynamic variable reordering for the Python
  implementation, invoke reordering explicitly, and permute variables to
  a desired order.

- `cudd_configure_reordering.py`: how to turn reordering off when using CUDD

- `cudd_statistics.py`: read CUDD's activity in numbers.

- `cudd_memory_limits.py`: bound how much memory CUDD is
  allowed to use.

- `cudd_zdd.py`: how to use ZDDs with CUDD.

- `json_example.py`: how to write BDDs to JSON files,
  and how to load BDDs from JSON files.


The shell scripts show how to install the Cython modules of `dd`:

- `install_dd_cudd.sh`: how to install the modules:
  - `dd.cudd` and
  - `dd.cudd_zdd`
- `install_dd_sylvan.sh`: how to install the module `dd.sylvan`
- `install_dd_buddy.sh`: how to install the module `dd.buddy`

To install all the above modules, combine the steps contained in
the above shell scripts, and define all the relevant
environment variables, i.e.,

```shell
export \
    DD_BUDDY=1 \
    DD_FETCH=1 \
    DD_CUDD=1 \
    DD_CUDD_ZDD=1 \
    DD_SYLVAN=1
pip install dd
```
