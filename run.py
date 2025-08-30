#!/usr/bin/env python3
"""
Entry point script to run the Amazon scraper from project root.
This script handles the correct working directory setup.
"""
import os
import sys
import asyncio

# Add src directory to Python path
src_dir = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_dir)

# Change to src directory for correct file path resolution
original_cwd = os.getcwd()
os.chdir(src_dir)

try:
    from main import run_pipeline
    
    if __name__ == "__main__":
        print("🚀 Starting Amazon Scraper Pipeline...")
        asyncio.run(run_pipeline())
finally:
    # Restore original working directory
    os.chdir(original_cwd)