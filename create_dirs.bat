@echo off
cd /d "r:\All Projek Saya\Sistem Clipper Otomatis\backend\tests"
mkdir unit
mkdir integration
cd unit
type nul > __init__.py
cd ..\integration
type nul > __init__.py
echo Directories created successfully!
