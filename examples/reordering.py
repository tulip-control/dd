"""Activate dynamic reordering for the Python implementation `dd.autoref`."""
import logging

from dd import autoref as _bdd


def demo_dynamic_reordering():
    """Activate dynamic reordering and add nodes until triggered."""
    print(
        '\n' + (50 * '-') +
        '\ndemo of dynamic reordering\n' +
        (50 * '-'))
    show_logging()
    bdd = create_manager()
    # activate reordering
    # (for the Python implementation `dd.autoref` reordering
    # is disabled by default, whereas for `dd.cudd` reordering
    # is enabled by default)
    bdd.configure(reordering=True)
    print_manager_size(bdd)  # nearly empty BDD manager
    print_var_levels(bdd)
    # add enough nodes to trigger reordering
    nodes = trigger_reordering(bdd)
    print_manager_size(bdd)
    print_var_levels(bdd)  # variables have been reordered


def show_logging():
    """Display logging messages relevant to reordering.

    To see more details, increase the verbosity level
    to `logging.DEBUG`.
    """
    logger = logging.getLogger('dd.bdd')
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())


def create_manager():
    """Return a BDD manager with plenty of variables declared."""
    bdd = _bdd.BDD()
    vrs = ['x{i}'.format(i=i) for i in range(100)]
    bdd.declare(*vrs)
    return bdd


def trigger_reordering(bdd):
    """Add several nodes to the manager.

    Dynamic reordering is triggered when the total number
    of nodes that are in the manager reaches a certain threshold.
    We add nodes in order to reach that that threshold,
    and thus trigger reordering.

    To witness the reordering happen,
    look at the logging messages.
    """
    nodes = list()
    for i in range(25):
        expr = (
            '(x{i1} /\ x{i2}) \/ (x{i3} /\ x{i4})'
            ' \/ (x{i5} /\ x{i6})').format(
                i1=i, i2=i + 6, i3=i + 7,
                i4=i + 8, i5=i + 9, i6=i + 10)
        u = bdd.add_expr(expr)
        nodes.append(u)
    return nodes


def print_var_levels(bdd):
    """Print level of each variable."""
    n = len(bdd.vars)
    levels = [
        bdd.var_at_level(level)
        for level in range(n)]
    print((
        'Variable order (starting at level 0):\n'
        '{levels}').format(
            levels=levels))


def demo_static_reordering():
    """How to invoke reordering explicitly."""
    print(
        '\n' + (50 * '-') +
        '\ndemo of static reordering\n' +
        (50 * '-'))
    bdd = _bdd.BDD()
    bdd.declare('z1', 'z2', 'z3', 'y1', 'y2', 'y3')
    expr = '(z1 /\ y1) \/ (z2 /\ y2) \/ (z3 /\ y3)'
    u = bdd.add_expr(expr)
    print_manager_size(bdd)
    # invoke sifting
    _bdd.reorder(bdd)
    print_manager_size(bdd)


def demo_specific_var_order():
    """How to permute the variables to a desired order."""
    print(
        '\n' + (50 * '-') +
        '\ndemo of user-defined variable permutation\n' +
        (50 * '-'))
    bdd = _bdd.BDD()
    bdd.declare('a', 'b', 'c')
    u = bdd.add_expr('(a \/ b) /\ ~ c')
    print_var_levels(bdd)
    # reorder
    desired_order = dict(a=2, b=0, c=1)
    _bdd.reorder(bdd, desired_order)
    # confirm
    print_var_levels(bdd)


def print_manager_size(bdd):
    """
    Print the size of bdd of bdd.

    Args:
        bdd: (str): write your description
    """
    msg = 'Nodes in manager: {n}'.format(n=len(bdd))
    print(msg)


if __name__ == '__main__':
    demo_dynamic_reordering()
    demo_static_reordering()
    demo_specific_var_order()
