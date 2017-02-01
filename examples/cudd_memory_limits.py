#!usr/bin/env python
"""How place an upper bound on the memory CUDD consumes."""
from dd import cudd


def main():
    assert cudd.GB == 2**30, cudd.GB
    b = cudd.BDD()
    b.configure(
        # number of bytes
        max_memory=2 * cudd.GB,
        # number of entries, not memory units!
        max_cache_hard=2**25)


if __name__ == '__main__':
    main()
