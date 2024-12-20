import numpy as np
import matplotlib.pyplot as plt
import os
import torch
import pandas as pd
import pickle
import random
import sys
from concurrent.futures import ThreadPoolExecutor

# CONSTANTS
DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print(DEVICE)
PAD_IDX = 2
BATCH_SIZE = 1024
NUM_EPOCHS = 250
CONTEXT_LENGTH = 32
PREDICTION_LENGTH = 32

sample_length = int(sys.argv[1])
name_index = sys.argv[2]

def get_tput(filename, total_time=10, interval=0.02):
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

def process_file(file, input_dim=13):
    try:
        d = pd.read_table(file[:-5], delimiter=',', header=0, engine='python')
        d = d.replace(' -nan', -1.0)
        d = d.to_numpy(float)
        dd = get_tput(file)[:, 1]
        dd = dd[:, np.newaxis]
        d = np.hstack((d, dd))
        temp = [i if i != 0 else 1 for i in np.max(d, axis=0)]
        d = d.T
        d = d.reshape(1, input_dim, 500)
        return d, temp
    except:
        print(file)
        return None, None

def form_dataset_mod(filelist, context_len, prediction_len, input_dim=13, num_threads=80):
    seq_len = context_len + prediction_len
    train_dataset = np.zeros((1, input_dim, 500))
    print('Started Forming Raw Dataset')
    files_per_thread = len(filelist) // num_threads
    global_max = -10 * np.ones(input_dim)

    def process_chunk(thread_idx):
        # print(f'Chunk {thread_idx + 1} of {num_threads}')
        d1 = np.zeros((1, input_dim, 500))
        max_vals = -10 * np.ones(input_dim)
        for file in filelist[thread_idx * files_per_thread:(thread_idx + 1) * files_per_thread]:
            d, temp = process_file(file)
            if d is not None:
                max_vals = np.maximum(temp, max_vals)
                d1 = np.vstack((d1, d))
        return d1[1:, :, :], max_vals

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        results = list(executor.map(process_chunk, range(num_threads)))

    for d1, max_vals in results:
        train_dataset = np.vstack((train_dataset, d1))
        global_max = np.maximum(global_max, max_vals)

    global_max = global_max[:, np.newaxis]
    global_max = np.repeat(global_max, 500, axis=1)
    global_max = global_max[np.newaxis, :, :]
    global_max = np.repeat(global_max, train_dataset.shape[0], axis=0)
    train_dataset = np.divide(train_dataset, global_max)
    print('Finished gathering data. Reshaping...', flush=True)
    train_dataset = train_dataset[1:, :, :]

    mod_data = np.zeros((1, input_dim, seq_len))
    N, _, total_len = train_dataset.shape  # Get dimensions of train_dataset

    for sample_idx in range(N):  # Iterate through each sample in the dataset
        remaining_length = total_len  # Initialize remaining length of the data
        last_end = 0  # Initialize the last endpoint

        while remaining_length >= seq_len:  # Continue until there is enough data for another segment
            # Randomly select a start point after the last end point, within bounds
            start = np.random.randint(last_end, total_len - seq_len + 1)
            end = start + seq_len  # Determine the end point based on the sequence length

            # Extract the segment and add it to mod_data
            segment = train_dataset[sample_idx, :, start:end]
            segment = np.expand_dims(segment, axis=0)  # Expand dimensions to make it 3D

            # Append the segment
            mod_data = np.vstack((mod_data, segment))

            # Update the last end point and remaining length
            last_end = end
            remaining_length = total_len - last_end  # Update remaining length

    # Remove the initial placeholder row and convert to torch.FloatTensor
    mod_data = mod_data[1:, :, :]
    mod_data = torch.FloatTensor(mod_data)
    mod_data = torch.transpose(mod_data, 1, 2)  # Transpose to the required format

    global_max = torch.FloatTensor(global_max[0, :, 0])
    return mod_data, global_max

# Out-of-distribution
params_list_alt = [
    ('Reno', 1, 2, 'ferry'), ('Reno', 5, 3, 'metro'), ('Reno', 2, 2, 'bus'), ('Reno', 1.5, 2, 'train'),
    ('Cubic', 0.9, 0.4, 'bus'), ('Cubic', 0.7, 0.8, 'metro'), ('Cubic', 0.5, 0.4, 'car'), ('Cubic', 0.8, 0.8, 'tram'),
    ('Reno-10x', 1, 2, 'ferry'), ('Reno-10x', 5, 3, 'metro'), ('Reno-10x', 2, 2, 'bus'), ('Reno-10x', 1.5, 2, 'train'),
    ('Cubic-10x', 0.9, 0.4, 'bus'), ('Cubic-10x', 0.7, 0.8, 'metro'), ('Cubic-10x', 0.5, 0.4, 'car'), ('Cubic-10x', 0.8, 0.8, 'tram')
]

cubic_files = '/scratch/09498/janechen/Cubic'
reno_files = '/scratch/09498/janechen/NewReno'

filelist = []

for pol, inc, dec, transport in params_list_alt:
    if pol.startswith('Reno'): 
        path = reno_files
        if len(pol.split('-')) > 1:
            path += '-'
            path += pol.split('-')[1]
        path = os.path.join(path, 'NewReno-'+str(inc)+'-'+str(dec), transport)
        # print(path)
    else:
        path = cubic_files
        if len(pol.split('-')) > 1:
            path += '-'
            path += pol.split('-')[1]
        path = os.path.join(path, 'Cubic-'+str(inc)+'-'+str(dec), transport)
        # print(path)
    tput_list = [os.path.join(path, f) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f)) and f[-4:]=='tput']
    l = [i for i in tput_list if os.path.exists(i[:-5])]
    random.shuffle(l)
    # sample_length = 10000
    if len(l) < sample_length:
        sample_length = len(l)
    l = l[:sample_length]
    filelist += l

data, normalizer = form_dataset_mod(filelist, CONTEXT_LENGTH, PREDICTION_LENGTH)

dataset = dict()
dataset['data'] = data
dataset['normalizer'] = normalizer
import pickle
with open('/scratch/09498/janechen/NEWDatasets/FullDataset_alt'+name_index+'.p', 'wb') as f:
    pickle.dump(dataset, f, pickle.HIGHEST_PROTOCOL)

# dataset = dataset['data']
# shuffle_idx = torch.randperm(dataset.shape[0])
# dataset = dataset[shuffle_idx, :, :]
# train_samples = int(0.8*dataset.shape[0])

# with open('/scratch/09498/janechen/NEWDatasets/FullDataset_alt-test.p', 'wb') as f:
#     pickle.dump(dataset[train_samples:,:,:], f, pickle.HIGHEST_PROTOCOL)

# with open('/scratch/09498/janechen/NEWDatasets/FullDataset_alt-train.p', 'wb') as f:
#     pickle.dump(dataset[:train_samples, :,:], f, pickle.HIGHEST_PROTOCOL)
