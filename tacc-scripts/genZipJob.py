# Cubic-0.5-0.4  Cubic-0.5-0.8  Cubic-0.7-0.4  Cubic-0.7-0.8  Cubic-0.8-0.4  Cubic-0.8-0.8  Cubic-0.9-0.4  Cubic-0.9-0.8

for config in ["NewReno-1.0-1.0", "NewReno-1.0-3.0", "NewReno-1.0-4.0", "NewReno-1-2", "NewReno-1.5-1.0", "NewReno-1.5-2.0", "NewReno-1.5-3.0",  "NewReno-1.5-4.0", "NewReno-2.0-1.0", "NewReno-2.0-2.0", "NewReno-2.0-3.0",  "NewReno-2.0-4.0", "Cubic-0.5-0.4", "Cubic-0.5-0.8", "Cubic-0.7-0.4", "Cubic-0.7-0.8", "Cubic-0.8-0.4", "Cubic-0.8-0.8", "Cubic-0.9-0.4", "Cubic-0.9-0.8"]:
    policy = config.split("-")[0]
    for transport in ["car", "bus", "train", "ferry", "metro", "tram"]:
        print("zip -r "+config+"-"+transport+".zip /scratch/09498/janechen/"+policy+"/"+config+"/"+transport+"/ &")
    # print("python sortTraces.py " + config)