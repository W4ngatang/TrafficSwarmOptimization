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
def generate_aco_tls_logic(n,this_setting):
    #assumes settings are in the 4 * 2 * 2 * 2 * 2 variety: each intersection has 64 total possible settings

    with open("data/cross.add.xml", "w") as logic:
        print >> logic, '<additional>'

        strings = ["rrrGGgrrrGGg", "rrryygrrryyg", "rrrrrGrrrrrG", "rrrrryrrrrry", "GGgrrrGGgrrr", "yygrrryygrrr", "rrGrrrrrGrrr", "rryrrrrryrrr"]
        tl_times = [15,30]

        for i in range(0, n*n):
            times = []
            this_set = this_setting[i] % 16
            times.append(tl_times[int(np.floor(this_set / 8))])
            this_set = this_setting[i] % 8
            times.append(tl_times[int(np.floor(this_set / 4))])
            this_set = this_setting[i] % 4
            times.append(tl_times[int(np.floor(this_set / 2))])
            this_set = this_setting[i] % 2
            times.append(tl_times[int(np.floor(this_set / 1))])

            print >> logic, '    <tlLogic id="%i" programID="stuff" offset="0" type="static">' % (i+1)

            strlst = []
            if this_setting[i] < 16:
                strlst = [0,1,2,3,4,5,6,7]
            elif this_setting[i] < 32:
                strlst = [2,3,4,5,6,7,0,1]
            elif this_setting[i] < 48:
                strlst = [4,5,6,7,0,1,2,3]
            else:
                strlst = [6,7,0,1,2,3,4,5]

            print >> logic, '         <phase duration="%d" state="%s" />' % (times[0], strings[strlst[0]])
            print >> logic, '         <phase duration="%d" state="%s" />' % (5, strings[strlst[1]])
            print >> logic, '         <phase duration="%d" state="%s" />' % (times[1], strings[strlst[2]])
            print >> logic, '         <phase duration="%d" state="%s" />' % (5, strings[strlst[3]])
            print >> logic, '         <phase duration="%d" state="%s" />' % (times[2], strings[strlst[4]])
            print >> logic, '         <phase duration="%d" state="%s" />' % (5, strings[strlst[5]])
            print >> logic, '         <phase duration="%d" state="%s" />' % (times[3], strings[strlst[6]])
            print >> logic, '         <phase duration="%d" state="%s" />' % (5, strings[strlst[7]])
            print >> logic, "    </tlLogic>"

        print >> logic, "</additional>"
