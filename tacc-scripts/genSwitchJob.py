import os
import sys
import random

parent_dir = "/scratch/09498/janechen/"
trace_dir = "/scratch/09498/janechen/ns3-traces/"
exp_per_file = sys.argv[1]

def main():
    print("max_jobs=48; cur_jobs=0")
    for root, dirs, files in os.walk(trace_dir):
        if files:
            for file in files:
                print("((cur_jobs >= max_jobs)) && wait -n")
                cmd = "python /home1/09498/janechen/ns3-transformer-cc/tacc-scripts/genSwitchJobSub.py " + root + file + " " + "switch_output_avg_" + str(exp_per_file)
                print(cmd+" & ((++cur_jobs))")
    print("wait")

if __name__ == "__main__":
    main()