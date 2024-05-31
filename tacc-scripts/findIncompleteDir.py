import os

def get_leaf_dirs(root_dir):
    leaf_dirs = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if not dirnames:  # This means it's a leaf directory
            leaf_dirs.append(dirpath)
    return leaf_dirs

def find_incomplete_dirs(leaf_dirs):
    incomplete_dirs = []
    for dir in leaf_dirs:
        files = os.listdir(dir)
        if "tmp_bw_trace.txt" not in files or "state.txt" not in files or len(files) != 122:
            incomplete_dirs.append(dir)
    return incomplete_dirs

def write_to_file(dirs, filename):
    with open(filename, 'w') as f:
        for dir in dirs:
            f.write(dir + '\n')

parent_dir = "/scratch/09498/janechen/switch_output_avg_30"
output_file = "/scratch/09498/janechen/incomplete_dirs.txt"

# Get all leaf directories
leaf_dirs = get_leaf_dirs(parent_dir)

# Find incomplete directories
incomplete_dirs = find_incomplete_dirs(leaf_dirs)

# Write incomplete directories to file
write_to_file(incomplete_dirs, output_file)

print(f"Found {len(incomplete_dirs)} incomplete directories. Paths written to {output_file}")
