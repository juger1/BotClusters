#!/bin/bash

# Activate the virtual environment
source /app/venv/bin/activate

# Run Flask and other processes
flask run -h 0.0.0.0 -p 8000 &

python3 ping_server.py &

python3 worker.py

# Wait for all background processes to finish
wait
