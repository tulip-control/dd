"""How to write BDDs to JSON files, and load them."""
import dd.cudd as _bdd


def json_example():
    """Entry point."""
    filename = 'storage.json'
    dump_bdd_as_json(filename)
    load_bdd_from_json(filename)


def dump_bdd_as_json(filename):
    """Write a BDD to a JSON file."""
    bdd = _bdd.BDD()
    bdd.declare('x', 'y', 'z')
    u = bdd.add_expr(r'(x /\ y) \/ ~ z')
    bdd.dump(filename, [u])
    print(f'Dumped BDD: {u}')


def load_bdd_from_json(filename):
    """Load a BDD from a JSON file."""
    bdd = _bdd.BDD()
    u, = bdd.load(filename)
    print(f'Loaded BDD: {u}')


if __name__ == '__main__':
    json_example()
