"""How to print readable statistics."""
import pprint

import dd.cudd


def print_statistics():
    b = dd.cudd.BDD()
    b.declare('x', 'y', 'z')
    u = b.add_expr(r'x /\ y /\ z')
    u = b.add_expr(r'x \/ y \/ ~ z')
    stats = b.statistics()
    pprint.pprint(format_dict(stats))


def format_dict(d):
    """Return `dict` with values readable by humans."""
    return {k: format_number(v) for k, v in d.items()}


def format_number(x):
    """Return readable string for `x`."""
    if 0 < x < 1:
        return f'{x:1.2}'
    return f'{x:_}'


if __name__ == '__main__':
    print_statistics()
