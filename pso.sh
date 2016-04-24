#!/bin/bash
# My first script

python pso.py 25 500 2. 2. pso25 5 30 10 # standard
python pso.py 10 500 2. 2. pso10 5 30 10 # fewer particles
python pso.py 25 500 1. 1. pso1 5 30 10 # smaller c0, c1
python pso.py 25 500 3. 3. pso3 5 30 10 # larger c0, c1
