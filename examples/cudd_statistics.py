"""How to print readable statistics."""
import pprint

from dd import cudd
import humanize


def main():
    """
    Main function.

    Args:
    """
    b = cudd.BDD()
    b.declare('x', 'y', 'z')
    u = b.add_expr('x & y & z')
    u = b.add_expr('x | y | ~ z')
    stats = b.statistics()
    pprint.pprint(format_dict(stats))


def format_dict(d):
    """Return `dict` with values readable by humans."""
    return {k: format_number(v) for k, v in d.items()}


def format_number(x):
    """Return readable string for `x`."""
    if 0 < x and x < 1:
        return '{x:1.2}'.format(x=x)
    return humanize.intword(x)


if __name__ == '__main__':
    main()
