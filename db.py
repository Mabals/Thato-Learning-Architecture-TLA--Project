import os
import pyodbc
from dotenv import load_dotenv

# 1. Inject configurations from the hidden .env file at application runtime
load_dotenv()

SERVER = os.getenv("DB_SERVER", "localhost\SQLEXPRESS")
DATABASE = os.getenv("DB_DATABASE", "TLA_Enterprise_DB")

def get_db_connection():
    """
    Establishes and returns a live connection pool handle to the MS SQL Server instance.
    Uses trusted Windows Authentication for local security clearance.
    """
    try:
        # Constructing the Native ODBC Connection String
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={SERVER};"
            f"DATABASE={DATABASE};"
            f"Trusted_Connection=yes;" # Uses your active Windows user login clearance
        )
        
        connection = pyodbc.connect(conn_str)
        return connection
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: Unable to establish connection to SQL Server.\nDetails: {e}")
        return None

# Test routing script to instantly verify the connection pipeline works
if __name__ == "__main__":
    print("Testing database pipeline connection...")
    test_conn = get_db_connection()
    if test_conn:
        print("🚀 SUCCESS: Python successfully shook hands with TLA_Enterprise_DB inside SSMS!")
        test_conn.close()