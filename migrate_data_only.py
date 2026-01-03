#!/usr/bin/env python3
"""
SQLite to MySQL Data Migration Script

This script migrates only data from SQLite to MySQL, skipping table creation.
Usage: python migrate_data_only.py
"""

import sqlite3
import mysql.connector
import os
from pathlib import Path

# Load environment variables from .env file
def load_env_file():
    """Load environment variables from .env file"""
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

def get_env_var(key, default=''):
    """Get environment variable with default"""
    return os.environ.get(key, default)

def connect_databases():
    """Connect to both SQLite and MySQL databases"""
    # Load .env file
    load_env_file()
    
    # SQLite connection
    sqlite_path = Path(__file__).parent / 'db.sqlite3'
    sqlite_conn = sqlite3.connect(str(sqlite_path))
    sqlite_conn.row_factory = sqlite3.Row
    
    # MySQL connection
    mysql_config = {
        'host': get_env_var('DB_HOST', 'localhost'),
        'port': get_env_var('DB_PORT', '3306'),
        'user': get_env_var('DB_USER', 'root'),
        'password': get_env_var('DB_PASSWORD', ''),
        'database': get_env_var('DB_NAME', 'wagtail'),
        'charset': 'utf8mb4',
        'collation': 'utf8mb4_unicode_ci',
        'autocommit': True
    }
    
    print(f"MySQL config: {mysql_config['user']}@{mysql_config['host']}:{mysql_config['port']}/{mysql_config['database']}")
    
    try:
        mysql_conn = mysql.connector.connect(**mysql_config)
        mysql_conn.cursor().execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci")
        return sqlite_conn, mysql_conn
    except mysql.connector.Error as e:
        print(f"MySQL connection failed: {e}")
        print("Make sure MySQL container is running and .env is configured correctly")
        return None, None

def get_table_names(sqlite_conn):
    """Get all table names from SQLite"""
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    return [row[0] for row in cursor.fetchall()]

def migrate_table_data(sqlite_conn, mysql_conn, table_name):
    """Migrate only data from SQLite to MySQL table"""
    print(f"Migrating data for table: {table_name}")
    
    try:
        # Get data from SQLite
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute(f"SELECT * FROM {table_name}")
        rows = sqlite_cursor.fetchall()
        
        if not rows:
            print(f"   No data in {table_name}")
            return
        
        # Get column names
        columns = [desc[0] for desc in sqlite_cursor.description]
        
        # Insert data into MySQL
        mysql_cursor = mysql_conn.cursor()
        placeholders = ', '.join(['%s'] * len(columns))
        insert_sql = f"INSERT INTO `{table_name}` VALUES ({placeholders})"
        
        # Convert rows to tuples and handle None values
        mysql_rows = []
        for row in rows:
            mysql_row = tuple(
                None if (isinstance(val, str) and val == '') or val is None else val
                for val in row
            )
            mysql_rows.append(mysql_row)
        
        mysql_cursor.executemany(insert_sql, mysql_rows)
        print(f"   Migrated {len(rows)} rows")
        
    except Exception as e:
        print(f"   Error migrating {table_name}: {e}")

def main():
    """Main migration function"""
    print("Starting SQLite to MySQL Data Migration")
    print("=" * 50)
    
    # Connect to databases
    sqlite_conn, mysql_conn = connect_databases()
    if not sqlite_conn or not mysql_conn:
        return
    
    try:
        # Switch to the database
        db_name = get_env_var('DB_NAME', 'wagtail')
        mysql_conn.database = db_name
        mysql_conn.cursor().execute(f"USE `{db_name}`")
        
        # Get SQLite tables
        tables = get_table_names(sqlite_conn)
        print(f"Found {len(tables)} tables in SQLite")
        
        # Migrate data for each table
        for table_name in tables:
            migrate_table_data(sqlite_conn, mysql_conn, table_name)
        
        print("=" * 50)
        print("Data migration completed!")
        print("\nNext steps:")
        print("1. Update DATABASE_URL in .env to use MySQL")
        print("2. Test the application")
        print("3. Backup the SQLite file for safety")
        
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        if sqlite_conn:
            sqlite_conn.close()
        if mysql_conn:
            mysql_conn.close()

if __name__ == '__main__':
    main()
