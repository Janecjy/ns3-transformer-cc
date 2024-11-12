#!/bin/bash

# Array of base directories
base_directories=("switch_output_1x_20" "switch_output_1x_100" "switch_output_10x_20" "switch_output_10x_100")

# Loop through each base directory
for BASE_DIR in "${base_directories[@]}"; do
    echo "Processing directory: $BASE_DIR"
    
    # Walk through each subdirectory
    find "$BASE_DIR" -type d | while read -r dir; do
        # Check if it's a leaf directory (contains no other directories)
        if [ "$(find "$dir" -mindepth 1 -type d | wc -l)" -eq 0 ]; then
            # Count the files in the leaf directory
            file_count=$(find "$dir" -type f | wc -l)

            # If the leaf directory doesn't contain exactly 12 files, delete it
            if [ "$file_count" -ne 12 ]; then
                # echo "Deleting $dir (contains $file_count files)"
                rm -rf "$dir"
            fi
        fi
    done

    # Count and print the number of remaining subdirectories under the base directory
    remaining_dirs=$(find "$BASE_DIR" -type d | wc -l)
    echo "After pruning, $BASE_DIR contains $remaining_dirs directories."
done
