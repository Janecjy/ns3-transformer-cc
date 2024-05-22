import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import LabelEncoder
from concurrent.futures import ThreadPoolExecutor, as_completed
import random

# Step 1: Define the custom dataset
class CustomDataset(Dataset):
    def __init__(self, root_dirs, normalizer, nan_token=-1):
        self.data = []
        self.labels = []
        self.rewards = []
        self.label_encoder = LabelEncoder()
        self.normalizer = torch.tensor(normalizer).view(1, 1, -1)  # Reshape to (1, 1, 13) for broadcasting
        label_list = []

        with ThreadPoolExecutor(max_workers=48) as executor:
            futures = []
            for root_dir in root_dirs:
                for subdir, _, files in os.walk(root_dir):
                    if "state.txt" in files and len(files) > 20 and "tmp_bw_trace.txt" in files:
                        state_file = os.path.join(subdir, "state.txt")
                        futures.append(executor.submit(self.process_file, state_file, subdir, nan_token))
            
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
    
    
    def process_file(self, state_file, root_dir, nan_token):
        with open(state_file, 'r') as f:
            lines = f.readlines()
            if len(lines) < 32:
                return None
            lines = lines[-32:]
            data_point = []
            for line in lines:
                data_point.append([float(x) for x in line.strip().split(',')])
                # get last_cwnd to calculate new_cwnd relative difference
                last_cwnd = line.split(',')[1]
        data_point = torch.tensor(data_point).view(1, 32, 13) / self.normalizer
        data_point[data_point != data_point] = nan_token  # Replace NaN values with nan_token
        label, rewards = self.get_label(root_dir)
        # print(len(self.data))
        return data_point, label, rewards
    
    def get_label(self, root_dir):
        # Custom label generation logic provided by the user
        results = {}
        d_min = 20
        tput_max_t = []
        tput_max = []
        delta = 0.1
        line_limit = 16

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
            if file.endswith(".txt"):
                continue
            if not file.startswith("TcpCubic-0.700000-0.400000") and not file.startswith("TcpNewReno-1.000000-2"):
                continue
            tput_max_index = 0
            with open(os.path.join(root_dir, file)) as f:
                total_reward = 0
                line_count = 0
                for line in f:
                    if line.startswith("Time"):
                        continue
                    t = float(line.split(',')[0])
                    tput = float(line.split(',')[3])
                    delay = float(line.split(',')[5])
                    drop = int(line.split(',')[7])
                    if tput_max_index + 1 < len(tput_max_t) and t >= tput_max_t[tput_max_index + 1]:
                        tput_max_index += 1
                    reward = (tput - delta * drop) / delay / (tput_max[tput_max_index] / d_min)
                    if reward > 0:
                        total_reward += reward
                        line_count += 1
                        if line_count >= line_limit:
                            break
                results[file] = total_reward
        label = max(results, key=results.get)
        return label, results
    
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
normalizer = [1.0000e+01, 5.4600e+02, 4.2950e+09, 4.0254e+02, 1.0000e+00, 4.7300e+03,
              1.4190e+04, 1.3200e+02, 1.0000e+00, 1.3800e+02, 7.9061e+05, 6.3031e+06,
              6.0121e+06]

# Directories
root_dirs = ["/scratch/09498/janechen/switch_output", "/scratch/09498/janechen/switch_output_20", "/scratch/09498/janechen/switch_output_50", "/scratch/09498/janechen/switch_output_100", "/scratch/09498/janechen/switch_output_200"]

# Create dataset
dataset = CustomDataset(root_dirs, normalizer)

# Save dataset
dataset.save('/scratch/09498/janechen/cc-decider-dataset.pth')

# Load dataset (if needed)
# dataset.load('dataset.pth')

# Train the model
# train_loader = dataset.get_train_loader(batch_size=32)
# test_loader = dataset.get_test_loader(batch_size=32)

# model = train_model(train_loader)
# test_model(model, test_loader)

# # Save the trained model
# torch.save(model.state_dict(), '/scratch/09498/janechen/cc-decider-model.pth')