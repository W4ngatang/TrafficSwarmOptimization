import os
import sys
import optparse
import subprocess
import random
import pdb
import xml.etree.ElementTree as ET
from matplotlib import pyplot as plt
import numpy as np
from runner import run_sumo

#helper function to display solutions on console in friendly manner
def convert_aco_setting(settings, k):
    new_setting = []
    for setting in settings:
        tl_sets = []
        cycle_stage = np.floor(setting / (k**4))
        tl_sets.append(cycle_stage)
        setting = setting % (k**4)
        tl_sets.append(np.floor(setting / (k**3)))
        setting = setting % (k**3)
        tl_sets.append(np.floor(setting / (k**2)))
        setting = setting % (k**2)
        tl_sets.append(np.floor(setting / (k**1)))
        setting = setting % (k**1)
        tl_sets.append(np.floor(setting / (k**0)))
        new_setting.append(tl_sets)
    return new_setting

#ACO algorithm
def run_aco(n):
    
    num_time_options = 2
    m = 4 * (num_time_options**4)
    N = n * n

    num_rounds = 1000########
    batch_size = 2#m#####

    evaporation = 0.0
    rank_cutoff = int(batch_size / 2)

    #define the edge pheromone values
    phero = np.ones((N, m))

    #define best value so far
    best_value = 100000000.0
    #define the corresponding setting
    best_setting = None

    fl1 = open("general.txt", "w")
    fl2 = open("best_settings.txt", "w")
    fl3 = open("best_performances.txt", "w")
    fl4 = open("pheromones.txt", "w")

    for i in range(num_rounds):

        all_settings = []
        all_performances = []
        for j in range(batch_size):
            print "Currently in round:"
            print i
            print "Currently working ant:"
            print j

            this_setting = [0] * N
            eligible_verts = list(range(0,N))

            for k in range(N):
                #probabilistically choose an intersection and setting
                available_values = []
                available_probs = []
                normalizer = 0.0
                for vert in eligible_verts:
                    for l in range(m):
                        available_values.append([vert,l])
                        available_probs.append(phero[vert,l])
                        normalizer += phero[vert,l]
                selection_index = np.random.choice(m*len(eligible_verts), 1, p=(np.asarray(available_probs) / normalizer))
                selection = available_values[selection_index]
                this_setting[selection[0]] = selection[1]
                eligible_verts.remove(selection[0])

            #evaluate solution performance
            this_performance = run_sumo(n, 'summary.xml', this_setting, "aco")

            if this_performance < best_value:
                best_value = this_performance
                best_setting = this_setting

            all_settings.append(this_setting)
            all_performances.append(this_performance)

            formatted_setting = convert_aco_setting(this_setting, num_time_options)

            print this_performance
            print formatted_setting
            print best_value
            print convert_aco_setting(best_setting, num_time_options)

            fl1.write("Round %i, Ant %i\n" % (i, j))
            for eachsetting in formatted_setting:
                for settingterm in eachsetting:
                    fl1.write("%d " % (settingterm))
                fl1.write("\n")
            fl1.write("Mean Time %d\n" % (this_performance))


        print i
        print "Best value:"
        print best_value
        print "Best setting:"
        print convert_aco_setting(best_setting, num_time_options)
        print all_performances

        #update the pheromone values -- part 1
        #first, perform evaporation
        phero = phero * (1.0 - evaporation)
        amount_evaporated = evaporation * N * m

        #rank the m ants this round from best to worst performance
        set_and_perf = zip(all_performances, all_settings)
        set_and_perf.sort()

        #reorder the m ants this round's settings in order by performance
        ordered_settings = []
        for element in set_and_perf:
            ordered_settings.append(element[1])

        #compute number of parts (of the amount_evaporated pheromone) that each of the N*m edges gets allocated
        parts_allocation = np.zeros((N,m))
        ordered_settings = ordered_settings[:rank_cutoff]
        parts_given = rank_cutoff
        for this_setting in ordered_settings:
            for i in range(N):
                parts_allocation[i, this_setting[i]] += parts_given
            parts_given -= 1

        #update the pheromone values -- part 2
        #split up N*(rank_cutoff)*(rank_cutoff + 1)/2 parts of amount_evaporated
        #add performance-based pheromone for this round
        phero = phero + ((parts_allocation / (N * rank_cutoff * (rank_cutoff + 1.0) * 0.5)) * amount_evaporated)

        #fill in txt files with data
        best_setting_formatted = convert_aco_setting(best_setting, num_time_options)
        for eachsetting in best_setting_formatted:
            for settingterm in eachsetting:
                fl2.write("%d " % (settingterm))
            fl2.write("\n")
        fl2.write("\n")
        fl3.write("%.3f, " % (best_value))
        fl4.write("[") 
        for vertex in range(N):
            for l in range(m):
                if l == 0:
                    fl4.write("[")
                fl4.write("%.3f" % (phero[vertex, l]))
                if (l != (m-1)):
                    fl4.write(",") 
                if l == (m-1):
                    fl4.write("]")
                if l == (m-1) and vertex != (N-1):
                    fl4.write(",")
        fl4.write("],") 



n = 5
run_aco(n)
