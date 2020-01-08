import sys
import gvr_vanet as gvr

rawgraph = sys.argv[1]
if len(sys.argv) == 3:
    last_read_time = float(sys.argv[2])
else:
    last_read_time = -1

gvr.measure_graphs(rawgraph=rawgraph, n_proc=4, last_read_time=last_read_time)

