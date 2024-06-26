import os
from concurrent.futures import ThreadPoolExecutor

def compare_files(file1, file2):
    with open(file1, 'r') as f1, open(file2, 'r') as f2:
        line_num = 0
        for line1, line2 in zip(f1, f2):
            line_num += 1
            if line1 != line2:
                return line_num
    return None

def process_leaf_directory(dirpath, tput_files, log_files):
    tput_line_num = None
    log_line_num = None

    for i in range(1, len(tput_files)):
        line_num = compare_files(tput_files[0], tput_files[i])
        if line_num is not None:
            tput_line_num = line_num
            break

    for i in range(1, len(log_files)):
        line_num = compare_files(log_files[0], log_files[i])
        if line_num is not None:
            log_line_num = line_num
            break

    return f"Directory: {dirpath}, Tput files diverge at line: {tput_line_num}, Log files diverge at line: {log_line_num}"

def process_directory(root_dir):
    leaf_dirs = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        tput_files = sorted([os.path.join(dirpath, f) for f in filenames if f.endswith('tput')])
        log_files = sorted([os.path.join(dirpath, f) for f in filenames if f.endswith('.log')])

        if len(tput_files) == 6 and len(log_files) == 6:
            leaf_dirs.append((dirpath, tput_files, log_files))

    results = []
    with ThreadPoolExecutor(max_workers=48) as executor:
        futures = [executor.submit(process_leaf_directory, dirpath, tput_files, log_files) for dirpath, tput_files, log_files in leaf_dirs]
        for future in futures:
            results.append(future.result())

    for result in results:
        print(result)

if __name__ == "__main__":
    root_directory = "/scratch/09498/janechen/switch_output_avg_5"
    process_directory(root_directory)
