import os

# Create the directories
base_path = r'r:\All Projek Saya\Sistem Clipper Otomatis\backend\tests'
unit_dir = os.path.join(base_path, 'unit')
integration_dir = os.path.join(base_path, 'integration')

# Create directories with exist_ok=True
os.makedirs(unit_dir, exist_ok=True)
os.makedirs(integration_dir, exist_ok=True)

print(f'Created: {unit_dir}')
print(f'Created: {integration_dir}')

# Create __init__.py files
init_unit = os.path.join(unit_dir, '__init__.py')
init_integration = os.path.join(integration_dir, '__init__.py')

open(init_unit, 'w').close()
open(init_integration, 'w').close()

print(f'Created: {init_unit}')
print(f'Created: {init_integration}')

# Verify by listing the directories
print('\n--- Verification: Listing unit directory ---')
print(os.listdir(unit_dir))
print('\n--- Verification: Listing integration directory ---')
print(os.listdir(integration_dir))

# List the parent tests directory
print('\n--- Verification: Parent tests directory contents ---')
print(os.listdir(base_path))
