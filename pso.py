import os
import sys
import optparse
import subprocess
import random
import pdb
import xml.etree.ElementTree as ET
from matplotlib import pyplot as plt
import numpy as np
import argparse
from runner import run_sumo

def pso(nparticles, niters, c0, c1, outfile="pso", min_time=5., max_time=30., max_velocity=10., seed=42):
    # ALGORITHM
    # n: number of particles
    # d: size of position + velocity vector
    # optimus/optimal: globally best position/score
    # primes/primals: agent best position/score
    nstates = 4
    nlights = 25
    #np.random.seed(seed)

    # initialize everything uniformly at random
    positions = np.random.uniform(min_time, max_time/2, (nparticles, nlights, nstates))
    velocities = np.random.uniform(-max_velocity, max_velocity, (nparticles, nlights, nstates))
    primes = np.zeros((nparticles, nlights, nstates))
    primals = [0]*nparticles
    optimus = np.zeros((nparticles, nlights, nstates))
    optimal = 100000 # really high number
    
    for i in xrange(nparticles):
        primals[i] = run_sumo(nlights, 'summary.xml', positions[i], "pso")
        primes[i] = positions[i]
        if primals[i] < optimal:
            optimal = primals[i]
            optimus = np.tile(positions[i], (nparticles, 1, 1))
    
    fh = open("output/"+outfile+"_global.csv", "w")
    fh.write("Iteration, Particle, Mean Travel Time\n")

    fh2 = open("output/"+outfile+"_locals.csv","w")
    fh2.write("Iteration, Local Bests\n")

    fh3 = open("output/"+outfile+"_gposition.csv","w")
    fh3.write("Iteration, Particle, Positions\n")

    print >> fh2, "%d " % t
    print >> fh2, primals, "\n"
    print >> fh, "%d, %d, %.5f\n" % (t, i, optimal)
    print >> fh3, "%d, %d\n" % (t, i)
    for row in optimus[0]:
        print >> fh3, row

    for t in xrange(niters):
        r0 = np.repeat(np.repeat(c0*np.random.random_sample((nparticles,1,1)), nlights, axis=1), nstates, axis=2)#, nlights, nstates))
        r1 = np.repeat(np.repeat(c1*np.random.random_sample((nparticles,1,1)), nlights, axis=1), nstates, axis=2)#, nlights, nstates))
        velocities = velocities + np.multiply(r0,(primes - positions)) + np.multiply(r1,(optimus - positions))
        positions = np.clip(positions + velocities, min_time, max_time) # clip positions to be within search space
        velocities = np.clip(velocities, -max_velocity, max_velocity)   # clip velocities to be within allowed limits, done after update to hit limit
        for i in xrange(nparticles):
            score = run_sumo(0, 'summary.xml', positions[i], "pso")
            if score < primals[i]:
                primes[i] = positions[i]
                primals[i] = score
                if score < optimal:
                    optimus = np.tile(positions[i], (nparticles, 1, 1))
                    optimal = score
                    print >> fh, "%d, %d, %.5f\n" % (t, i, optimal)
                    print >> fh3, "%d, %d\n" % (t, i)
                    for row in optimus[0]:
                        print >> fh3, row
        print >> fh2, "%d " % t
        print >> fh2, primals, "\n"
        
def main(arguments):
    global args
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('nparticles', help="number of particles",type=int, default=25)
    parser.add_argument('niters', help="number of iterations",type=int, default = 1000)
    parser.add_argument('c0', help="number of iterations",type=float, default=2.)
    parser.add_argument('c1', help="number of iterations",type=float, default=2.)
    parser.add_argument('predfile', help="file to write to",type=str, default="pso")
    parser.add_argument('min_time', help="number of iterations",type=float, default=5.)
    parser.add_argument('max_time', help="number of iterations",type=float, default=30.)
    parser.add_argument('max_velocity', help="number of iterations",type=float, default=10.)
    args = parser.parse_args(arguments)
    nparticles = args.nparticles
    niters = args.niters
    c0 = args.c0
    c1 = args.c1
    min_time = args.min_time
    max_time = args.max_time
    max_velocity = args.max_velocity
    predfile = args.predfile
    pso(nparticles, niters, c0, c1, predfile, min_time, max_time, max_velocity)

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
