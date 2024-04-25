# ./ns3 run "scratch/scratch-simulator --tcpTypeId=TcpNewReno --stopTime=10 --traceFile=/mydata/ns3-traces/tram.ljabru-jernbanetorget-report.2011-02-02_1345CET.log --outputDir=./ --startLine=10"

import os
import sys
import random

trace_dir = sys.argv[1]
output_dir = sys.argv[2]
type = sys.argv[3]

# for all traces in the directory, add to list
traces = []
for file in os.listdir(trace_dir):
    if file.endswith(".log"):
        traces.append(trace_dir+file)
        
on_off_config = [["1", "0.1", "0.2", "0.05"], ["1", "0.5", "0.2", "0.05"], ["1", "0.1", "0.5", "0.1"], ["2", "0.5", "0.2", "0.1"],  ["0.1", "0.05", "0.02", "0.01"], ["1", "0.5", "0.2", "0.05"]]

for config in on_off_config:
    om = config[0]
    ov = config[1]
    ofm = config[2]
    ofv = config[3]
    for trace in traces:
        # get line number of the trace file
        with open(trace) as f:
            for i, l in enumerate(f):
                pass
            trace_line_num = i + 1
        for i in range(0, int(trace_line_num/10)):
            #get a random number between 0 and line_num - 10
            start_line = random.randint(0, trace_line_num-10)
            cmd = '/home1/09498/janechen/ns3-transformer-cc/ns3 run "scratch/scratch-simulator --tcpTypeId='+type+' --stopTime=10 --traceFile='+trace+' --outputDir='+output_dir+' --onTimeMean='+om+' --onTimeVar='+ov+' --offTimeMean='+ofm+' --offTimeVar='+ofv+' --startLine='+str(start_line)+'"'
            print(cmd)