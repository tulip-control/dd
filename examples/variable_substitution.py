"""Renaming variables."""
from dd import autoref as _bdd
# from dd import cudd as _bdd  # uncomment to use CUDD


# instantiate a shared BDD manager
bdd = _bdd.BDD()
bdd.declare("x", "y", "u", "v")
# create the BDD for the disjunction of x and y
u = bdd.add_expr("x \/ y")
# Substitution of x' for x and y' for y.
# In TLA+ we can write this as:
#
# LET
#     x == u
#     y == v
# IN
#     x \/ y
rename = dict(x="u", y="v")
v = bdd.let(rename, u)
# show the result
s = bdd.to_expr(v)
print(s)

# another way to confirm that the result is as expected
v_ = bdd.add_expr("u \/ v")
assert v == v_
