# init_db.py
from database import init_db, engine
from models import Base

if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("Database initialized successfully!")

