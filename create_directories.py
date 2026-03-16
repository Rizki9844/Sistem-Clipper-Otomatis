import os

# List of directories to create
directories = [
    r"r:\All Projek Saya\Sistem Clipper Otomatis\frontend\src\app\admin",
    r"r:\All Projek Saya\Sistem Clipper Otomatis\frontend\src\app\admin\users",
    r"r:\All Projek Saya\Sistem Clipper Otomatis\frontend\src\app\admin\users\[id]",
    r"r:\All Projek Saya\Sistem Clipper Otomatis\frontend\src\app\admin\jobs",
]

# Create each directory
for directory in directories:
    try:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Created: {directory}")
    except Exception as e:
        print(f"✗ Error creating {directory}: {e}")

print("\nAll directories processed successfully!")
