#!/usr/bin/env python3
"""
Simple SQLite to MySQL Migration Script

This script migrates data from SQLite to MySQL without Django dependencies.
Usage: python simple_migrate.py
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
        'host': get_env_var('DB_HOST', 'localhost'),  # Changed from 'db' to 'localhost'
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

def get_table_schema(sqlite_conn, table_name):
    """Get table schema from SQLite"""
    cursor = sqlite_conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    return cursor.fetchall()

def migrate_table(sqlite_conn, mysql_conn, table_name):
    """Migrate a single table from SQLite to MySQL"""
    print(f"Migrating table: {table_name}")
    
    try:
        # Get table schema
        schema = get_table_schema(sqlite_conn, table_name)
        if not schema:
            print(f"   No schema found for {table_name}")
            return
        
        # Get data from SQLite
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute(f"SELECT * FROM {table_name}")
        rows = sqlite_cursor.fetchall()
        
        if not rows:
            print(f"   No data in {table_name}")
            return
        
        # Create table in MySQL
        mysql_cursor = mysql_conn.cursor()
        
        # Build CREATE TABLE statement
        column_defs = []
        for col in schema:
            col_name = col[1]
            col_type = col[2].upper()
            
            # Map SQLite types to MySQL types
            if 'INT' in col_type:
                mysql_type = 'INT'
            elif 'TEXT' in col_type:
                mysql_type = 'TEXT'
            elif 'REAL' in col_type or 'FLOAT' in col_type:
                mysql_type = 'DOUBLE'
            elif 'CHAR' in col_type:
                mysql_type = f"VARCHAR({col[3]})"
            else:
                mysql_type = 'TEXT'
            
            not_null = 'NOT NULL' if col[3] == 1 else 'NULL'
            column_defs.append(f"`{col_name}` {mysql_type} {not_null}")
        
        # Add primary key if it's the first column
        if schema and schema[0][5] == 1:
            column_defs[0] += ' PRIMARY KEY AUTO_INCREMENT' if 'INT' in column_defs[0] else ' PRIMARY KEY'
        
        create_sql = f"""
        CREATE TABLE IF NOT EXISTS `{table_name}` (
            {', '.join(column_defs)}
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        mysql_cursor.execute(create_sql)
        
        # Insert data
        if rows:
            # Get column names
            columns = [desc[0] for desc in sqlite_cursor.description]
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
        raise

def create_mysql_database(mysql_conn):
    """Create MySQL database if it doesn't exist"""
    try:
        cursor = mysql_conn.cursor()
        db_name = get_env_var('DB_NAME', 'wagtail')
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        mysql_conn.commit()
        print(f"Database '{db_name}' created or already exists")
        return True
    except mysql.connector.Error as e:
        print(f"Error creating database: {e}")
        return False

def main():
    """Main migration function"""
    print("Starting SQLite to MySQL Migration")
    print("=" * 50)
    
    # Connect to databases
    sqlite_conn, mysql_conn = connect_databases()
    if not sqlite_conn or not mysql_conn:
        return
    
    try:
        # Create MySQL database
        if not create_mysql_database(mysql_conn):
            return
        
        # Switch to the created database
        db_name = get_env_var('DB_NAME', 'wagtail')
        mysql_conn.database = db_name
        mysql_conn.cursor().execute(f"USE `{db_name}`")
        
        # Get SQLite tables
        tables = get_table_names(sqlite_conn)
        print(f"Found {len(tables)} tables in SQLite")
        
        # Migrate each table
        for table_name in tables:
            migrate_table(sqlite_conn, mysql_conn, table_name)
        
        print("=" * 50)
        print("Migration completed!")
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
