#!/usr/bin/env python3
import psycopg2
import os

def test_neon_connection():
    # Load .env file
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
    
    neon_url = os.getenv('DATABASE_URL')
    if not neon_url:
        print("DATABASE_URL not found in .env")
        return
    
    try:
        conn = psycopg2.connect(neon_url)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"Connected to NeonDB successfully!")
        print(f"PostgreSQL version: {version[0]}")
        
        # Check if tables exist
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
        tables = cursor.fetchall()
        print(f"Found {len(tables)} tables in NeonDB:")
        for table in tables:
            print(f"  - {table[0]}")
        
        conn.close()
    except Exception as e:
        print(f"Error connecting to NeonDB: {e}")

if __name__ == "__main__":
    test_neon_connection()
