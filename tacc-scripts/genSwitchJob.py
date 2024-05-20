import os

parent_dir = "/scratch/09498/janechen/"
policy_list = ["NewReno", "Cubic"]

def main():
    for policy in policy_list:
        trace_dir = os.path.join(parent_dir, policy)
        print("trace_dir: ", trace_dir)
        # root is the directory path, file is the file name
        for root, dirs, files in os.walk(trace_dir):
            for file in files:
                cmd = "python /home1/09498/janechen/ns3-transformer-cc/tacc-scripts/genSwitchJobSub.py " + root + " " + file + " &"
                print(cmd)
                break
            # break
    print("wait")

if __name__ == "__main__":
    main()