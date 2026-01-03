#!/usr/bin/env python3
import os
import psycopg2

def clean_neon_db():
    """Clean up existing tables in NeonDB"""
    
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
        print("DATABASE_URL not found in .env file")
        return
    
    try:
        conn = psycopg2.connect(neon_url)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        
        if not tables:
            print("No tables found in NeonDB")
            return
        
        print(f"Found {len(tables)} tables. Dropping them...")
        
        # Drop all tables
        for table in tables:
            table_name = table[0]
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
                print(f"Dropped table: {table_name}")
            except Exception as e:
                print(f"Error dropping table {table_name}: {e}")
        
        conn.commit()
        print("All tables dropped successfully!")
        
    except Exception as e:
        print(f"Error cleaning NeonDB: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    clean_neon_db()
