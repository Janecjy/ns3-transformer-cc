import os
import sys

def process_file(input_path, output_path, scaler_factor):
    with open(input_path, 'r') as infile, open(output_path, 'w') as outfile:
        for line in infile:
            timestamp, bandwidth = map(int, line.split())
            scaled_bandwidth = int(bandwidth * scaler_factor)
            outfile.write(f"{timestamp} {scaled_bandwidth}\n")

def main():
    if len(sys.argv) != 2:
        print("Usage: python scaleTrace.py <scaler_factor>")
        sys.exit(1)

    scaler_factor = float(sys.argv[1])
    input_dir = '/scratch/09498/janechen/ns3-traces'
    output_dir = f'/scratch/09498/janechen/ns3-traces-{scaler_factor}x'

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for filename in os.listdir(input_dir):
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename)
        process_file(input_path, output_path, scaler_factor)

if __name__ == "__main__":
    main()
