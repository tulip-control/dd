"""Traversing binary decision diagrams.

Read [1, Section 2.2].


Reference
=========

[1] Steven M. LaValle
    Planning Algorithms
    Cambridge University Press, 2006
    <http://lavalle.pl/planning/>
"""
import collections as _cl
import textwrap as _tw

import dd.autoref as _bdd


def traverse_breadth_first(u):
    """Return nodes encountered."""
    queue = _cl.deque([u])
    visited = set()
    while queue:
        g = queue.popleft()
        visited.add(int(g))
        # is `g` a leaf ?
        if g.var is None:
            continue
        queue.extend([g.low, g.high])
    return visited


def traverse_depth_first(u):
    """Return nodes encountered."""
    stack = [u]
    visited = set()
    while stack:
        g = stack.pop()
        visited.add(int(g))
        # is `g` a leaf ?
        if g.var is None:
            continue
        stack.extend([g.low, g.high])
    return visited


def run_traversals():
    bdd = _bdd.BDD()
    bdd.declare('x', 'y', 'z')
    u = bdd.add_expr(
        r' (x \/ ~ y) /\ z ')
    print('breadth-first traversal')
    visited_b = traverse_breadth_first(u)
    print(visited_b)
    print('depth-first traversal')
    visited_d = traverse_depth_first(u)
    print(visited_d)
    if visited_b == visited_d:
        return
    raise AssertionError(_tw.dedent(f'''
        Expected same set of nodes from
        traversals, but:
        {visited_b = }
        and:
        {visited_d = }
        '''))


if __name__ == '__main__':
    run_traversals()
