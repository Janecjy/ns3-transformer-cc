import os
import sys
import random

parent_dir = "/scratch/09498/janechen/"
trace_dir = os.path.join(parent_dir, sys.argv[1])
exp_per_file = sys.argv[2]

def main():
    print("max_jobs=48; cur_jobs=0")
    for root, dirs, files in os.walk(trace_dir):
        if files:
            for file in files:
                print("((cur_jobs >= max_jobs)) && wait -n")
                cmd = "python /scratch/09498/janechen/tacc-scripts/genSwitchJobSub.py " + root + '/' + file + " " + "switch_output_" + str(exp_per_file)
                print(cmd+" & ((++cur_jobs))")
    print("wait")

if __name__ == "__main__":
    main()