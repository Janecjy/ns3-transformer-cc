import os
import sys
import random

parent_dir = "/scratch/09498/janechen/"
policy_full_name_list = ["Cubic-0.5-0.4", "Cubic-0.5-0.8", "Cubic-0.7-0.4", "Cubic-0.7-0.8", "Cubic-0.8-0.4", "Cubic-0.8-0.8", "Cubic-0.9-0.4", "Cubic-0.9-0.8", "NewReno-1.0-1.0", "NewReno-1.0-3.0", "NewReno-1.0-4.0", "NewReno-1-2", "NewReno-1.5-1.0", "NewReno-1.5-2.0", "NewReno-1.5-3.0", "NewReno-1.5-4.0", "NewReno-2.0-1.0", "NewReno-2.0-2.0", "NewReno-2.0-3.0", "NewReno-2.0-4.0"]
bw_trace_dir = os.path.join(parent_dir, "ns3-traces")
output_parent_dir = os.path.join(parent_dir, "switch_output")
first_state_length = 50
second_state_time_length = 1 # in terms of seconds
root = sys.argv[1]
file = sys.argv[2]


def copy_state(output_dir, state_trace_path, second_start_line):
    state_out_path = os.path.join(output_dir, "state.txt")
    # print("state_out_path: ", state_out_path)
    tmp_cwnd = 0
    with open(state_out_path, "w") as out:
        with open(state_trace_path) as state_trace:
            start_write = False
            for i, line in enumerate(state_trace):
                if i == second_start_line - first_state_length:
                    start_write = True
                if start_write:
                    out.write(line)
                    tmp_cwnd = int(line.split(',')[1])
                if i == second_start_line:
                    second_start_time = float(line.split(',')[0])
                    # print("second_start_line: %d, second_start_time: %f", second_start_line, second_start_time)
                    return second_start_time, tmp_cwnd
    

def copy_bw_trace(output_dir, bw_trace_path, first_start_line, second_start_time):
    tmp_bw_trace_path = os.path.join(output_dir, "tmp_bw_trace.txt")
    # print("bw_trace_path: ", bw_trace_path)
    # print("tmp_bw_trace_path: ", tmp_bw_trace_path)
    tmp_buf = ""
    with open(tmp_bw_trace_path, "w") as f:
        with open(bw_trace_path) as bw_trace:
            for i, line in enumerate(bw_trace):
                t = float(line.split(' ')[0])/1000
                if t < second_start_time:
                    tmp_buf = line
                if t >= second_start_time:
                    if tmp_buf:
                        f.write(str(second_start_time*1000) + " " + tmp_buf.split(' ')[1])
                        tmp_buf = ""
                    f.write(line)
                if t > second_start_time + second_state_time_length:
                    return tmp_bw_trace_path

def run_job(output_dir, second_start_cwnd, run_policy, tmp_bw_trace_path, run_time_seed, om, ov, ofm, ofv):
    if run_policy.split('-')[0] == "Cubic":
        type = "TcpCubic"
        cubic_beta = run_policy.split('-')[1]
        cubic_c = run_policy.split('-')[2]
        cmd = '/home1/09498/janechen/ns3-transformer-cc/ns3 run "scratch/scratch-simulator --tcpTypeId='+type+' --beta='+cubic_beta+' --cubicC='+cubic_c+' --initialCwnd='+str(second_start_cwnd)+' --stopTime='+str(second_state_time_length)+' --traceFile='+tmp_bw_trace_path+' --outputDir='+output_dir+'/ --onTimeMean='+om+' --onTimeVar='+ov+' --offTimeMean='+ofm+' --offTimeVar='+ofv+' --runNum='+str(run_time_seed)+' --isSecondPolicy=true"'
    else:
        type = "TcpNewReno"
        reno_alpha = run_policy.split('-')[1]
        reno_beta = run_policy.split('-')[2]
        cmd = '/home1/09498/janechen/ns3-transformer-cc/ns3 run "scratch/scratch-simulator --tcpTypeId='+type+' --alpha='+reno_alpha+' --renoBeta='+reno_beta+' --initialCwnd='+str(second_start_cwnd)+' --stopTime='+str(second_state_time_length)+' --traceFile='+tmp_bw_trace_path+' --outputDir='+output_dir+'/ --onTimeMean='+om+' --onTimeVar='+ov+' --offTimeMean='+ofm+' --offTimeVar='+ofv+' --runNum='+str(run_time_seed)+' --isSecondPolicy=true"'
    # print(cmd)
    os.system(cmd)

def gen_data(parent_dir, file_name):
    policy = parent_dir.split("/")[-2]
    transport = parent_dir.split("/")[-1]
    line_num_index = 11
    om_index = 1
    if len(file_name.split('-')) > 17:
        line_num_index = 13
        om_index = 3
    first_start_line = file_name.split('-')[line_num_index] # get the bandwidth start line in the trace for the first policy
    # print("first_start_line: ", first_start_line)
    second_start_line = random.randint(first_state_length, 351) # create the line number in the state trace for the second policy to start from
    output_dir = os.path.join(output_parent_dir, policy, transport, file_name+"-"+str(second_start_line))
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    bw_trace_path = os.path.join(bw_trace_dir, "-".join(file_name.split('-')[line_num_index+1:]))
    state_trace_path = os.path.join(parent_dir, file_name)
    # print("state_trace_path: ", state_trace_path)
    second_start_time, first_end_cwnd = copy_state(output_dir, state_trace_path, second_start_line)
    tmp_bw_trace_path = copy_bw_trace(output_dir, bw_trace_path, first_start_line, second_start_time)
    run_time_seed = random.randint(0, 1000)
    om = file_name.split('-')[om_index]
    ov = file_name.split('-')[om_index+1]
    ofm = file_name.split('-')[om_index+2]
    ofv = file_name.split('-')[om_index+3]
    for run_policy in policy_full_name_list:
        for second_start_cwnd in range(max(1, first_end_cwnd-5), first_end_cwnd+5):
            run_job(output_dir, second_start_cwnd, run_policy, tmp_bw_trace_path, run_time_seed, om, ov, ofm, ofv)

def main():
    gen_data(root, file)
    
if __name__ == "__main__":
    main()