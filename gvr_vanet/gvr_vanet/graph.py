import os
import sys
import time
import json
import logging
import logging.handlers as handlers
from joblib import Parallel, delayed

import numpy as np
from scipy import spatial
# try:
#     import graph_tool as gt
# except ImportError:
import networkx as nx

GRAPH_ROOT = "graph_doc/"
LAST_TIME_READ = -1

def density(G):
    n = G.num_vertices()
    m = G.num_edges()
    if m == 0 or n <= 1:
      return 0.0
    return 2 * m / (n * (n - 1))

def get_metrics(G, t):
    if "graph_tool" in sys.modules:
        return dict(
            time=t,
            nodes=list(G.vp.label),
            n_vehicle=G.num_vertices(),
            degree=list(np.array(G.degree_property_map('total').get_array()) / (G.num_vertices() - 1)),
            density=density(G)
        )
    else:
        return dict(
            time=t,
            labels=list(dict(G.nodes(data='label')).values()),
            n_vehicle=G.number_of_nodes(),
            degree=nx.degree_centrality(G),
            density=nx.density(G)
        )

def store_graph(G, dir_name, pos, labels):
    path = os.path.join(GRAPH_ROOT, dir_name)
    if not os.path.isdir(path):
        os.makedirs(path)
    nx.write_sparse6(G, os.path.join(path, "graph.sparse6"))
    np.savez_compressed(os.path.join(path, "node_pos.npz"), pos)
    np.savez_compressed(os.path.join(path, "node_labels.npz"), labels)
    weights = list(G.edges(data='weight'))
    if weights:
      np.savez_compressed(os.path.join(path, "edge_weights.npz"), np.array(weights)[:,-1])


def store_metrics(data, use_dir=False, db=None, collection=None):
    if not db or not collection:
        if use_dir:
            file_path = os.path.join(str(data["time"]), "metrics.json")
        else:
            file_path = str(data["time"]) + ".json"
        path = os.path.join(GRAPH_ROOT, file_path)
        with open(path, "w") as f:
            json.dump(data, f)
    else:
        db[collection].insert_many(data)

def cdist_mask(pos, th, n, sl):
    dist = spatial.distance.cdist([pos[n]], pos[sl]).ravel()
    mask = dist <= th
    receivers = np.arange(sl.start, sl.stop)
    senders = np.full_like(receivers, n)
    dist = np.array(list(zip(senders, receivers, dist)), dtype='u4,u4,f4')
    return dist[mask]

def connecting_nodes(labels, pos, n_proc, dir_name=None):
    n_nodes = len(labels)
    transmission_range = 200.0

    if "graph_tool" in sys.modules:
        G = gt.Graph(directed=False)
        G.add_vertex(n_nodes)
        G.vp.label = G.new_vp("string", vals=labels)
        G.ep.weight = G.new_ep("float")
    else:
        G = nx.Graph()
        G.add_nodes_from([(idx, dict(label=l)) for idx, l in zip(range(n_nodes), labels)])

    with Parallel(n_jobs=n_proc) as parallel:
        for i in range(n_nodes - 1):
            size = n_nodes - (i + 1)
            if size > n_proc * 10:
                step = size // n_proc
                slices = [slice(start, start + step) for start in range(i + 1, (i + 1) + (size - 2 * step), step)]
                slices.append(slice((i + 1) + (n_proc - 1) * step, n_nodes))
            else:
                slices = [slice(i + 1, n_nodes)]
            results = Parallel(n_jobs=n_proc)(delayed(cdist_mask)(pos, transmission_range, i, sl) for sl in slices)
            G.add_weighted_edges_from(np.concatenate(results, axis=0))
    if dir_name:
        store_graph(G, dir_name, pos, labels)
    return G

def process_lines(graph_lines, n_proc):
    if graph_lines:
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
        G = connecting_nodes(labels, pos, n_proc)#, dir_name=str(time))
        return get_metrics(G, time)
    return None

def read_file_graph(rawgraph):
    global LAST_TIME_READ
    with open(rawgraph, "r") as file_:
        graph_lines = []
        for line in file_:
            if "END" not in line:
                graph_lines.append(line)
            else:
                time = float(line.split(" ")[1])
                graph_lines.append(line)
                tmp_lines = graph_lines.copy()
                graph_lines = []
                if len(tmp_lines) > 1 and time > LAST_TIME_READ:
                    yield tmp_lines
    return None

def measure_graphs(rawgraph='raw_graph.dat', n_proc=None, db=None, collection=None, last_read_time=-1):
    global LAST_TIME_READ
    LAST_TIME_READ = last_read_time
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_logger = logging.getLogger('Logger')
    file_logger.setLevel(logging.DEBUG)
    file_handler = handlers.RotatingFileHandler(
        'graph_measure.log', maxBytes=200 * 1024 * 1024, backupCount=1
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    file_logger.addHandler(file_handler)

    if not os.path.isdir(GRAPH_ROOT):
        os.makedirs(GRAPH_ROOT)

    n_proc = cpu_count() if not n_proc else n_proc
    graph_lines_generator = read_file_graph(rawgraph)
    start = time.time()
    for graph_lines in graph_lines_generator:
        json_measuments = process_lines(graph_lines, n_proc):
        if json_measuments:
            store_metrics(json_measuments, db, collection)
            file_logger.info("Duration >> %s -- Graph size >> %s"%(time.time() - start, json_measuments["n_vehicle"]))
        else:
            file_logger.info("Duration >> %s -- None"%(time.time() - start))
