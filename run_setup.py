#!/usr/bin/env python3
import os
import sys

# Add the project directory to the path
project_dir = r'r:\All Projek Saya\Sistem Clipper Otomatis'
sys.path.insert(0, project_dir)

# Execute the setup_dirs.py script
setup_script = os.path.join(project_dir, 'setup_dirs.py')
with open(setup_script, 'r') as f:
    exec(f.read())
