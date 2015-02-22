import time
from dd import dddmp
import humanize
import networkx as nx
from pympler import asizeof


parser = dddmp.Parser()


def test_parser():
    fname = 'sample_dddmp.txt'
    g = parser.parse(fname)
    h = nx.DiGraph()
    for u, d in g.nodes_iter(data=True):
        h.add_node(u, label=d['var_name'])
    for u, v, d in g.edges_iter(data=True):
        h.add_edge(u, v, label=int(d['c']))
    pd = nx.to_pydot(h)
    pd.write_pdf('bdd.pdf')


def load_bdd_2_masters():
    fname = 'bdd_16_masters.txt'
    t0 = time.time()
    g = parser.parse(fname)
    t1 = time.time()
    print('finished: {t}'.format(t=t1 - t0))
    print(len(g))
    print(humanize.naturalsize(asizeof.asizeof(g)))


if __name__ == '__main__':
    load_bdd_2_masters()
