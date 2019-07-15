import sys
import time

import json
import logging
import numpy as np
import graph_tool as gt

# from pymongo import MongoClient
from scipy import spatial
from multiprocessing import Pool
import logging.handlers as handlers


def density(G):
    n = G.num_vertices()
    m = G.num_edges()
    if m == 0 or n <= 1:
      return 0.0
    return 2 * m / (n * (n - 1))

def get_metrics(G, t):
    return dict(
        time=t,
        nodes=list(G.vp.label),
        n_vehicle=G.num_vertices(),
        degree=list(np.array(G.degree_property_map('total').get_array()) / (G.num_vertices() - 1)),
        density=density(G)
    )

def store_metrics(data):#, db, collection):
    time = data["time"]
    with open("jsons/%s.json"%time, "w") as f:
        json.dump(data, f)

    # db[collection].insert_many(data)
    # print("There were written %s graphs information in %s collection."%(len(data), collection))

def connecting_nodes(labels, pos):
    G = gt.Graph(directed=False)
    n_nodes = len(labels)
    G.add_vertex(n_nodes)
    G.vp.label = G.new_vp("string", vals=labels)
    G.ep.weight = G.new_ep("float")
    transmission_range = 200.0

    for i in range(n_nodes - 1):
        dist = spatial.distance.cdist([pos[i]], pos[i+1:]).ravel()
        edges_dist = np.array(list(
          zip([i] * dist.shape[0], range(i+1, n_nodes), dist)
        ), dtype='u4, u4, f4')
        mask = np.ma.masked_less_equal(dist, transmission_range).mask
        if np.any(mask):
          G.add_edge_list(list(edges_dist[mask]), eprops=[G.ep.weight])
    return G

def process_lines(graph_lines):
    n_lines = len(graph_lines)
    pos = np.zeros(((n_lines - 1), 2), dtype=np.float32)
    labels = np.full((n_lines - 1), fill_value='0', dtype='U8')
    for i in range(n_lines - 1):
        id_, x, y = graph_lines[i].split(":")
        labels[i] = id_
        pos[i][0] = float(x)
        pos[i][1] = float(y)
    time = graph_lines[-1].split(" ")[1]
    labels = np.flip(labels)
    pos = np.flip(pos, 0)
    labels, idx = np.unique(labels, return_index=True)
    pos = pos[idx, :]
    G = connecting_nodes(labels, pos)
    return get_metrics(G, time)

def read_file_graph():
    with open("../graphs.txt", "r") as file_:
        graph_lines = []
        for line in file_:
            if "END" not in line:
                graph_lines.append(line)
            else:
                graph_lines.append(line)
                tmp_lines = graph_lines.copy()
                graph_lines = []
                yield tmp_lines

def measure_graphs():
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_logger = logging.getLogger('Logger')
    file_logger.setLevel(logging.DEBUG)
    file_handler = handlers.RotatingFileHandler(
        'logger.log', maxBytes=200 * 1024 * 1024, backupCount=1
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    file_logger.addHandler(file_handler)
    # client = MongoClient('localhost', 27017)
    # db = client.vanet

    graph_lines_generator = read_file_graph()
    with Pool(4) as p:
        start = time.time()
        for json_measuments in p.imap_unordered(process_lines, graph_lines_generator):
            store_metrics(json_measuments)
            file_logger.info("Duration >> %s -- Graph size >> %s"%(time.time() - start, json_measuments["n_vehicle"]))

if __name__ == "__main__":
    measure_graphs()



# def measure_graphs():
#     client = MongoClient('localhost', 27017)
#     db = client.vanet

#     with open("../graphs.txt", "r") as f:
#         graphs = []
#         G = nx.Graph()
#         for line in f:
#             if "END" not in line:
#                 id_, x, y = line.split(":")
#                 G.add_node(int(id_), pos=(float(x), float(y)))
#             else:
#                 connecting_nodes(G)
#                 graphs.append((line.split(" ")[1], G.copy()))
#                 G.clear()
#                 print(len(graphs))
#                 if len(graphs) % 100 == 0:
#                     store_metrics(graphs, db, 'cologne')
#                     graphs = []
#         if len(graphs) > 0:
#             connecting_nodes(graphs)
#             store_metrics(graphs, db, 'cologne')

# def connecting_nodes(G, pos):
#     transmission_range = 200.0  # condition in meters to create an edge between u and v

#     nodes = G.nodes()
#     distances = spatial.distance.squareform(spatial.distance.pdist(pos), checks=False).ravel()
#     weighted_edges = np.concatenate([ [i_.ravel()], [j_.ravel()], [distances] ]).T
#     mask = np.ma.masked_greater_equal(distances, transmission_range).mask
#     G.add_weighted_edges_from(weighted_edges[mask, :])

# def store_metrics(graphs, db, collection):
#     data = []
#     for time, G in graphs:
#         data.append(dict(
#             time=time,
#             n_vehicle=len(G.nodes),
#             degree=nx.degree_centrality(G),
#             betweeness=nx.betweenness_centrality(G),
#             closeness=nx.closeness_centrality(G),
#             # pagerank=nx.pagerank(G),
#             # harmonic_centrality=nx.harmonic_centrality(G),
#             # clustering_cf=nx.clustering(G),
#             # local_efficiency=nx.local_efficiency(G),
#             # global_efficiency=nx.global_efficiency(G),
#             density=nx.density(G)
#             # maximal_matching=nx.maximal_matching(G)
#         ))

#     db[collection].insert_many(data)
#     print("There were written %s graphs information in %s collection."%(len(data), collection))
