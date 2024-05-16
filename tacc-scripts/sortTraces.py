import os
import sys
import shutil

parent_path = "/scratch/09498/janechen/"
# old_dir_name_list = ["clean-traces", "clean-traces-add-cubic", "clean-traces-add-reno"]
dir = sys.argv[1]

# default policy parameters
cubic_beta = 0.7
cubic_c = 0.4
reno_alpha = 1
reno_beta = 2

# for dir in old_dir_name_list:
for file_name in os.listdir(os.path.join(parent_path, dir)):
    # print(file_name)
    file_path = os.path.join(parent_path, dir, file_name)
    policy = file_name.split('-')[0][3:]
    # print(policy)
    # print(len(file_name.split('-')))
    
    if len(file_name.split('-')) > 17:
        if policy == 'Cubic':
            cubic_beta = float(file_name.split('-')[1])
            cubic_c = float(file_name.split('-')[2])
        if policy == "NewReno":
            reno_alpha = float(file_name.split('-')[1])
            reno_beta = float(file_name.split('-')[2])
    transport = file_name.split('-')[-5].split('.')[0]
    if policy == 'Cubic':
        output_dir = os.path.join(parent_path, 'Cubic', 'Cubic-'+str(cubic_beta)+'-'+str(cubic_c), transport)
    if policy == 'NewReno':
        output_dir = os.path.join(parent_path, 'NewReno', 'NewReno-'+str(reno_alpha)+'-'+str(reno_beta), transport)
    # print(output_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    if not os.path.exists(os.path.join(output_dir, file_name)):
        shutil.copyfile(file_path, os.path.join(output_dir, file_name))
    # break