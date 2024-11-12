import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import LabelEncoder
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import pandas as pd
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
    
    def get_tput(filename, total_time=4, interval=0.02):
        tput_arr = pd.read_table(filename, delimiter=',', header=None, engine='python')
        tput_arr = tput_arr.to_numpy(float)
        tput = np.zeros((int(total_time/interval), 2))
        tput_size = tput_arr.shape[0]
        tput[:,0] = interval * np.arange(tput.shape[0])
        curr_line, count_packets = 0, 0
        for i in range(tput.shape[0]):
            if curr_line == tput_size:
                break
            curr_time = tput[i, 0]
            if tput_arr[curr_line, 0] > curr_time + interval:
                continue
            else:
                count_packets = 0
                while tput_arr[curr_line, 0] <= curr_time + interval:
                    count_packets += 1
                    curr_line += 1
                    if curr_line == tput_size:
                        break
                tput[i, 1] = 1e-6 * count_packets * 1448 * 8 / interval
        return tput
    
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

# Step 2: Define the neural network
class SimpleNN(nn.Module):
    def __init__(self):
        super(SimpleNN, self).__init__()
        self.fc1 = nn.Linear(32 * 13, 128)
        self.fc2 = nn.Linear(128, 64)
        self.fc3 = nn.Linear(64, len(dataset.label_encoder.classes_))  # Number of classes
    def forward(self, x):
        x = x.view(x.size(0), -1)  # Flatten the input (1, 32, 13) to (32*13)
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        x = self.fc3(x)
        return x

# Step 3: Training the model
def train_model(train_loader, epochs=1000, learning_rate=0.001):
    model = SimpleNN()
    criterion = nn.CrossEntropyLoss(ignore_index=dataset.nan_token)
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    
    for epoch in range(epochs):
        for data, labels in train_loader:
            optimizer.zero_grad()
            outputs = model(data.float())
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
        print(f'Epoch {epoch+1}/{epochs}, Loss: {loss.item()}')
    
    return model

def test_model(model, test_loader):
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for data, labels in test_loader:
            outputs = model(data.float())
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
    
    print(f'Accuracy on test set: {(correct/total)*100:.2f}%')

# Normalizer tensor
normalizer = [
    1.0000000e+01, 3.2800000e+02, 4.2949673e+09, 1.0000000e+00, 3.1980000e+03,
    1.0994000e+04, 2.6100000e+02, 1.0000000e+00, 1.5000000e+01, 4.7494400e+05,
    5.9773450e+06, 5.9512810e+06, 1.7781441e+02
]

normalizer_10x = [
    1.0000000e+01, 2.8970000e+03, 4.2949673e+09, 1.0000000e+00, 1.9990000e+03,
    9.3880000e+03, 4.1400000e+02, 1.0000000e+00, 1.5500000e+02, 4.0804640e+06,
    6.1179448e+07, 6.0940528e+07, 8.6879997e+01
]

# Directories
trace_dir = sys.argv[1]
# trace_dir = "/scratch/09498/janechen/ns3-traces"
# trace_dir = "./"
# root_dirs = ["/scratch/09498/janechen/switch_output_avg_20", "/scratch/09498/janechen/switch_output_avg_5"] # ["/scratch/09498/janechen/switch_output", "/scratch/09498/janechen/switch_output_20", "/scratch/09498/janechen/switch_output_50", "/scratch/09498/janechen/switch_output_100", "/scratch/09498/janechen/switch_output_200"]
# root_dirs = ["./bus.ljansbakken-oslo-report.2010-09-28_1407CEST.log-132-2024-06-17_14:30:22"]
root_dir = sys.argv[2]
scale = sys.argv[3]

# Create dataset
dataset = CustomDataset(root_dir, normalizer)

# Save dataset
dataset.save('/scratch/09498/janechen/cc-decider-dataset-'+root_dir.split('/')[-1]+'.pth')

# Load dataset (if needed)
# dataset.load('dataset.pth')
# Train the model
train_loader = dataset.get_train_loader(batch_size=32)
test_loader = dataset.get_test_loader(batch_size=32)
model = train_model(train_loader)
test_model(model, test_loader)
# Save the trained model
torch.save(model.state_dict(), '/scratch/09498/janechen/cc-decider-model.pth')