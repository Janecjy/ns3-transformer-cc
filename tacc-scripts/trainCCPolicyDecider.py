import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import LabelEncoder
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import numpy as np
import sys


STATE_START_LINE = 124
STATE_LINE_LIMIT = 32
LABEL_LINE_LIMIT = 16

# Step 1: Define the custom dataset
class CustomDataset(Dataset):
    def __init__(self, root_dir, normalizer, nan_token=-1):
        self.data = []
        self.labels = []
        self.rewards = []
        self.label_encoder = LabelEncoder()
        self.normalizer = torch.tensor(normalizer).view(1, 1, -1)  # Reshape to (1, 1, 13) for broadcasting
        label_list = []

        with ThreadPoolExecutor(max_workers=48) as executor:
            futures = []
            for subdir, _, files in os.walk(root_dir):
                if len(files) == 12:
                    futures.append(executor.submit(self.process_file, subdir, nan_token))
                else:
                    print(f"Skipping {subdir} as it has {len(files)} files")
            
            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    data_point, label, rewards = result
                    self.data.append(data_point)
                    label_list.append(label)
                    self.rewards.append(rewards)

        self.labels = self.label_encoder.fit_transform(label_list)
        self.nan_token = nan_token
        self.train_indices, self.test_indices = self.split_data(len(self.data), train_ratio=0.7)
    
    def split_data(self, total_size, train_ratio=0.7):
        indices = list(range(total_size))
        random.shuffle(indices)
        train_size = int(total_size * train_ratio)
        train_indices = indices[:train_size]
        test_indices = indices[train_size:]
        return train_indices, test_indices

    def get_train_loader(self, batch_size):
        return DataLoader(self, batch_size=batch_size, sampler=torch.utils.data.SubsetRandomSampler(self.train_indices))
    
    def get_test_loader(self, batch_size):
        return DataLoader(self, batch_size=batch_size, sampler=torch.utils.data.SubsetRandomSampler(self.test_indices))
    
    def process_file(self, root_dir, nan_token):
        saved_state = None
        rewards = {}

        for f in os.listdir(root_dir):
            if not f.endswith("-tput") and f.endswith(".log"):
                tput_name = f + "-tput"
                tput = self.get_tput(os.path.join(root_dir, tput_name))
                reward_lines = []

                with open(os.path.join(root_dir, f), 'r') as file:
                    current_state = []

                    for current_line_number, line in enumerate(file, start=1):
                        if STATE_START_LINE <= current_line_number < STATE_START_LINE + STATE_LINE_LIMIT:
                            line_data = [float(x) for x in line.strip().split(',')]
                            del line_data[3]
                            # Add tput to the state
                            for t, tput_val in tput:
                                if t == line_data[0]:
                                    line_data.append(tput_val)
                            current_state.append(line_data)
                            last_cwnd = line.split(',')[1]

                        elif current_line_number >= STATE_START_LINE + STATE_LINE_LIMIT and current_line_number < STATE_START_LINE + STATE_LINE_LIMIT + LABEL_LINE_LIMIT:
                            if current_line_number == STATE_START_LINE + STATE_LINE_LIMIT:
                                new_cwnd = line.split(',')[1]
                                cwnd_diff = int(new_cwnd) - int(last_cwnd)
                            # Calculate reward
                            for t, tput_val in tput:
                                if t == float(line.split(',')[0]):
                                    line += ', ' + str(tput_val)
                            reward_lines.append(line)
                            
                        else:
                            continue

                    if saved_state is None:
                        saved_state = current_state
                    else:
                        if current_state != saved_state:
                            print(f"State mismatch found in file: {os.path.join(root_dir, f)}")
                            # Handle the discrepancy as needed
                            return None
                        else:
                            policy_name = f.split('-')[3] + '-' + f.split('-')[4] + '-' + f.split('-')[5] + '-' + str(cwnd_diff)
                            rewards[policy_name] = self.get_reward(f, reward_lines)
        
        state = torch.tensor(saved_state).view(1, 32, 13) / self.normalizer
        state[state != state] = nan_token  # Replace NaN values with nan_token

        label = self.get_label(rewards)
        return state, label, rewards
    
    def get_tput(self, file_path):
        # Read the data from the file
        timestamps = []
        bytes_received = []

        with open(file_path, 'r') as file:
            for line in file:
                timestamp, bytes = map(float, line.split(','))
                timestamps.append(timestamp)
                bytes_received.append(bytes)

        # Convert lists to numpy arrays for easier manipulation
        timestamps = np.array(timestamps)
        bytes_received = np.array(bytes_received)

        # Calculate the throughput every 20 milliseconds (0.02 seconds)
        interval_ms = 20
        max_time_ms = int(timestamps[-1] * 1000)
        throughputs = []

        for current_time_ms in range(0, max_time_ms + 1, interval_ms):
            current_time = current_time_ms / 1000.0
            next_time = (current_time_ms + interval_ms) / 1000.0
            # Find the indices of the timestamps within the current interval
            indices = np.where((timestamps >= current_time) & (timestamps < next_time))
            if len(indices[0]) > 0:
                # Sum the bytes received within the current interval
                bytes_sum = np.sum(bytes_received[indices])
                # Calculate the throughput in bytes/second and convert to Mbps
                throughput_mbps = (bytes_sum * 8) / (0.02 * 1_000_000)
            else:
                throughput_mbps = 0  # No data for this interval
            throughputs.append((current_time, throughput_mbps))

        return throughputs
    
    def get_reward(self, file_name, reward_lines):
        parts = file_name.split('-')
        extracted_part = '-'.join(parts[-5:])
        trace_file = os.path.join(trace_dir, extracted_part)
        start_line = int(parts[-6])
        with open(trace_file, 'r') as file:
            trace_lines = file.readlines()
        
            # Get the next LABEL_LINE_LIMIT lines starting from start_line
            end_line = start_line + LABEL_LINE_LIMIT
            selected_lines = trace_lines[start_line:end_line]
            start_t = -1
            tput_max_t = []
            tput_max = []
            for line in selected_lines:
                if start_t == -1:
                    start_t = int(float(line.split(' ')[0]))/1000
                t = int(float(line.split(' ')[0]))/1000
                tput = int(line.split(' ')[1]) / 1e6
                tput_max_t.append(t-start_t)
                tput_max.append(tput)

        total_reward = 0
        line_count = 0
        tput_max_index = 0
        d_min = 20
        delta = 0.1
        for line in reward_lines:
            t = float(line.split(',')[0])
            tput = float(line.split(',')[-1])
            delay = float(line.split(',')[5])
            drop = int(line.split(',')[7])
            if tput_max_index + 1 < len(tput_max_t) and t >= tput_max_t[tput_max_index + 1]:
                tput_max_index += 1
            reward = (tput - delta * drop) / delay / (tput_max[tput_max_index] / d_min)
            if reward > 0:
                total_reward += reward
                line_count += 1
                if line_count >= LABEL_LINE_LIMIT:
                    break
        return total_reward
    
    def get_label(self, rewards):
                
        label = max(rewards, key=rewards.get)
        return label
    
    def decode_labels(self, encoded_labels):
        return self.label_encoder.inverse_transform(encoded_labels)

    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        return self.data[idx], self.labels[idx]

    def save(self, path):
        torch.save((self.data, self.labels, self.label_encoder, self.rewards), path)

    def load(self, path):
        self.data, self.labels, self.label_encoder = torch.load(path)

# Normalizer tensor
normalizer = [1.0000e+01, 4.7000e+02, 4.2950e+09, 1.0000e+00, 6.7410e+03, 2.3282e+04,
        1.6700e+02, 1.0000e+00, 2.0000e+01, 6.7766e+05, 6.2278e+06, 6.1873e+06,
        2.7454e+02]

# Directories
trace_dir = "/scratch/09498/janechen/ns3-traces"
# trace_dir = "./"
# root_dirs = ["/scratch/09498/janechen/switch_output_avg_20", "/scratch/09498/janechen/switch_output_avg_5"] # ["/scratch/09498/janechen/switch_output", "/scratch/09498/janechen/switch_output_20", "/scratch/09498/janechen/switch_output_50", "/scratch/09498/janechen/switch_output_100", "/scratch/09498/janechen/switch_output_200"]
# root_dirs = ["./bus.ljansbakken-oslo-report.2010-09-28_1407CEST.log-132-2024-06-17_14:30:22"]
root_dir = sys.argv[1]

# Create dataset
dataset = CustomDataset(root_dir, normalizer)

# Save dataset
dataset.save('/scratch/09498/janechen/cc-decider-dataset-'+root_dir.split('/')[-1]+'.pth')