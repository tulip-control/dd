"""How BDDs are implemented.

This module describes the main characteristics of
the data structure used in the module `dd.bdd`.
The module `dd.autoref` is an interface to the
implementation that is in the module `dd.bdd`.
"""


def bdd_implementation_example():
    """Main details of `dd.bdd.BDD`.

    The module `dd.bdd.BDD` contains
    the Python implementation of
    binary decision diagrams.
    """
    # the graph that represents
    # the BDDs stored in memory
    successors = {
        1: (2, None, None),
            # The node `1` represents the value `TRUE`.
            # The node `-1` represents the value `FALSE`.
            # Node `1` is used also as node `-1`.
            #
            # The number of "-" symbols on the edges
            # along the path that reaches the node `1`
            # determines whether `1` will be regarded
            # as `-1` when reached.
        2: (1, -1, 1),
            # node_id:
            # (level,
            #  successor_if_false,
            #  successor_if_true)
        3: (0, -1, 2)}
            # Keys are positive integers.
            # Doing so reduces how much
            # memory needs to be used.
    var_to_level = dict(
        x=0,
        y=1)
    values_to_substitute = dict(
        x=False,
        y=True)
    bdd_reference = 3
        # BDD that means `x /\ y`,
        # the conjunction of `x` and `y`.
    # invert dictionary
    level_to_var = {
        level: varname
        for varname, level in
            var_to_level.items()}
    # Exercise: change the implementation
    # of the function `let()`, so that
    # `values_to_substitute` can be
    # an assignment to only some of
    # the variables that occur in the
    # BDD given to `let()`.
    result = let(
        values_to_substitute,
        bdd_reference,
        successors,
        level_to_var)
    print(f'{result = }')


def let(
        values:
            dict[str, bool],
        bdd_ref:
            int,
        successors:
            dict[
                int,
                tuple[
                    int,
                    int | None,
                    int | None]],
        level_to_var:
            dict[
                int, str]
        ) -> int:
    """Recursively substitute values for variables.

    Return a binary decision diagram that
    represents the result of this substitution.

    @param values:
        assignment of Boolean values to
        variable names
    @param bdd_ref:
        a node, key in successors
    @param successors:
        graph that stores nodes
    @return:
        BDD node,
        which is a key in `successors`
    """
    # leaf ?
    if abs(bdd_ref) == 1:
        return bdd_ref
    # nonleaf node
    key = abs(bdd_ref)
    level, low, high = successors[key]
    variable_name = level_to_var[level]
    variable_value = values[variable_name]
    if variable_value:
        successor = high
    else:
        successor = low
    result = let(
        values, successor, successors,
        level_to_var)
    # copy sign
    if bdd_ref < 0:
        result = - result
    return result


if __name__ == '__main__':
    bdd_implementation_example()
