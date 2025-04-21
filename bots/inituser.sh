#!/bin/bash

# Check if a folder name was provided
if [ -z "$1" ]; then
  echo "Usage: $0 <folder_name>"
  exit 1
fi

folder="$1"

# Create the folder if it doesn't exist
if ! [ -d "$folder" ]; then
  mkdir "$folder"

  # Move base files
  cp ./bots/requirements.txt "$folder"
  cp ./bots/startup.sh "$folder"
  cp ./bots/program.py "$folder"

  cd "$folder"

  python3 -m venv venv
else
  cd "$folder"
fi

#Create a user
if id "$2" &>/dev/null; then
  echo "User '$2' already exists."
else
  echo "Creating user '$2'..."
  useradd -d "$1" "$2"
fi

chown -R "$2":"$2" .
chmod -R o-rwx .