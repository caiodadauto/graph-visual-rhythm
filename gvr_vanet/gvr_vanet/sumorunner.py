from __future__ import absolute_import
from __future__ import print_function

import os
import sys
import logging
import subprocess as sub
import logging.handlers as handlers
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import numpy as np

import traci


def run_simulation(sumocfg, minutes=10,  tripinfo="trip_info.xml", rawgraph="raw_graph.dat"):
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_logger = logging.getLogger('Logger')
    file_logger.setLevel(logging.DEBUG)
    file_handler = handlers.RotatingFileHandler(
        'run_sumo.log', maxBytes=200 * 1024 * 1024, backupCount=1
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    file_logger.addHandler(file_handler)

    seconds = 60
    milisseconds = 1000
    minutes = minutes
    interval = minutes * seconds * milisseconds

    traci.start(["sumo", "-c", sumocfg, "--tripinfo-output", tripinfo])

    n = 0

    id_vehicle = 1
    vehicles = {}
    with open(rawgraph, "w") as f:
        while traci.simulation.getMinExpectedNumber() > 0:
            current_time = traci.simulation.getCurrentTime()
            traci.simulationStep()
            if (current_time % interval) == 0:
                n_vehicles = 0
                for veh_id in traci.vehicle.getIDList():
                    speed = traci.vehicle.getSpeed(veh_id)
                    x, y = traci.vehicle.getPosition(veh_id)
                    lon, lat = traci.simulation.convertGeo(x, y)
                    x2, y2 = traci.simulation.convertGeo(lon, lat, fromGeo=True)

                    if veh_id not in vehicles:
                        index = id_vehicle
                        id_vehicle += 1
                        vehicles[veh_id] = id_vehicle
                        n_vehicles += 1
                    else:
                        index = vehicles[veh_id]

                    f.write(str(index) + ":" + str(x2) + ":" + str(y2) + "\n")
                if n_vehicles >= 1:
                    file_logger.info("A Graph was simulated at %s with %s new vehicles."%(current_time, n_vehicles))
                    f.write("END " + str(current_time) + " \n")
                n += 1



# def sumo_generator(interval):
#     id_vehicle = 1
#     vehicles = {}

#     while traci.simulation.getMinExpectedNumber() > 0:
#         currentTime = traci.simulation.getCurrentTime()
#         traci.simulationStep()
#         if (currentTime % interval) == 0:
#             pos = []
#             labels = []
#             n_vehicles = 0
#             for veh_id in traci.vehicle.getIDList():
#                 speed = traci.vehicle.getSpeed(veh_id)
#                 x, y = traci.vehicle.getPosition(veh_id)
#                 lon, lat = traci.simulation.convertGeo(x, y)
#                 x2, y2 = traci.simulation.convertGeo(lon, lat, fromGeo=True)

#                 if veh_id not in vehicles:
#                     index = id_vehicle
#                     id_vehicle += 1
#                     vehicles[veh_id] = id_vehicle
#                     n_vehicles += 1
#                 else:
#                     index = vehicles[veh_id]

#                 pos.append([x2, y2])
#                 labels.append(str(index))
#             if n_vehicles >= 1:
#                 yield {'pos': np.array(pos, dtype=np.float32), 'labels': np.array(labels, dtype='U8')}