import os

# Create unit tests directory
unit_dir = r'r:\All Projek Saya\Sistem Clipper Otomatis\backend\tests\unit'
os.makedirs(unit_dir, exist_ok=True)
with open(os.path.join(unit_dir, '__init__.py'), 'w') as f:
    pass

# Create integration tests directory
integration_dir = r'r:\All Projek Saya\Sistem Clipper Otomatis\backend\tests\integration'
os.makedirs(integration_dir, exist_ok=True)
with open(os.path.join(integration_dir, '__init__.py'), 'w') as f:
    pass

print('✓ Created unit tests directory with __init__.py')
print('✓ Created integration tests directory with __init__.py')
