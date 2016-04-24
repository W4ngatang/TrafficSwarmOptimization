 #!/usr/bin/env python
"""
@file    runner.py
@author  Lena Kalleske
@author  Daniel Krajzewicz
@author  Michael Behrisch
@author  Jakob Erdmann
@date    2009-03-26
@version $Id: runner.py 19535 2015-12-05 13:47:18Z behrisch $

Tutorial for traffic light control via the TraCI interface.

SUMO, Simulation of Urban MObility; see http://sumo.dlr.de/
Copyright (C) 2009-2015 DLR/TS, Germany

This file is part of SUMO.
SUMO is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.
"""

import os
import sys
import optparse
import subprocess
import random
import pdb
import xml.etree.ElementTree as ET
from matplotlib import pyplot as plt

# we need to import python modules from the $SUMO_HOME/tools directory
try:
    sys.path.append(os.path.join(os.path.dirname(
        __file__), '..', '..', '..', '..', "tools"))  # tutorial in tests
    sys.path.append(os.path.join(os.environ.get("SUMO_HOME", os.path.join(
        os.path.dirname(__file__), "..", "..", "..")), "tools"))  # tutorial in docs
    from sumolib import checkBinary
except ImportError:
    sys.exit(
        "please declare environment variable 'SUMO_HOME' as the root directory of your sumo installation (it should contain folders 'bin', 'tools' and 'docs')")

import traci
# the port used for communicating with your sumo instance
PORT = 8873


def generate_routefile():
    random.seed(42)  # make tests reproducible
    N = 3600  # number of time steps
    # demand per second from different directions
    pWE = 1. / 10
    pEW = 1. / 10
    pNS = 1. / 30
    with open("data/cross.rou.xml", "w") as routes:
        print >> routes, """<routes>
        <vType id="typeWE" accel="0.8" decel="4.5" sigma="0.5" length="5" minGap="2.5" maxSpeed="16.67" guiShape="passenger"/>
        <vType id="typeNS" accel="0.8" decel="4.5" sigma="0.5" length="7" minGap="3" maxSpeed="25" guiShape="bus"/>

        <route id="right" edges="51o 1i 2o 52i" />
        <route id="left" edges="52o 2i 1o 51i" />
        <route id="down" edges="54o 4i 3o 53i" />"""
        lastVeh = 0
        vehNr = 0
        for i in range(N):
            if random.uniform(0, 1) < pWE:
                print >> routes, '    <vehicle id="right_%i" type="typeWE" route="right" depart="%i" />' % (
                    vehNr, i)
                vehNr += 1
                lastVeh = i
            if random.uniform(0, 1) < pEW:
                print >> routes, '    <vehicle id="left_%i" type="typeWE" route="left" depart="%i" />' % (
                    vehNr, i)
                vehNr += 1
                lastVeh = i
            if random.uniform(0, 1) < pNS:
                print >> routes, '    <vehicle id="down_%i" type="typeNS" route="down" depart="%i" color="1,0,0"/>' % (
                    vehNr, i)
                vehNr += 1
                lastVeh = i
        print >> routes, "</routes>"

        
def generate_tls_logic(i):
    with open("data/cross.add.xml", "w") as logic:
        print >> logic, '<additional>'
        print >> logic, '    <tlLogic id="0" programID="my_program" offset="0" type="static">'
        print >> logic, '         <phase duration="%d" state="GrGr" />' % (i)
        print >> logic, '         <phase duration="%d" state="yryr" />' % (5)
        print >> logic, '         <phase duration="%d" state="rGrG" />' % (50 - i)
        print >> logic, '         <phase duration="%d" state="ryry" />' % (5)
        print >> logic, "    </tlLogic>"
        print >> logic, "</additional>"

# The program looks like this
#    <tlLogic id="0" type="static" programID="0" offset="0">
# the locations of the tls are      NESW
#        <phase duration="31" state="GrGr"/>
#        <phase duration="6"  state="yryr"/>
#        <phase duration="31" state="rGrG"/>
#        <phase duration="6"  state="ryry"/>
#    </tlLogic>


def run():
    """execute the TraCI control loop"""
    traci.init(PORT)
    step = 0
    # we start with phase 2 where EW has green
    traci.trafficlights.setPhase("0", 2)
    #pdb.set_trace()
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        '''
        if traci.trafficlights.getPhase("0") == 2:
            # we are not already switching
            if traci.inductionloop.getLastStepVehicleNumber("0") > 0:
                # there is a vehicle from the north, switch
                traci.trafficlights.setPhase("0", 3)
            else:
                # otherwise try to keep green for EW
                traci.trafficlights.setPhase("0", 2)
        '''
        step += 1
    traci.close()
    sys.stdout.flush()


def get_options():
    optParser = optparse.OptionParser()
    optParser.add_option("--nogui", action="store_true",
                         default=False, help="run the commandline version of sumo")
    options, args = optParser.parse_args()
    return options


# this is the main entry point of this script
if __name__ == "__main__":
    options = get_options()
    summaryFile = 'summary.xml'
    nsims = 10
	
    # this script has been called from the command line. It will start sumo as a
    # server, then connect and run
    if options.nogui:
        sumoBinary = checkBinary('sumo')
    else:
        sumoBinary = checkBinary('sumo-gui')

    # first, generate the route file for this simulation
    meanWaits = []
    meanTravels = []
    
    for i in xrange(5, 45, 5):
        print "Iteration", i
        generate_tls_logic(i)
        iWait = []
        iTravel = []
        for j in xrange(nsims):

            generate_routefile()
            # this is the normal way of using traci. sumo is started as a
            # subprocess and then the python script connects and runs
            sumoProcess = subprocess.Popen([sumoBinary, "-c", "data/cross.sumocfg", "--additional-files", "data/cross.add.xml", 
                                            "--tripinfo-output", "tripinfo.xml", "--duration-log.statistics", "true", 
                                            "--summary", summaryFile, "--remote-port", str(PORT)], stdout=sys.stdout, stderr=sys.stderr)
            run()
            sumoProcess.wait()
            
            tree = ET.parse(summaryFile)
            root = tree.getroot()
            maxTravel = 0
            maxWait = 0
            meanTravel = 0
            meanWait = 0
            nsteps = 0
            for child in root:
                if child.attrib['meanTravelTime'] > maxTravel:
                    maxTravel = child.attrib['meanTravelTime']
                if child.attrib['meanWaitingTime'] > maxWait:
                    maxWait = child.attrib['meanWaitingTime']
                meanTravel += float(child.attrib['meanTravelTime'])
                meanWait += float(child.attrib['meanWaitingTime'])
                nsteps += 1
                    
            iWait.append(meanWait/nsteps)
            iTravel.append(meanTravel/nsteps)
        meanTravels.append(sum(iTravel)/nsims)
        meanWaits.append(sum(iWait)/nsims)
    plt.plot(range(5,45,5), meanWaits)
    plt.show()
    plt.plot(range(5,45,5), meanTravels)
    plt.show()
    pdb.set_trace()