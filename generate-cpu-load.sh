#!/bin/bash
# Generate CPU load to demonstrate IPI correlation feature

echo "Generating CPU load for 90 seconds..."
echo "This will create multiple CPU-bound threads to generate IPIs"

# Function to generate CPU load
cpu_burn() {
    local duration=$1
    local end=$((SECONDS + duration))
    while [ $SECONDS -lt $end ]; do
        : # Busy loop
    done
}

# Start 8 background CPU burners
for i in {1..8}; do
    cpu_burn 90 &
done

echo "Started 8 CPU-bound threads (PIDs: $!)"
echo "Waiting for 90 seconds..."

# Wait for all background jobs
wait

echo "CPU load generation complete"

# Made with Bob
