./ns3 clean
./ns3 configure --build-profile=debug
./ns3 build

python genSwitchJob.py ns3-traces 100 1x
python genSwitchJob.py ns3-traces-10.0x 100 10x