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
        
on_mean = ["0.1", "0.5", "1", "2", "5", "7", "10"]
on_var = ["0.01", "0.05", "0.1", "0.2", "0.5", "0.8", "1"]
off_mean = ["0.02", "0.1", "0.2", "0.5", "0.8", "1", "1.5", "2"]
off_var = ["0.005", "0.01", "0.05", "0.1", "0.5", "1"]

for test in range(10):
    for om in on_mean:
        for ov in on_var:
            for ofm in off_mean:
                for ofv in off_var:
                    for trace in traces:
                        # get line number of the trace file
                        with open(trace) as f:
                            for i, l in enumerate(f):
                                pass
                            trace_line_num = i + 1
                        for i in range(0, int(trace_line_num/10)):
                            #get a random number between 0 and line_num - 10
                            start_line = random.randint(0, trace_line_num-10)
                            cmd = './ns3 run "scratch/scratch-simulator --tcpTypeId='+type+' --stopTime=10 --traceFile='+trace+' --outputDir='+output_dir+' --onTimeMean='+om+' --onTimeVar='+ov+' --offTimeMean='+ofm+' --offTimeVar='+ofv+' --startLine='+str(start_line)+'"'