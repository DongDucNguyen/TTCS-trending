import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import engine, Base
from app.models.schema import Category, Paper, Cluster
from sqlalchemy import text

def init_db():
    print("Initializing Database...")
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
    
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Database initialization complete.")

if __name__ == "__main__":
    init_db()
