"""Is a given Boolean formula satisfiable?"""
import dd


def example():
    """Demonstrate usage."""
    # a formula
    names = ['x', 'y']
    formula = r'x /\ ~ y'
    sat = is_satisfiable(formula, names)
    _print_result(formula, sat)
    # another formula
    names = ['x']
    formula = r'x /\ ~ x'
    sat = is_satisfiable(formula, names)
    _print_result(formula, sat)


def is_satisfiable(formula, names):
    """Return `True` if `formula` is satisfiable.

    A formula is satisfiable by Boolean values,
    if there exist Boolean values such that,
    when those values are substituted for the
    variables that appear in the formula,
    the result is equivalent to `TRUE`.
    """
    bdd = dd.BDD()
    bdd.declare(*names)
    u = bdd.add_expr(formula)
    return u != bdd.false


def _print_result(formula, sat):
    """Inform at stdout."""
    if sat:
        neg = ''
    else:
        neg = 'not '
    print(
        f'The formula `{formula}` '
        f'is {neg}satisfiable.')


if __name__ == '__main__':
    example()
