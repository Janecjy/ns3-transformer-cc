import os
import sys

root_dir = sys.argv[1]
results = {}
d_min = 20
tput_max_t = []
tput_max = []
delta = 0.1
line_limit = 16


# Read tput_max from the temp bw trace
with open(os.path.join(root_dir, "tmp_bw_trace.txt")) as bw_f:
    start_t = -1
    for line in bw_f:
        if start_t == -1:
            start_t = int(float(line.split(' ')[0]))/1000
        t = int(float(line.split(' ')[0]))/1000
        tput = int(line.split(' ')[1]) / 1e6
        tput_max_t.append(t-start_t)
        tput_max.append(tput)
            
for file in os.listdir(root_dir):
    # print(file)
    if file.endswith(".txt"):
        continue
    # TODO: take average from multiple random seeds
    
    tput_max_index = 0
    
    with open(os.path.join(root_dir, file)) as f:
        # print("open: ", file)
        total_reward = 0
        line_count = 0
        for line in f:
            if line.startswith("Time"):
                continue
            t = float(line.split(',')[0])
            tput = float(line.split(',')[3])
            delay = float(line.split(',')[5])
            drop = int(line.split(',')[7])
            
            if tput_max_index+1 < len(tput_max_t) and t >= tput_max_t[tput_max_index+1]:
                tput_max_index += 1
            
            reward = (tput - delta * drop)/delay/(tput_max[tput_max_index]/d_min)
            if reward > 0:
                total_reward += reward
                line_count += 1
                # print(t, tput, delay, drop, reward)
                if line_count >= line_limit:
                    break
            # print(reward)
        # print(file, total_reward)
        results[file] = total_reward

# print(results)
label = max(results, key=results.get)
print(label)