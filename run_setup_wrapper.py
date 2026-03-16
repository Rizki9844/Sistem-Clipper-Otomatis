#!/usr/bin/env python3
import subprocess
import sys
import os

# Change to the project directory
os.chdir(r'r:\All Projek Saya\Sistem Clipper Otomatis')

# Run the setup_dirs.py script
result = subprocess.run([sys.executable, 'setup_dirs.py'], capture_output=True, text=True)

# Print the output
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)
print("Return code:", result.returncode)
