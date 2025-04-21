#!/bin/bash

# Ensure virtual environment exists
if [ ! -d "./venv" ]; then
  echo "Error: Virtual environment 'venv' not found. Please create it first."
  exit 1
fi

# Activate virtual environment
source ./venv/bin/activate

# Ensure requirements.txt exists
if [ ! -f "requirements.txt" ]; then
  echo "Error: requirements.txt not found."
  exit 1
fi

# Install dependencies
if ! pip install -r requirements.txt; then
  echo "Error: Failed to install dependencies."
  exit 1
fi

# Run program and log output and errors
python program.py > log.txt 2>&1