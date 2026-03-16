import os

dirs = [
    r'r:\All Projek Saya\Sistem Clipper Otomatis\backend\tests\unit',
    r'r:\All Projek Saya\Sistem Clipper Otomatis\backend\tests\integration',
]

for d in dirs:
    os.makedirs(d, exist_ok=True)
    init_file = os.path.join(d, '__init__.py')
    open(init_file, 'w').close()
    print(f'Created: {init_file}')

# Verify
base = r'r:\All Projek Saya\Sistem Clipper Otomatis\backend\tests'
print('\nDirectory structure:')
for root, subdirs, files in os.walk(base):
    level = root.replace(base, '').count(os.sep)
    indent = '  ' * level
    print(f'{indent}{os.path.basename(root)}/')
    for f in files:
        print(f'{indent}  {f}')
