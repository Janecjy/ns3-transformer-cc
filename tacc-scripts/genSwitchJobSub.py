import os
import sys
import random
import datetime

parent_dir = "/scratch/09498/janechen/"
# policy_full_name_list = ["Cubic-0.5-0.4", "Cubic-0.5-0.8", "Cubic-0.7-0.4", "Cubic-0.7-0.8", "Cubic-0.8-0.4", "Cubic-0.8-0.8", "Cubic-0.9-0.4", "Cubic-0.9-0.8", "NewReno-1.0-1.0", "NewReno-1.0-3.0", "NewReno-1.0-4.0", "NewReno-1-2", "NewReno-1.5-1.0", "NewReno-1.5-2.0", "NewReno-1.5-3.0", "NewReno-1.5-4.0", "NewReno-2.0-1.0", "NewReno-2.0-2.0", "NewReno-2.0-3.0", "NewReno-2.0-4.0"]
policy_full_name_list = ["TcpCubic-0.7-0.4", "TcpNewReno-1-2"]
on_off_config = [["1", "0.1", "0.2", "0.05"], ["1", "0.5", "0.2", "0.05"], ["5", "0.1", "0.1", "0.1"], ["2", "0.5", "0.2", "0.1"],  ["0.1", "0.05", "0.02", "0.01"]]
first_state_time_length = 3 # in terms of seconds
second_state_time_length = 1 # in terms of seconds
root = sys.argv[1]
file = sys.argv[2]
output_path_name = sys.argv[3]
output_parent_dir = os.path.join(parent_dir, output_path_name)
exp_per_file = int(output_path_name.split('_')[-1])
# run_num = 20 # get reward average of 20 runs

def run_job(run_time_seed, output_dir, start_cwnd_diff, first_policy, second_policy, file_name, om, ov, ofm, ofv):
    first_policy_type = first_policy.split('-')[0]
    first_policy_first_par = float(first_policy.split('-')[1])
    first_policy_second_par = float(first_policy.split('-')[2])
    second_policy_type = second_policy.split('-')[0]
    second_policy_first_par = float(second_policy.split('-')[1])
    second_policy_second_par = float(second_policy.split('-')[2])
    cmd = '/home1/09498/janechen/ns3-transformer-cc/ns3 run "scratch/scratch-simulator-switch --firstTcpTypeId='+first_policy_type+' --firstPolicyFirstParam='+first_policy_first_par+' --firstPolicySecondParam='+first_policy_second_par+' --secondTcpTypeId'+second_policy_type+' --secondPolicyFirstParam='+second_policy_first_par+' --secondPolicySecondParam='+second_policy_second_par+' --secondCwndDiff='+start_cwnd_diff+' --switchTime='+str(first_state_time_length)+' --stopTime='+str(first_state_time_length+second_state_time_length)+' --traceFile='+file_name+' --outputDir='+output_dir+'/ --onTimeMean='+om+' --onTimeVar='+ov+' --offTimeMean='+ofm+' --offTimeVar='+ofv+' --runNum='+str(run_time_seed)+'"'
    #+' --initialCwnd='+str(second_start_cwnd)+' --stopTime='+str(second_state_time_length)+' --traceFile='+tmp_bw_trace_path+' --outputDir='+output_dir+'/ --onTimeMean='+om+' --onTimeVar='+ov+' --offTimeMean='+ofm+' --offTimeVar='+ofv+' --runNum='+str(run_time_seed)+' --isSecondPolicy=true"'
    os.system(cmd)

def find_start_line_max(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()
        
    line_num = len(lines)
    return line_num - first_state_time_length - second_state_time_length

def gen_data(file_path):
    file_name = file_path.split('/')[-1]
    start_line_max = find_start_line_max(file_path)
    for exp in range(exp_per_file):
        start_line = random.randint(0, start_line_max)
        first_policy = random.choice(policy_full_name_list)
            
        output_dir = os.path.join(output_parent_dir, first_policy, file_name+"-"+str(start_line)+"-"+"{date:%Y-%m-%d_%H:%M:%S}".format( date=datetime.datetime.now()))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        else:
            print("output_dir "+output_dir+" already exists")
            return
        on_off = random.choice(on_off_config)
        om = on_off[0]
        ov = on_off[1]
        ofm = on_off[2]
        ofv = on_off[3]
        run_time_seed = random.randint(0, 100000)
        for second_policy in policy_full_name_list:
            for start_cwnd_diff in [0, -5, 5]: #range(max(1, first_end_cwnd-5), first_end_cwnd+5):
                # for _ in range(run_num):
                run_job(run_time_seed, output_dir, start_cwnd_diff, first_policy, second_policy, file_name, om, ov, ofm, ofv)

def main():
    gen_data(file)
    
if __name__ == "__main__":
    main()