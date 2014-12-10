About
=====

A pure-Python package for manipulating decision diagrams, for now [binary decision diagrams](https://en.wikipedia.org/wiki/Binary_decision_diagram) (BDDs).
An ordered BDD is represented as a [`networkx`](https://networkx.github.io/) digraph.
BDDs dumped by [CUDD](http://vlsi.colorado.edu/~fabio/CUDD/) can be loaded using a [PLY](https://github.com/dabeaz/ply/)-based parser.


Installation
============

Uses `setuptools`:

```
python setup.py install
```


License
=======
[BSD-3](http://opensource.org/licenses/BSD-3-Clause), see `LICENSE` file.