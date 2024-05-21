import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import LabelEncoder
from concurrent.futures import ThreadPoolExecutor, as_completed

# Step 1: Define the custom dataset
class CustomDataset(Dataset):
    def __init__(self, root_dirs, normalizer, nan_token=-1):
        self.data = []
        self.labels = []
        self.label_encoder = LabelEncoder()
        self.normalizer = torch.tensor(normalizer).view(1, 1, -1)  # Reshape to (1, 1, 13) for broadcasting
        label_list = []

        with ThreadPoolExecutor(max_workers=48) as executor:
            futures = []
            for root_dir in root_dirs:
                for subdir, _, files in os.walk(root_dir):
                    if "state.txt" in files:
                        state_file = os.path.join(subdir, "state.txt")
                        futures.append(executor.submit(self.process_file, state_file, subdir, nan_token))
            
            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    data_point, label = result
                    self.data.append(data_point)
                    label_list.append(label)

        self.labels = self.label_encoder.fit_transform(label_list)
        self.nan_token = nan_token
    
    def process_file(self, state_file, root_dir, nan_token):
        with open(state_file, 'r') as f:
            lines = f.readlines()
            if len(lines) < 32:
                return None
            lines = lines[-32:]
            data_point = []
            for line in lines:
                data_point.append([float(x) for x in line.strip().split(',')])
        data_point[data_point != data_point] = nan_token  # Replace NaN values with nan_token
        label = self.get_label(root_dir)
        return data_point, label
    
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
        return label
    
    def decode_labels(self, encoded_labels):
        return self.label_encoder.inverse_transform(encoded_labels)

    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        return self.data[idx], self.labels[idx]

    def save(self, path):
        torch.save((self.data, self.labels, self.label_encoder), path)

    def load(self, path):
        self.data, self.labels, self.label_encoder = torch.load(path)

# Step 2: Define the neural network without Conv1d layers
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
def train_model(dataset, epochs=10, batch_size=32, learning_rate=0.001):
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    model = SimpleNN()
    criterion = nn.CrossEntropyLoss(ignore_index=dataset.nan_token)
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    
    for epoch in range(epochs):
        for data, labels in dataloader:
            optimizer.zero_grad()
            outputs = model(data.float())
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
        print(f'Epoch {epoch+1}/{epochs}, Loss: {loss.item()}')
    
    return model

# Normalizer tensor
normalizer = [1.0000e+01, 5.4600e+02, 4.2950e+09, 4.0254e+02, 1.0000e+00, 4.7300e+03,
              1.4190e+04, 1.3200e+02, 1.0000e+00, 1.3800e+02, 7.9061e+05, 6.3031e+06,
              6.0121e+06]

# Directories
root_dirs = ["/scratch/09498/janechen/switch_output", "/scratch/09498/janechen/switch_output_20"]

# Create dataset
dataset = CustomDataset(root_dirs, normalizer)

# Save dataset
dataset.save('dataset.pth')

# Load dataset (if needed)
# dataset.load('dataset.pth')

# Train the model
model = train_model(dataset)

# Save the trained model
torch.save(model.state_dict(), 'model.pth')