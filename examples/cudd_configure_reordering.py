"""How to configure reordering in CUDD via `dd.cudd`."""
import pprint

import dd.cudd as _bdd


bdd = _bdd.BDD()
vrs = ['x', 'y', 'z']
bdd.declare(*vrs)
# get the variable order
levels = {var: bdd.level_of_var(var) for var in vrs}
print(levels)
# change the levels
desired_levels = dict(x=2, y=0, z=1)
_bdd.reorder(bdd, desired_levels)
# confirm that variables are now where desired
new_levels = {var: bdd.level_of_var(var) for var in vrs}
print(new_levels)
# dynamic reordering is initially turned on
config = bdd.configure()
pprint.pprint(config)
# turn off dynamic reordering
bdd.configure(reordering=False)
# confirm dynamic reordering is now off
config = bdd.configure()
pprint.pprint(config)
