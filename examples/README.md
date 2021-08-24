The examples are:

- `variable_substitution.py`: rename variables that a BDD depends on

- `reachability.py`: compute the states reachable from some
  starting set of states.

- `queens.py`: solve the [N-queens problem](
    https://en.wikipedia.org/wiki/Eight_queens_puzzle).

- `reordering.py`: activate dynamic variable reordering for the Python
  implementation, invoke reordering explicitly, and permute variables to
  a desired order.

- `cudd_configure_reordering.py`: how to turn reordering off when using CUDD

- `cudd_statistics.py`: see CUDD's activity in numbers.

- `cudd_memory_limits.py`: bound how much memory CUDD is
  allowed to use.

- `cudd_zdd.py`: how to use ZDDs with CUDD.


The shell scripts show how to install the Cython modules of `dd`:

- `install_dd_cudd.sh`: how to install the modules:
  - `dd.cudd` and
  - `dd.cudd_zdd`
- `install_dd_sylvan.sh`: how to install the module `dd.sylvan`
- `install_dd_buddy.sh`: how to install the module `dd.buddy`

To install all the above modules, combine the steps contained in
the above shell scripts, and pass to `setup.py`
all the relevant command-line options, i.e.,

```shell
pip install -r <(echo "dd \
    --install-option='--buddy' \
    --install-option='--fetch' \
    --install-option='--cudd' \
    --install-option='--cudd_zdd' \
    --install-option='--sylvan'")
```
