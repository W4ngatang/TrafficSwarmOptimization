 #!/usr/bin/env python
import os
import sys
import optparse, argparse
import subprocess
import random
import pdb
import xml.etree.ElementTree as ET
from matplotlib import pyplot as plt
import numpy as np

from aco_tls_logic import generate_aco_tls_logic
from pso_tls_logic import generate_pso_tls_logic

try:
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', "tools"))  # tutorial in tests
    sys.path.append(os.path.join(os.environ.get("SUMO_HOME"),"tools"))
    #sys.path.append(os.path.join(os.environ.get("SUMO_HOME", os.path.join(
    #    os.path.dirname(__file__), "..", "..", "..")), "tools"))  # tutorial in docs
    from sumolib import checkBinary
except ImportError:
    sys.exit(
        "please declare environment variable 'SUMO_HOME' as the root directory of your sumo installation (it should contain folders 'bin', 'tools' and 'docs')")

import traci
# the port used for communicating with your sumo instance
PORT = 8873

#helper function for setting up route schedule
def generate_edge_probs(all_edge_ids, seed_val):
    np.random.seed(seed_val) 

    edgeprob = {}
    for edge in all_edge_ids:
        edgeprob[edge] = np.random.random()

    return edgeprob

#helper function for setting up route schedule
def generate_direction_maps(n):
    north = {}
    for i in range(1,(n*(n-1) + 1)):
        north[i] = i+n
    temp = 0
    for i in range((n*(n-1) + 1), n*n + 1):
        north[i] = i + 4*n - 1 - 2*temp
        temp += 1
    for i in range(n*n + 1, n*(n+1) + 1):
        north[i] = i - (n*n)
    for i in range(n*(n+1) + 1, n*(n+4) + 1):
        north[i] = 0

    south = {}
    for i in range(1, n+1):
        south[i] = i + n*n
    for i in range(n+1, n*n + 1):
        south[i] = i - n
    for i in range(n*n + 1, n*(n+2) + 1):
        south[i] = 0
    temp = 0
    for i in range(n*(n+2) + 1, n*(n+3) + 1):
        south[i] = i - 2*n - 1 - 2*temp
        temp += 1
    for i in range(n*(n+3) + 1, n*(n+4) + 1):
        south[i] = 0

    west = {}
    temp = 0
    for i in range(1, n*n + 1):
        if (i % n) != 1:
            west[i] = i - 1
        else:
            west[i] = n*(n+4) - temp
            temp += 1
    for i in range(n*n + 1, n*(n+1) + 1):
        west[i] = 0
    temp = 0
    for i in range(n*(n+1) + 1, n*(n+2) + 1):
        west[i] = (temp + 1)*n 
        temp +=1
    for i in range(n*(n+2) + 1, n*(n+4) + 1):
        west[i] = 0

    east = {}
    temp = 0
    for i in range(1, n*n + 1):
        if (i % n) != 0:
            east[i] = i + 1
        else:
            east[i] = n*n + n + 1 + temp
            temp += 1
    for i in range(n*n + 1, n*(n+3) + 1):
        east[i] = 0
    temp = 0
    for i in range(n*(n+3) + 1, n*(n+4) + 1):
        east[i] = 1 + n*(n - 1 - temp)
        temp += 1

    overall = [north, south, west, east]
    return overall

def generate_routefile(edge_prob, direction_map, n, seed_val):
    np.random.seed(seed_val)  # make tests reproducible

    T = 3600  # number of time steps
    with open("data/cross.rou.xml", "w") as routes:
        print >> routes, """<routes>
        <vType id="car" accel="0.8" decel="4.5" sigma="0.5" length="5" minGap="2.5" maxSpeed="30" guiShape="passenger"/>
        """
        #to determine car spawning rate
        max_per_timestep = 10
        prob = 0.1
        
        route_dirs = ["NW", "NE", "SW", "SE"]
        north = direction_map[0]
        south = direction_map[1]
        west = direction_map[2]
        east = direction_map[3]

        cars_so_far = 0
        for i in range(T):
            num_cars = np.random.binomial(max_per_timestep, prob)
            for j in range(num_cars):
                this_route = {}
                this_route["num"] = cars_so_far
                this_route["source"] = np.random.randint(1,(n*(n+4) + 1))
                this_route["dir"] = route_dirs[np.random.randint(4)]
                this_route["edges"] = []
                this_route["curloc"] = this_route["source"]

                if this_route["source"] > n*n:
                #Case of not starting at a traffic light: make the first edge in the route be moving to a traffic light
                    if this_route["source"] <= n*(n+1):
                        this_route["curloc"] = north[this_route["source"]]
                    elif this_route["source"] <= n*(n+2):
                        this_route["curloc"] = west[this_route["source"]]
                    elif this_route["source"] <= n*(n+3):
                        this_route["curloc"] = south[this_route["source"]]
                    else:
                        this_route["curloc"] = east[this_route["source"]]
                    this_route["edges"].append(this_route["source"] * 1000 + this_route["curloc"])

                #Probabilistically generate a path for this car
                while True:
                    #find the two eligible vertices to move to
                    v1 = 0
                    v2 = 0
                    if this_route["dir"] == "NW":
                        v1 = north[this_route["curloc"]]
                        v2 = west[this_route["curloc"]]
                    elif this_route["dir"] == "NE":
                        v1 = north[this_route["curloc"]]
                        v2 = east[this_route["curloc"]]
                    elif this_route["dir"] == "SW":
                        v1 = south[this_route["curloc"]]
                        v2 = west[this_route["curloc"]]
                    else:
                        v1 = south[this_route["curloc"]]
                        v2 = east[this_route["curloc"]]

                    if v1 == 0 or v2 == 0:
                        break

                    #find the corresponding edges and add to path based on relative edge weights
                    e1 = 1000*this_route["curloc"] + v1
                    e2 = 1000*this_route["curloc"] + v2
                    if np.random.random() < (edge_prob[e1] / (edge_prob[e1] + edge_prob[e2])):
                        if this_route["source"] == (e1 % 1000):
                            break
                        this_route["edges"].append(e1)
                        this_route["curloc"] = (e1 % 1000)
                    else:
                        if this_route["source"] == (e2 % 1000):
                            break
                        this_route["edges"].append(e2)
                        this_route["curloc"] = (e2 % 1000)

                    #with some probability, stop path. Path lengths distributed Geometrically with mean n/2
                    if np.random.random() < (1.0 / (2.0 * n)):
                        break

                #build xml for both route and vehicle
                edgestring = ""
                for edge in this_route["edges"]:
                    edgestring = edgestring + " " + str(edge)
                edgestring = edgestring[1:]

                print >> routes, '    <route id="r%i" edges="%s" />' % (cars_so_far, edgestring)
                print >> routes, '    <vehicle id="v%i" type="car" route="r%i" depart="%i" />' % (cars_so_far, cars_so_far, i)

                cars_so_far += 1 
        print >> routes, "</routes>"

        
def generate_tls_logic(n, times):
#This is the default logic for testing out SUMO. Simulations should use their own functions instead
    with open("data/cross.add.xml", "w") as logic:
        print >> logic, '<additional>'

        for i in range(1,(n*n + 1)):
            print >> logic, '    <tlLogic id="%i" programID="stuff" offset="0" type="static">' % (i)
            print >> logic, '         <phase duration="%d" state="rrrGGgrrrGGg" />' % (times[0])
            print >> logic, '         <phase duration="%d" state="rrryygrrryyg" />' % (5)
            print >> logic, '         <phase duration="%d" state="rrrrrGrrrrrG" />' % (times[1])
            print >> logic, '         <phase duration="%d" state="rrrrryrrrrry" />' % (5)
            print >> logic, '         <phase duration="%d" state="GGgrrrGGgrrr" />' % (times[2])
            print >> logic, '         <phase duration="%d" state="yygrrryygrrr" />' % (5)
            print >> logic, '         <phase duration="%d" state="rrGrrrrrGrrr" />' % (times[3])
            print >> logic, '         <phase duration="%d" state="rryrrrrryrrr" />' % (5)
            print >> logic, "    </tlLogic>"
        print >> logic, "</additional>"

#generates the xml file for the grid of nodes
def generate_nodes(n): #n^2 = number of total intersections
    with open("data/cross.nod.xml", "w") as nodes:
        print >> nodes, '''<?xml version="1.0" encoding="UTF-8"?>
<nodes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/nodes_file.xsd">'''

        for i in range(n):
            for j in range(n):
                print >> nodes, '    <node id="%i" x="%d" y="%d"  type="traffic_light"/>' % ((n*i + j + 1), (i+1)*500, (j+1)*500)
        for i in range(n):
            print >> nodes, '    <node id="%i" x="%d" y="%d"  type="priority"/>' % ((n*n + i + 1), (i+1)*500, 0)
        for i in range(n):
            print >> nodes, '    <node id="%i" x="%d" y="%d"  type="priority"/>' % ((n*(n+1) + i + 1), (n+1)*500, (i+1)*500)
        for i in range(n):
            print >> nodes, '    <node id="%i" x="%d" y="%d"  type="priority"/>' % ((n*(n+2) + i + 1), (n-i)*500, (n+1)*500)
        for i in range(n):
            print >> nodes, '    <node id="%i" x="%d" y="%d"  type="priority"/>' % ((n*(n+3) + i + 1), 0, (n-i)*500)

        print >> nodes, '</nodes>'

#general-purpose random number helper function
def get_rand_num(low, high):
    return (np.random.random() * (high - low) + low)

#generate edges between nodes for edges xml file
def generate_edges(n):
    all_edge_ids = []

    with open("data/cross.edg.xml", "w") as edges:
        print >> edges, '''<?xml version="1.0" encoding="UTF-8"?>
<edges xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/edges_file.xsd">'''

        min_s = 5.0
        max_s = 30.0

        #edges at the bottom, right, top, left
        for i in range(1,(n+1)):
            print >> edges, '    <edge id="%i" from="%i" to="%i" priority="80" numLanes="1" speed="%d" />' % ((1000*(n*n + i) + i), (n*n + i), i, get_rand_num(min_s,max_s))
            print >> edges, '    <edge id="%i" from="%i" to="%i" priority="80" numLanes="1" speed="%d" />' % ((1000*i + n*n + i), i, (n*n + i), get_rand_num(min_s,max_s))
            all_edge_ids.append((1000*(n*n + i) + i))
            all_edge_ids.append((1000*i + n*n + i))
        for i in range(1,(n+1)):
            print >> edges, '    <edge id="%i" from="%i" to="%i" priority="80" numLanes="1" speed="%d" />' % ((1000*(n*(n+1) +i) + (n*i)), (n*(n+1) +i), (n*i), get_rand_num(min_s,max_s))
            print >> edges, '    <edge id="%i" from="%i" to="%i" priority="80" numLanes="1" speed="%d" />' % ((1000*n*i + (n*(n+1) +i)), (n*i), (n*(n+1) + i), get_rand_num(min_s,max_s))
            all_edge_ids.append((1000*(n*(n+1) +i) + (n*i)))
            all_edge_ids.append((1000*n*i + (n*(n+1) +i)))
        for i in range(1,(n+1)):
            print >> edges, '    <edge id="%i" from="%i" to="%i" priority="80" numLanes="1" speed="%d" />' % ((1000*(n*(n+2) +i) + (n*n+1-i)), (n*(n+2) +i), (n*n+1-i), get_rand_num(min_s,max_s))
            print >> edges, '    <edge id="%i" from="%i" to="%i" priority="80" numLanes="1" speed="%d" />' % ((1000*(n*n+1-i) + (n*(n+2) +i)), (n*n+1-i), (n*(n+2) + i), get_rand_num(min_s,max_s))
            all_edge_ids.append((1000*(n*(n+2) +i) + (n*n+1-i)))
            all_edge_ids.append((1000*(n*n+1-i) + (n*(n+2) +i)))
        for i in range(1,(n+1)):
            print >> edges, '    <edge id="%i" from="%i" to="%i" priority="80" numLanes="1" speed="%d" />' % ((1000*(n*(n+3) +i) + (n*(n-i)+1)), (n*(n+3) +i), (n*(n-i)+1), get_rand_num(min_s,max_s))
            print >> edges, '    <edge id="%i" from="%i" to="%i" priority="80" numLanes="1" speed="%d" />' % ((1000*(n*(n-i)+1) + (n*(n+3) +i)), (n*(n-i)+1), (n*(n+3) + i), get_rand_num(min_s,max_s))
            all_edge_ids.append((1000*(n*(n+3) +i) + (n*(n-i)+1)))
            all_edge_ids.append((1000*(n*(n-i)+1) + (n*(n+3) +i)))

        #horizontal edges between intersections
        for i in range(n):
            for j in range(n-1):
                print >> edges, '    <edge id="%i" from="%i" to="%i" priority="80" numLanes="1" speed="%d" />' % (1000*(n*i + 1 + j)+(n*i + 2 + j), (n*i + 1 + j), (n*i + 2 + j), get_rand_num(min_s,max_s))
                print >> edges, '    <edge id="%i" from="%i" to="%i" priority="80" numLanes="1" speed="%d" />' % (1000*(n*i + 2 + j)+(n*i + 1 + j), (n*i + 2 + j), (n*i + 1 + j), get_rand_num(min_s,max_s))
                all_edge_ids.append(1000*(n*i + 1 + j)+(n*i + 2 + j))
                all_edge_ids.append(1000*(n*i + 2 + j)+(n*i + 1 + j))

        #vertical edges between intersections
        for i in range(n):
            for j in range(n-1):
                print >> edges, '    <edge id="%i" from="%i" to="%i" priority="80" numLanes="1" speed="%d" />' % (1000*(n*j + 1 + i)+(n*(j+1) + 1 + i), (n*j + 1 + i), (n*(j+1) + 1 + i), get_rand_num(min_s,max_s))
                print >> edges, '    <edge id="%i" from="%i" to="%i" priority="80" numLanes="1" speed="%d" />' % (1000*(n*(j+1) + 1 + i)+(n*j + 1 + i), (n*(j+1) + 1 + i), (n*j + 1 + i), get_rand_num(min_s,max_s))
                all_edge_ids.append(1000*(n*j + 1 + i)+(n*(j+1) + 1 + i))
                all_edge_ids.append(1000*(n*(j+1) + 1 + i)+(n*j + 1 + i))

        print >> edges, '</edges>'
    return all_edge_ids

#build all the connection links between edges for the connections xml file
def generate_connections(n):
    with open("data/cross.con.xml", "w") as connections:
        print >> connections, '''<?xml version="1.0" encoding="iso-8859-1"?>
<connections xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/connections_file.xsd">'''

        def print_intersection_connections(inedges, outedges):
            for i in range(4):
                for j in range(1,4):
                    print >> connections, '    <connection from="%i" to="%i"/>' % (inedges[i], outedges[(i+j) % 4])

        all_intersections_in = []
        all_intersections_out = []

        #intersections that are not on the border (there are (n-2) x (n-2) of these)
        for i in range(1,n-1):
            for j in range(1,n-1):
                int_number = n*i + j + 1 
                this_in_int = [1000*(int_number-n) + int_number, 1000*(int_number+1) + int_number, 1000*(int_number+n) + int_number, 1000*(int_number-1) + int_number]
                this_out_int = [1000*(int_number) + int_number - n, 1000*(int_number) + int_number + 1, 1000*(int_number) + int_number + n, 1000*(int_number) + int_number - 1]
                all_intersections_in.append(this_in_int)
                all_intersections_out.append(this_out_int)

        #intersections that are on the corners (there are 4 of these)
        all_intersections_in.append([1000*(n*n + 1) + 1, 1000*(2) + 1, 1000*(1+n) + 1, 1000*(n*(n+4)) + 1])
        all_intersections_out.append([1000*(1) + n*n + 1, 1000*(1) + 2, 1000*(1) + 1 + n, 1000*(1) + n*(n+4)])
        all_intersections_in.append([1000*(n*(n+1)) + n, 1000*(n*(n+1) + 1) + n, 1000*(2*n) + n, 1000*(n-1) + n])
        all_intersections_out.append([1000*(n) + n*(n+1), 1000*(n) + n*(n+1) + 1, 1000*(n) + 2*n, 1000*(n) + n-1])
        all_intersections_in.append([1000*(n*(n-1)) + n*n, 1000*(n*(n+2)) + n*n, 1000*((n+1)*(n+1)) + n*n, 1000*(n*n-1) + n*n])
        all_intersections_out.append([1000*(n*n) + n*(n-1), 1000*(n*n) + n*(n+2), 1000*(n*n) + (n+1)*(n+1), 1000*(n*n) + n*n-1])
        all_intersections_in.append([1000*((n-1)*(n-1)) + (n*n-n+1), 1000*(n*n-n+2) + (n*n-n+1), 1000*(n*(n+3)) + (n*n-n+1), 1000*(n*n+3*n+1) + (n*n-n+1)])
        all_intersections_out.append([1000*(n*n-n+1) + (n-1)*(n-1), 1000*((n*n-n+1)) + (n*n-n+2), 1000*((n*n-n+1)) + n*(n+3), 1000*(n*n-n+1) + (n*n+3*n+1)])

        #intersections on the sides that are not corners (there are 4n - 4 of these)
        for i in range(2,n):
            int_number = i
            this_in_int = [1000*(n*n+i) + int_number, 1000*(int_number+1) + int_number, 1000*(int_number+n) + int_number, 1000*(int_number-1) + int_number]
            this_out_int = [1000*(int_number) + (n*n+i), 1000*(int_number) + int_number + 1, 1000*(int_number) + int_number + n, 1000*(int_number) + int_number - 1]
            all_intersections_in.append(this_in_int)
            all_intersections_out.append(this_out_int)
            int_number = i*n
            this_in_int = [1000*(int_number-n) + int_number, 1000*(n*n+n+i) + int_number, 1000*(int_number+n) + int_number, 1000*(int_number-1) + int_number]
            this_out_int = [1000*(int_number) + int_number - n, 1000*(int_number) + (n*n+n+i), 1000*(int_number) + int_number + n, 1000*(int_number) + int_number - 1]
            all_intersections_in.append(this_in_int)
            all_intersections_out.append(this_out_int)
            int_number = n*n - i + 1
            this_in_int = [1000*(int_number-n) + int_number, 1000*(int_number+1) + int_number, 1000*(n*n + 2*n + i) + int_number, 1000*(int_number-1) + int_number]
            this_out_int = [1000*(int_number) + int_number - n, 1000*(int_number) + int_number + 1, 1000*(int_number) + (n*n + 2*n + i), 1000*(int_number) + int_number - 1]
            all_intersections_in.append(this_in_int)
            all_intersections_out.append(this_out_int)
            int_number = n*(i-1) + 1
            this_in_int = [1000*(int_number-n) + int_number, 1000*(int_number+1) + int_number, 1000*(int_number+n) + int_number, 1000*(n*(n+4)-i+1) + int_number]
            this_out_int = [1000*(int_number) + int_number - n, 1000*(int_number) + int_number + 1, 1000*(int_number) + int_number + n, 1000*(int_number) + (n*(n+4)-i+1)]
            all_intersections_in.append(this_in_int)
            all_intersections_out.append(this_out_int)

        for i in range(len(all_intersections_in)):
            print_intersection_connections(all_intersections_in[i], all_intersections_out[i])
        
        print >> connections, '</connections>'

def run(max_step=-1):
    
    """execute the TraCI control loop"""
    traci.init(PORT)
    step = 0
    # we start with phase 2 where EW has green
    #traci.trafficlights.setPhase("0", 0)
    #pdb.set_trace()
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        step += 1
        if step > max_step and max_step > 0:
            break
    traci.close()
    sys.stdout.flush()

#to setup the xml files and run the default traffic light logic case of SUMO
def setup_and_run_sumo(n, seed_val):

    summaryFile = 'summary.xml'

    generate_nodes(n) 
    all_edge_ids = generate_edges(n) 
    generate_connections(n) 

    meanWaits = []
    meanTravels = []

    direction_map = generate_direction_maps(n) 
    edge_prob = generate_edge_probs(all_edge_ids, seed_val)

    generate_routefile(edge_prob, direction_map, n, seed_val)

    run_sumo(n, summaryFile, [40,5,20,5])

#to only run SUMO simulation (and leave XML files the way they are already)
#this can run the default SUMO traffic light logic or the ACO logic or the PSO logic
#it is used to evaluate solutions within the PSO and ACO algorithms
#note that setup_and_run_sumo must be called first before this gets used
#for run_sumo, the maps and route schedules remain identical between iterations
def run_sumo(n, summaryFile='summary.xml', tl_data=None, thetype=None):
    travel_times = []
    nsims = 1

    if thetype == "aco":
        generate_aco_tls_logic(n,tl_data)
    elif thetype == "pso":
        generate_pso_tls_logic(tl_data)
    elif len(tl_data) == 4:
        #default setup case
        generate_tls_logic(n,tl_data)

    for j in xrange(nsims):

        sumoBinary = checkBinary('sumo')

        # this is the normal way of using traci. sumo is started as a
        # subprocess and then the python script connects and runs
        sumoProcess = subprocess.Popen([sumoBinary, "-c", "data/cross.sumocfg", "--additional-files", "data/cross.add.xml", 
                                        "--tripinfo-output", "tripinfo.xml", #"--duration-log.statistics", "true", 
                                        "--summary", summaryFile, "--remote-port", str(PORT)], stdout=sys.stdout, stderr=sys.stderr)
        run()
        sumoProcess.wait()
        
        tree = ET.parse(summaryFile)
        root = tree.getroot()
        totalTravel = 0.0
        prev_num_cars_done = 0.0
        for child in root:
            totalTravel += float(child.attrib['meanTravelTime']) * (float(child.attrib['ended']) - prev_num_cars_done)
            prev_num_cars_done = float(child.attrib['ended'])

        travel_times.append(totalTravel / prev_num_cars_done)

    print "Mean travel time:", (sum(travel_times) / len(travel_times))
    return (sum(travel_times) / len(travel_times))

def main(arguments):
    global args
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('n', help="size of grid (along one side)",type=int, default=5)
    parser.add_argument('seed', help="seed value",type=int, default=42)
    parser.add_argument('max_step', help="max steps per simulation",type=int, default=-1)
    parser.add_argument('use_gui', help="use gui or not", type=bool, default=False)
    args = parser.parse_args(arguments)
    n = args.n
    seed_val = args.seed
    max_step = args.max_step
    if args.use_gui:
        sumoBinary = checkBinary('sumo')
    else:
        sumoBinary = checkBinary('sumo-gui')

    setup_and_run_sumo(n, seed_val)

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
