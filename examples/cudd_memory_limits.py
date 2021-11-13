"""How to place an upper bound on the memory CUDD consumes."""
import dd.cudd as _bdd


def configure():
    GiB = 2**30
    b = _bdd.BDD()
    b.configure(
        # number of bytes
        max_memory=2 * GiB,
        # number of entries, not memory units!
        max_cache_hard=2**25)


if __name__ == '__main__':
    configure()
