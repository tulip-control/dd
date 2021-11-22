"""Loading BDD from JSON using the `json` module.

This example shows how to load from JSON,
and convert to a `networkx` graph.

BDDs can be loaded from JSON into BDD contexts
using the methods:
- `dd.autoref.BDD.load()`
- `dd.cudd.BDD.load()`
"""
import json
import textwrap as _tw

import dd.autoref as _bdd
import networkx as _nx


def dump_load_example(
        ) -> None:
    """Loading to `networkx` graph, using `json`."""
    filename = 'example_bdd.json'
    create_and_dump_bdd(filename)
    graph = load_and_map_to_nx(filename)
    # print `graph`
    print('The loaded graph is:')
    for u, v in graph.edges():
        print(f'edge: {u} -> {v}')
    roots = graph.roots
    level_of_var = graph.level_of_var
    print(_tw.dedent(f'''
        with graph roots: {roots}
        and variable levels: {level_of_var}
        '''))


def create_and_dump_bdd(
        filename:
            str
        ) -> None:
    """Write BDD to JSON file."""
    bdd = _bdd.BDD()
    bdd.declare('x', 'y', 'z')
    u = bdd.add_expr(r'x /\ (~ y \/ z)')
    roots = dict(u=u)
    bdd.dump(
        filename,
        roots=roots)


def load_and_map_to_nx(
        filename:
            str
        ) -> _nx.DiGraph:
    """Return graph loaded from JSON."""
    with open(filename, 'r') as fd:
        data = fd.read()
    data = json.loads(data)
    # map to nx
    graph = _nx.DiGraph()
    for k, v in data.items():
        print(k, v)
        if k in ('roots', 'level_of_var'):
            continue
        node = int(k)
        level, node_low, node_high = v
        graph.add_edge(node, node_low)
        graph.add_edge(node, node_high)
    graph.roots = data['roots']
    graph.level_of_var = data['level_of_var']
    return graph


if __name__ == '__main__':
    dump_load_example()
