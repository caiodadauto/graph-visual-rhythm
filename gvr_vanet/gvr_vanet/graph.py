import os
import time
import json
import logging
import logging.handlers as handlers
from multiprocessing import Pool, cpu_count

import numpy as np
import graph_tool as gt
from scipy import spatial


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

def store_metrics(data, db=None, collection=None):
    if not db or not collection:
        time = data["time"]
        graph_dir = "graph_doc/"
        if not os.path.isdir(graph_dir):
            os.makedirs(graph_dir)
        with open(graph_dir + "%s.json"%time, "w") as f:
            json.dump(data, f)
    else:
        db[collection].insert_many(data)

def connecting_nodes(labels, pos):
    G = gt.Graph(directed=False)
    n_nodes = len(labels)
    G.add_vertex(n_nodes)
    G.vp.label = G.new_vp("string", vals=labels)
    G.ep.weight = G.new_ep("float")
    transmission_range = 200.0

    for i in range(n_nodes - 1):
        dist = spatial.distance.cdist([pos[i]], pos[(i + 1):]).ravel()
        edges_dist = np.array(list(
          zip([i] * dist.shape[0], range(i + 1, n_nodes), dist)
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

def read_file_graph(rawgraph):
    with open(rawgraph, "r") as file_:
        graph_lines = []
        for line in file_:
            if "END" not in line:
                graph_lines.append(line)
            else:
                graph_lines.append(line)
                tmp_lines = graph_lines.copy()
                graph_lines = []
                yield tmp_lines

def measure_graphs(rawgraph='raw_graph.dat', n_proc=None, db=None, collection=None):
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_logger = logging.getLogger('Logger')
    file_logger.setLevel(logging.DEBUG)
    file_handler = handlers.RotatingFileHandler(
        'graph_measure.log', maxBytes=200 * 1024 * 1024, backupCount=1
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    file_logger.addHandler(file_handler)

    n_proc = cpu_count() if not n_proc else n_proc
    graph_lines_generator = read_file_graph(rawgraph)
    with Pool(n_proc) as p:
        start = time.time()
        for json_measuments in p.imap_unordered(process_lines, graph_lines_generator):
            store_metrics(json_measuments, db, collection)
            file_logger.info("Duration >> %s -- Graph size >> %s"%(time.time() - start, json_measuments["n_vehicle"]))