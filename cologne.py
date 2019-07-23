import sys
import gvr_vanet as gvr

sumocfg = sys.argv[1]
if len(sys.argv) > 2:
    tripinfo = sys.argv[2]
    rawgraph = sys.argv[3]
else:
    tripinfo = 'trip_info.xml'
    rawgraph = '../graphs.txt'#'raw_graph.dat'

# client = MongoClient('localhost', 27017)
# db = client.vanet

# gvr.run_simulation(sumocfg, minutes=2, tripinfo=tripinfo, rawgraph=rawgraph)
gvr.measure_graphs(rawgraph=rawgraph)

