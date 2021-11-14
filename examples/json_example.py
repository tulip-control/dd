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
    roots = dict(u=u)
    bdd.dump(filename, roots)
    print(f'Dumped BDD: {u}')


def load_bdd_from_json(filename):
    """Load a BDD from a JSON file."""
    bdd = _bdd.BDD()
    roots = bdd.load(filename)
    print(f'Loaded BDD: {roots}')


if __name__ == '__main__':
    json_example()
