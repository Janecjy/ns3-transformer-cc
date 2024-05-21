import os

parent_dir = "/scratch/09498/janechen/switch_output/"

print("max_jobs=48; cur_jobs=0")
for root, directories, files in os.walk(parent_dir):
    if directories:  #you can check whether a list is empty like that
        #create your file in the current path you checked, it is stored in root variable.
        pass
    print("((cur_jobs >= max_jobs)) && wait -n")
    cmd = "python /home1/09498/janechen/ns3-transformer-cc/tacc-scripts/createLabelDatasetSub.py " + root
    print(cmd+" & ((++cur_jobs))")
print("wait")