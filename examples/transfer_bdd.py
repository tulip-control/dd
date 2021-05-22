"""How to copy a BDD from one manager to another."""
from dd import autoref


def transfer():
    """Copy a BDD from one manager to another."""
    # create two BDD managers
    source = autoref.BDD()
    target = autoref.BDD()
    # declare the variables in both BDD managers
    vrs = ['a', 'b']
    source.declare(*vrs)
    target.declare(*vrs)
    # create a BDD with root `u`
    u = source.add_expr('a /\ b')
    # copy the BDD `u` to the BDD manager `target`
    u_ = source.copy(u, target)


def copy_variable_order():
    """As in `transfer`, and copy variable order too."""
    source = autoref.BDD()
    target = autoref.BDD()
    # declare variables in the source BDD manager
    source.declare('a', 'b')
    # create a BDD with root `u`
    u = source.add_expr('a /\ b')
    # copy the variables, and the variable order
    target.declare(*source.vars)
    target.reorder(source.var_levels)
    # copy the BDD `u` to the BDD manager `target`
    u_ = source.copy(u, target)


if __name__ == '__main__':
    transfer()
    copy_variable_order()
