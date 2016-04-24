import os
import sys
import optparse
import subprocess
import random
import pdb
import xml.etree.ElementTree as ET
from matplotlib import pyplot as plt
import numpy as np

#generate traffic light logic XML file for the ACO algorithm
def generate_pso_tls_logic(times):
    #assumes settings are in the 4 * 2 * 2 * 2 * 2 variety: each intersection has 64 total possible settings

    #pdb.set_trace()
    with open("data/cross.add.xml", "w") as logic:
        print >> logic, '<additional>'

        # assume standard, four-way intersections; 8 possible light states
        strings = ["rrrGGgrrrGGg", "rrryygrrryyg", "rrrrrGrrrrrG", "rrrrryrrrrry", "GGgrrrGGgrrr", "yygrrryygrrr", "rrGrrrrrGrrr", "rryrrrrryrrr"]

        for i in xrange(times.shape[0]):
            print >> logic, '    <tlLogic id="%i" programID="stuff" offset="0" type="static">' % (i+1)

            #pdb.set_trace()
            for j in xrange(0,len(strings)/2):
                print >> logic, '         <phase duration="%d" state="%s" />' % (times[i][j], strings[j*2])
                print >> logic, '         <phase duration="5" state="%s" />' % strings[j*2+1]

            print >> logic, "    </tlLogic>"
        print >> logic, "</additional>"
