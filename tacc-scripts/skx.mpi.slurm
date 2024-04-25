#!/bin/bash
#----------------------------------------------------
# Sample Slurm job script
#   for TACC Stampede3 SKX nodes
#
#   *** MPI Job in SKX Queue ***
# 
# Last revised: 23 April 2024
#
# Notes:
#
#   -- Launch this script by executing
#      "sbatch skx.mpi.slurm" on Stampede3 login node.
#
#   -- Use ibrun to launch MPI codes on TACC systems.
#      Do not use mpirun or mpiexec.
#
#   -- Max recommended MPI ranks per SKX node: 48
#      (start small, increase gradually).
#
#   -- If you're running out of memory, try running
#      fewer tasks per node to give each task more memory.
#
#----------------------------------------------------

#SBATCH -J gentrace           # Job name
#SBATCH -o gentrace.o%j       # Name of stdout output file
#SBATCH -e gentrace.e%j       # Name of stderr error file
#SBATCH -p skx             # Queue (partition) name
#SBATCH -N 64               # Total # of nodes 
#SBATCH -n 32              # Total # of mpi tasks
#SBATCH -t 24:00:00        # Run time (hh:mm:ss)
#SBATCH --mail-user=janechen@cs.utexas.edu
#SBATCH --mail-type=all    # Send email at begin and end of job

# Other commands must follow all #SBATCH directives...

module list
pwd
date

# Launch MPI code... 

ibrun ./gentrace         # Use ibrun instead of mpirun or mpiexec