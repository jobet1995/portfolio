#!/usr/bin/env python3
import os

def check_env():
    """Check .env file contents"""
    if os.path.exists('.env'):
        print("Found .env file. Contents:")
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if 'DATABASE_URL' in line:
                        print(f"* {line}")
                    else:
                        print(f"  {line}")
    else:
        print("No .env file found")
    
    print(f"\nDATABASE_URL in environment: {'Found' if os.getenv('DATABASE_URL') else 'Not found'}")

if __name__ == "__main__":
    check_env()
