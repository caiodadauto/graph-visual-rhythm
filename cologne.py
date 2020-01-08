import sys
import gvr_vanet as gvr

sumocfg = sys.argv[1]
if len(sys.argv) == 4:
    tripinfo = sys.argv[2]
    rawgraph = sys.argv[3]
elif  len(sys.argv) == 5:
    tripinfo = sys.argv[2]
    rawgraph = sys.argv[3]
    last_read_time = float(sys.argv[4])
else:
    tripinfo = 'trip_info.xml'
    rawgraph = 'raw_graph.dat'
    last_read_time = -1

gvr.run_simulation(sumocfg, minutes=.5, tripinfo=tripinfo, rawgraph=rawgraph, last_read_time=last_read_time)

