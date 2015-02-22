import time
from dd import dddmp
import networkx as nx


s = '''
.ver DDDMP-2.0
.mode A
.varinfo 0
.nnodes 78
.nvars 18
.nsuppvars 15
.suppvarnames    y@0.0.10 y@0.0.10' y@1 y@1' y@2 y@2' y@3 y@3' pc0@0.0.3 pc0@0.0.3' pc0@1 pc0@1' key@0.0.3' key@1' _jx_b0
.orderedvarnames y@0.0.10 y@0.0.10' y@1 y@1' y@2 y@2' y@3 y@3' pc0@0.0.3 pc0@0.0.3' pc0@1 pc0@1' key@0.0.3 key@0.0.3' key@1 key@1' _jx_b0 strat_type
.ids 0 1 2 3 4 5 6 7 8 9 10 11 13 15 16
.permids 0 1 2 3 4 5 6 7 8 9 10 11 13 15 16
.auxids 0 1 2 3 4 5 6 7 8 9 10 11 13 15 16
.nroots 1
.nodes
1 T 1 0 0
2 16 14 1 -1
3 15 13 1 2
4 13 12 1 3
5 11 11 1 4
6 10 10 5 1
7 9 9 6 1
8 10 10 1 5
9 9 9 8 1
10 8 8 7 9
11 7 7 1 10
12 6 6 1 11
13 5 5 1 12
14 3 3 1 13
15 11 11 4 1
16 10 10 1 15
17 9 9 1 16
18 8 8 17 1
19 7 7 1 18
20 6 6 1 19
21 4 4 1 20
22 9 9 6 16
23 8 8 22 9
24 7 7 18 23
25 6 6 11 24
26 5 5 20 25
27 4 4 13 26
28 3 3 21 27
29 2 2 14 28
30 9 9 5 1
31 8 8 1 30
32 7 7 1 31
33 6 6 1 32
34 5 5 1 33
35 3 3 1 34
36 6 6 1 18
37 5 5 20 36
38 4 4 1 37
39 8 8 17 30
40 7 7 18 39
41 6 6 32 40
42 5 5 20 41
43 4 4 34 42
44 3 3 38 43
45 2 2 35 44
46 1 1 29 45
47 5 5 1 11
48 4 4 13 47
49 3 3 1 48
50 9 9 16 1
51 8 8 50 1
52 7 7 1 51
53 6 6 1 52
54 4 4 1 53
55 10 10 5 15
56 9 9 55 1
57 8 8 56 9
58 7 7 51 57
59 6 6 11 58
60 5 5 53 59
61 4 4 13 60
62 3 3 54 61
63 2 2 49 62
64 5 5 1 32
65 4 4 34 64
66 3 3 1 65
67 6 6 1 51
68 5 5 53 67
69 4 4 1 68
70 8 8 50 30
71 7 7 51 70
72 6 6 32 71
73 5 5 53 72
74 4 4 34 73
75 3 3 69 74
76 2 2 66 75
77 1 1 63 76
78 0 0 46 77
.end
'''
parser = dddmp.Parser()


def test_parser():
    g = parser.parse(s)
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


if __name__ == '__main__':
    load_bdd_2_masters()
