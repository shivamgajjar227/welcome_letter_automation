from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sshtunnel import SSHTunnelForwarder
import settings
import time


def test_connection(engine):
    try:
        print("in test connection")
        with engine.connect() as connection:
            print("in here")
            connection.execute(text("SELECT 1"))  # ✅ SQLAlchemy 1.4+ requires text()
            print("Connection successful!")
    except Exception as e:
        print("Database connection failed:", e)

REMOTE_CONNECTION = 0
def db_connection():
    if REMOTE_CONNECTION:
        print("remote connection")

        server = SSHTunnelForwarder(
            ('160.250.204.165', 22),
            ssh_username="root",
            ssh_password="careloop1234",
            remote_bind_address=('127.0.0.1', 3306)
        )
        server.start()
        port = server.local_bind_port
    else:
        print("local connection")
        port = settings.port

    SQLALCHEMY_DATABASE_URL = (
        f"mysql+mysqlconnector://{settings.id}:{settings.password}"
        f"@127.0.0.1:{port}/{settings.db_name}"
    )

    print("db url:", SQLALCHEMY_DATABASE_URL)

    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_size=0,
        max_overflow=-1
        # future=True  # Uncomment this if you want SQLAlchemy 2.x behavior
    )

    test_connection(engine)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, SessionLocal


engine, SessionLocal = db_connection()
Base = declarative_base()