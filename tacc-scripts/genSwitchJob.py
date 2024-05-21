import os
import random

parent_dir = "/scratch/09498/janechen/"
policy_list = ["NewReno", "Cubic"]
file_limit = 100

def main():
    for policy in policy_list:
        trace_dir = os.path.join(parent_dir, policy)
        # print("trace_dir: ", trace_dir)
        # root is the directory path, file is the file name
        
        # max_jobs=3; cur_jobs=0
        # for ((i=0; i<6; i++)); do
        #   # If true, wait until the next background job finishes to continue.
        #   ((cur_jobs >= max_jobs)) && wait -n
        #   # Increment the current number of jobs running.
        #   ./j"$i" & ((++cur_jobs))
        # done
        # wait
        print("max_jobs=48; cur_jobs=0")
        for root, dirs, files in os.walk(trace_dir):
            if files and (root.split("/")[-2] == "NewReno-1-2" or root.split("/")[-2] == "Cubic-0.7-0.4"):
                file_count = len(files)
                job_num = 0
                while job_num < file_limit:
                    file = files[random.randint(0, file_count-1)]
                    print("((cur_jobs >= max_jobs)) && wait -n")
                    cmd = "python /home1/09498/janechen/ns3-transformer-cc/tacc-scripts/genSwitchJobSub.py " + root + " " + file
                    print(cmd+" & ((++cur_jobs))")
                # for file in files:
                #     print("((cur_jobs >= max_jobs)) && wait -n")
                #     cmd = "python /home1/09498/janechen/ns3-transformer-cc/tacc-scripts/genSwitchJobSub.py " + root + " " + file
                #     print(cmd+" & ((++cur_jobs))")
                #     break
        print("wait")

if __name__ == "__main__":
    main()