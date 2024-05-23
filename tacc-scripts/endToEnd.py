import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from models import create_mask
import os
import random

#CONSTANTS
PAD_IDX = 2
BATCH_SIZE = 1024
NUM_EPOCHS = 250
CONTEXT_LENGTH = 32
PREDICTION_LENGTH = 32
TEST_LIMIT = 1
TEST_TIME_LIMIT = 10

on_off_config = [["1", "0.1", "0.2", "0.05"], ["1", "0.5", "0.2", "0.05"], ["1", "0.1", "0.5", "0.1"], ["2", "0.5", "0.2", "0.1"],  ["0.1", "0.05", "0.02", "0.01"], ["1", "0.5", "0.2", "0.05"]]

transformer_model_path = "/scratch/09498/janechen/mod_NewRenoCubicCombined-norm-0drop-1000iter.p"
device = torch.device("cuda:1" if torch.cuda.is_available() else "cpu")
transformer_model = torch.load(transformer_model_path, map_location=device)

trace_dir = "/scratch/09498/janechen/ns3-traces/"
output_dir = "/scratch/09498/janechen/end-to-end/"

def pick_random_trace(trace_dir):
    traces = os.listdir(trace_dir)
    trace_file = random.choice(traces)
    return os.path.join(trace_dir, trace_file)

def run_ns3_simulation(trace_path, output_dir, policy, first_par, second_par, om, ov, ofm, ofv, run_count):
    run_num = random.randint(0, 10000)
    if policy == "TcpCubic":
        ns3_command = '/home1/09498/janechen/ns3-transformer-cc/ns3 run "scratch/scratch-simulator --tcpTypeId='+policy+' --beta='+str(first_par)+' --cubicC='+str(second_par)+' --traceFile={trace_path} --outputDir={output_dir}/ --onTimeMean='+om+' --onTimeVar='+ov+' --offTimeMean='+ofm+' --offTimeVar='+ofv+' --runNum='+str(run_num)+' --isEndToEnd=true --runCount = '+run_count+'"'
    else:
        ns3_command = '/home1/09498/janechen/ns3-transformer-cc/ns3 run "scratch/scratch-simulator --tcpTypeId='+policy+' --alpha='+str(first_par)+' --renoBeta='+str(second_par)+' --traceFile={trace_path} --outputDir={output_dir}/ --onTimeMean='+om+' --onTimeVar='+ov+' --offTimeMean='+ofm+' --offTimeVar='+ofv+' --runNum='+str(run_num)+' --isEndToEnd=true --runCount = '+run_count+'"'
    os.system(ns3_command)

def read_output_file(output_file):
    # Read and transform output file into a (1, 32, 13) matrix
    with open(output_file, 'r') as file:
        lines = file.readlines()
    
    matrix = []
    for line in lines:
        values = line.strip().split(', ')
        matrix.append([float(value) for value in values])

    return matrix

def extract_last_timepoint(matrix):
    last_timepoint = matrix[-1][0]
    return last_timepoint

def create_temp_bandwidth_trace(trace_path, last_timepoint, run_count):
    temp_trace_path = os.path.join(output_dir, )
    with open(trace_path, 'r') as file:
        lines = file.readlines()
    
    temp_trace_lines = [line.strip().split(' ') for line in lines if float(line.split(' ')[0]) > last_timepoint]
    temp_trace_lines = [f"{float(line[0]) - last_timepoint} {line[1]}" for line in temp_trace_lines]
    temp_trace_lines.insert(0, f"0 {lines[0].split(' ')[1]}")
    
    with open(temp_trace_path, 'w') as file:
        file.write('\n'.join(temp_trace_lines))

    return temp_trace_path

def feed_into_transformer(matrix):
    # Feed matrix into transformer model and get output
    pass

def test_model(model, dataset, prediction_len, device):
    model = model.eval()
    loss_func = nn.MSELoss(reduction='sum')
    num_samples = dataset.shape[0]
    test_loss = np.zeros((num_samples, prediction_len))
    print(f'Total test samples = {test_loss.shape[0]}')
    for i in range(num_samples):
        sample = (dataset[i,:,:].reshape(1, dataset.shape[1], dataset.shape[2])).clone()
        enc_input = sample[:,:-prediction_len, :].to(device)
        dec_input = (1.5*torch.ones((1, prediction_len, sample.shape[2]))).to(device)
        expected_output = sample[:, -prediction_len:, :].to(device)
        src_mask, tgt_mask, _, _ = create_mask(enc_input, dec_input, pad_idx=PAD_IDX, device=device)
        model_out = model(enc_input, dec_input, src_mask, tgt_mask, None, None, None)
        test_loss[i,:] = [loss_func(model_out[:,j,:], expected_output[:,j,:]).item() for j in range(prediction_len)]
        # for j in range(prediction_len):
        #     test_loss[i, j] = loss_func(model_out[:, j, :], expected_output[:,j,:]).item()
        if i%(num_samples//10) == 0: print(f'Done testing {i} of {num_samples}')
    return test_loss

def feed_into_policy_decider(output):
    # Feed output into policy decider and get label
    pass

def translate_label(label):
    # Translate label into next period's policy and parameters
    pass


def main():
    
    current_time = 0 # in seconds

    for _ in range(TEST_LIMIT):
        trace_path = pick_random_trace(trace_dir)
        output_path = os.path.join(output_dir, )
        policy = "TcpCubic"
        first_par = 0.7
        second_par = 0.4
        
        on_off = random.choice(on_off_config)
        om = on_off[0]
        ov = on_off[1]
        ofm = on_off[2]
        ofv = on_off[3]
        
        run_count = 0
        last_timepoint = 0
        
        while current_time < TEST_TIME_LIMIT:
            
            temp_trace_path = create_temp_bandwidth_trace(trace_path, last_timepoint, run_count)
            run_ns3_simulation(temp_trace_path, output_dir, policy, first_par, second_par, om, ov, ofm, ofv, run_count)
            output_file = os.path.join(output_dir, "output.txt")
            matrix = read_output_file(output_file)
            last_timepoint = extract_last_timepoint(matrix)
            output = feed_into_transformer(matrix)
            # matrix + output
            label = feed_into_policy_decider(output)
            policy, parameters = translate_label(label)
            # Start another simulation using the new policy and parameters

if __name__ == "__main__":
    main()
