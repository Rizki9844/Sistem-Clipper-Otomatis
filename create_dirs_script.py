#!/usr/bin/env python3
import os
import pathlib
import sys

# Define directories to create
directories = [
    r"r:\All Projek Saya\Sistem Clipper Otomatis\frontend\src\app\pricing",
    r"r:\All Projek Saya\Sistem Clipper Otomatis\frontend\src\app\billing"
]

print("Creating directories...")
for dir_path in directories:
    try:
        pathlib.Path(dir_path).mkdir(parents=True, exist_ok=True)
        if os.path.exists(dir_path):
            print(f"✓ Created/Exists: {dir_path}")
        else:
            print(f"✗ Failed to create: {dir_path}")
            sys.exit(1)
    except Exception as e:
        print(f"✗ Error creating {dir_path}: {e}")
        sys.exit(1)

print("\nAll directories created successfully!")
