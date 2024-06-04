import os
import random
import shutil

def get_leaf_dirs(root_dir):
    leaf_dirs = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if not dirnames:  # This means it's a leaf directory
            leaf_dirs.append(dirpath)
    return leaf_dirs

def select_random_dirs(leaf_dirs, num_dirs):
    selected_dirs = []
    while len(selected_dirs) < num_dirs:
        select_index = random.randint(0, len(leaf_dirs) - 1)
        selected_dir = leaf_dirs[select_index]

        # Check for required files and number of files
        files = os.listdir(selected_dir)
        if "tmp_bw_trace.txt" not in files or "state.txt" not in files or len(files) != 122:
            print(f"Skipping {selected_dir}: does not meet criteria")
            continue

        selected_dirs.append(selected_dir)

    return selected_dirs

def copy_dirs(selected_dirs, target_dir):
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    for dir in selected_dirs:
        # Get the relative path of the directory
        relative_path = os.path.relpath(dir, start=parent_dir)
        target_path = os.path.join(target_dir, relative_path)
        shutil.copytree(dir, target_path)

parent_dir = "/scratch/09498/janechen/switch_output_avg_30"
target_dir = "/scratch/09498/janechen/switch_output_avg_30_sample"
num_dirs_to_select = 20

# Get all leaf directories
leaf_dirs = get_leaf_dirs(parent_dir)

# Select random leaf directories
selected_dirs = select_random_dirs(leaf_dirs, num_dirs_to_select)

# Copy selected directories to target location
copy_dirs(selected_dirs, target_dir)

print(f"Copied {num_dirs_to_select} directories to {target_dir}")
