from pymilvus import connections, db
import os
from dotenv import load_dotenv

load_dotenv()

MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = int(os.getenv("MILVUS_PORT", 19530))

def init_milvus():
    """Khởi tạo kết nối Milvus"""
    connections.connect(
        alias="default",
        host=MILVUS_HOST,
        port=MILVUS_PORT
    )
    print("✅ Connected to Milvus")

def create_database(db_name: str):
    """Tạo database"""
    try:
        db.create_database(db_name)
        print(f"✅ Database '{db_name}' created")
    except Exception as e:
        print(f"Database already exists or error: {e}")

def get_milvus():
    """Get Milvus connection"""
    return connections.get_connection()
