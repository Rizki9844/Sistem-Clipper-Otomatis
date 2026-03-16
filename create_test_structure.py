#!/usr/bin/env python3
import os

# Create the unit tests directory
unit_dir = r"r:\All Projek Saya\Sistem Clipper Otomatis\backend\tests\unit"
os.makedirs(unit_dir, exist_ok=True)
open(os.path.join(unit_dir, "__init__.py"), 'w').close()

# Create the integration tests directory
integration_dir = r"r:\All Projek Saya\Sistem Clipper Otomatis\backend\tests\integration"
os.makedirs(integration_dir, exist_ok=True)
open(os.path.join(integration_dir, "__init__.py"), 'w').close()

print("✓ Created directories:")
print(f"  - {unit_dir}")
print(f"  - {integration_dir}")
print("✓ Created __init__.py files in each directory")
