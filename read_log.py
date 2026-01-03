#!/usr/bin/env python3

def read_migration_log():
    """Read the migration log file"""
    try:
        with open('migration.log', 'r') as f:
            lines = f.readlines()
        
        # Show last 50 lines
        print("Last 50 lines of migration.log:")
        print("=" * 50)
        for line in lines[-50:]:
            print(line.rstrip())
            
    except FileNotFoundError:
        print("migration.log not found")
    except Exception as e:
        print(f"Error reading migration.log: {e}")

if __name__ == "__main__":
    read_migration_log()
