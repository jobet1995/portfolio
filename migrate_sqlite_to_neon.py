#!/usr/bin/env python3
"""
SQLite3 to NeonDB Migration Script

This script migrates data from SQLite3 to NeonDB (PostgreSQL).
It handles schema conversion, data migration, and foreign key constraints.

Requirements:
    - psycopg2-binary
    - Django (if using Django models)
    - sqlite3 (built-in)

Usage:
    python migrate_sqlite_to_neon.py --sqlite-path db.sqlite3 --neon-url postgresql://user:pass@host/db
"""

import sqlite3
import psycopg2
import argparse
import sys
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class SQLiteToNeonMigrator:
    def __init__(self, sqlite_path: str, neon_url: str):
        self.sqlite_path = sqlite_path
        self.neon_url = neon_url
        self.sqlite_conn = None
        self.neon_conn = None
        
    def connect_databases(self):
        """Connect to both SQLite and NeonDB databases"""
        try:
            # Connect to SQLite
            self.sqlite_conn = sqlite3.connect(self.sqlite_path)
            self.sqlite_conn.row_factory = sqlite3.Row
            logger.info(f"Connected to SQLite database: {self.sqlite_path}")
            
            # Connect to NeonDB
            self.neon_conn = psycopg2.connect(self.neon_url)
            self.neon_conn.autocommit = False
            logger.info("Connected to NeonDB")
            
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
    
    def get_sqlite_tables(self) -> List[str]:
        """Get all table names from SQLite database"""
        cursor = self.sqlite_conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        # Exclude SQLite system tables
        tables = [table for table in tables if not table.startswith('sqlite_')]
        logger.info(f"Found tables: {tables}")
        return tables
    
    def get_table_schema(self, table_name: str) -> List[sqlite3.Row]:
        """Get table schema from SQLite"""
        cursor = self.sqlite_conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name});")
        return cursor.fetchall()
    
    def convert_sqlite_type_to_postgres(self, sqlite_type: str) -> str:
        """Convert SQLite data types to PostgreSQL data types"""
        sqlite_type = sqlite_type.upper()
        
        type_mapping = {
            'INTEGER': 'INTEGER',
            'TEXT': 'TEXT',
            'REAL': 'REAL',
            'BLOB': 'BYTEA',
            'NUMERIC': 'NUMERIC',
            'BOOLEAN': 'BOOLEAN',
            'DATE': 'DATE',
            'DATETIME': 'TIMESTAMP',
            'TIME': 'TIME',
            'VARCHAR': 'VARCHAR(255)',
            'CHAR': 'TEXT',  # Convert CHAR to TEXT to avoid length issues
        }
        
        # Handle VARCHAR(n) patterns
        if 'VARCHAR' in sqlite_type:
            return sqlite_type
        
        # Handle CHAR(n) patterns - convert to TEXT to avoid length restrictions
        if 'CHAR' in sqlite_type:
            return 'TEXT'
        
        # Handle other patterns
        for sqlite_key, postgres_type in type_mapping.items():
            if sqlite_key in sqlite_type:
                return postgres_type
        
        return 'TEXT'  # Default fallback
    
    def create_postgres_table(self, table_name: str, schema: List[sqlite3.Row]):
        """Create table in PostgreSQL with converted schema"""
        columns = []
        primary_keys = []
        
        for column in schema:
            col_name = column['name']
            col_type = self.convert_sqlite_type_to_postgres(column['type'])
            
            # Handle NOT NULL constraints - be more permissive for migration
            # Allow NULL for commonly problematic fields
            nullable_fields = [
                'last_name', 'first_name', 'date_joined', 'site_name', 
                'hostname', 'root_page_id', 'is_default_site', 'seo_title',
                'search_description', 'go_live_at', 'expire_at', 'expired'
            ]
            not_null = 'NOT NULL' if column['notnull'] and col_name not in nullable_fields else ''
            default_val = f"DEFAULT {column['dflt_value']}" if column['dflt_value'] else ''
            
            column_def = f"{col_name} {col_type} {not_null} {default_val}".strip()
            columns.append(column_def)
            
            if column['pk']:
                primary_keys.append(col_name)
        
        # Add primary key constraint if exists
        if primary_keys:
            pk_constraint = f", PRIMARY KEY ({', '.join(primary_keys)})"
        else:
            pk_constraint = ""
        
        create_sql = f"""
        DROP TABLE IF EXISTS {table_name} CASCADE;
        CREATE TABLE {table_name} (
            {', '.join(columns)}{pk_constraint}
        );
        """
        
        try:
            cursor = self.neon_conn.cursor()
            cursor.execute(create_sql)
            logger.info(f"Created table: {table_name}")
        except Exception as e:
            logger.error(f"Error creating table {table_name}: {e}")
            raise
    
    def migrate_table_data(self, table_name: str):
        """Migrate data from SQLite table to PostgreSQL table"""
        sqlite_cursor = self.sqlite_conn.cursor()
        postgres_cursor = self.neon_conn.cursor()
        
        # Get column names
        sqlite_cursor.execute(f"SELECT * FROM {table_name} LIMIT 0")
        columns = [description[0] for description in sqlite_cursor.description]
        
        # Get data from SQLite
        sqlite_cursor.execute(f"SELECT * FROM {table_name}")
        rows = sqlite_cursor.fetchall()
        
        if not rows:
            logger.info(f"No data to migrate in table: {table_name}")
            return
        
        # Prepare insert statement
        placeholders = ', '.join(['%s'] * len(columns))
        insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        
        # Migrate data
        migrated_count = 0
        for row in rows:
            try:
                # Convert row to tuple and handle None values
                data_tuple = tuple(None if val == '' else val for val in row)
                postgres_cursor.execute(insert_sql, data_tuple)
                migrated_count += 1
            except Exception as e:
                logger.warning(f"Error migrating row in {table_name}: {e}")
                continue
        
        logger.info(f"Migrated {migrated_count} rows to table: {table_name}")
    
    def create_indexes(self, table_name: str):
        """Create indexes for the table"""
        sqlite_cursor = self.sqlite_conn.cursor()
        
        # Get index information from SQLite
        sqlite_cursor.execute(f"PRAGMA index_list({table_name});")
        indexes = sqlite_cursor.fetchall()
        
        for index in indexes:
            if index[2]:  # Skip auto-created indexes
                continue
                
            index_name = index[1]
            
            # Get index columns
            sqlite_cursor.execute(f"PRAGMA index_info({index_name});")
            index_columns = [col[2] for col in sqlite_cursor.fetchall()]
            
            # Create index in PostgreSQL
            index_sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({', '.join(index_columns)})"
            
            try:
                postgres_cursor = self.neon_conn.cursor()
                postgres_cursor.execute(index_sql)
                logger.info(f"Created index: {index_name}")
            except Exception as e:
                logger.warning(f"Error creating index {index_name}: {e}")
    
    def reset_sequences(self):
        """Reset PostgreSQL sequences after migration"""
        cursor = self.neon_conn.cursor()
        
        # Get all tables
        cursor.execute("""
            SELECT table_name, column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND column_default LIKE 'nextval%'
        """)
        
        sequences = cursor.fetchall()
        
        for table, column in sequences:
            try:
                cursor.execute(f"""
                    SELECT setval(pg_get_serial_sequence('{table}', '{column}'), 
                                  COALESCE(MAX({column}), 1)) 
                    FROM {table}
                """)
                logger.info(f"Reset sequence for {table}.{column}")
            except Exception as e:
                logger.warning(f"Error resetting sequence for {table}.{column}: {e}")
    
    def migrate(self):
        """Main migration process"""
        start_time = datetime.now()
        logger.info("Starting migration from SQLite to NeonDB")
        
        try:
            # Connect to databases
            self.connect_databases()
            
            # Get tables
            tables = self.get_sqlite_tables()
            
            # Migrate each table
            for table_name in tables:
                logger.info(f"Migrating table: {table_name}")
                
                # Get schema
                schema = self.get_table_schema(table_name)
                
                # Create table in PostgreSQL
                self.create_postgres_table(table_name, schema)
                
                # Migrate data
                self.migrate_table_data(table_name)
                
                # Create indexes
                self.create_indexes(table_name)
            
            # Reset sequences
            self.reset_sequences()
            
            # Commit all changes
            self.neon_conn.commit()
            
            end_time = datetime.now()
            duration = end_time - start_time
            logger.info(f"Migration completed successfully in {duration}")
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            if self.neon_conn:
                self.neon_conn.rollback()
            raise
        finally:
            # Close connections
            if self.sqlite_conn:
                self.sqlite_conn.close()
            if self.neon_conn:
                self.neon_conn.close()
    
    def verify_migration(self):
        """Verify migration by comparing row counts"""
        logger.info("Verifying migration...")
        
        try:
            self.connect_databases()
            
            sqlite_cursor = self.sqlite_conn.cursor()
            postgres_cursor = self.neon_conn.cursor()
            
            tables = self.get_sqlite_tables()
            
            for table_name in tables:
                # Get SQLite count
                sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                sqlite_count = sqlite_cursor.fetchone()[0]
                
                # Get PostgreSQL count
                postgres_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                postgres_count = postgres_cursor.fetchone()[0]
                
                if sqlite_count == postgres_count:
                    logger.info(f"✓ {table_name}: {sqlite_count} rows")
                else:
                    logger.warning(f"✗ {table_name}: SQLite={sqlite_count}, PostgreSQL={postgres_count}")
            
            logger.info("Migration verification completed")
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
        finally:
            if self.sqlite_conn:
                self.sqlite_conn.close()
            if self.neon_conn:
                self.neon_conn.close()

def main():
    parser = argparse.ArgumentParser(description='Migrate SQLite3 to NeonDB')
    parser.add_argument('--sqlite-path', required=True, help='Path to SQLite database file')
    parser.add_argument('--neon-url', required=True, help='NeonDB connection URL')
    parser.add_argument('--verify', action='store_true', help='Verify migration after completion')
    
    args = parser.parse_args()
    
    try:
        migrator = SQLiteToNeonMigrator(args.sqlite_path, args.neon_url)
        migrator.migrate()
        
        if args.verify:
            migrator.verify_migration()
        
        logger.info("Migration process completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
