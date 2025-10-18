from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sshtunnel import SSHTunnelForwarder

from config import get_settings


def test_connection(engine):
    try:
        print("in test connection")
        with engine.connect() as connection:
            print("in here")
            connection.execute(text("SELECT 1"))  # ✅ SQLAlchemy 1.4+ requires text()
            print("Connection successful!")
    except Exception as e:
        print("Database connection failed:", e)

app_settings = get_settings()

REMOTE_CONNECTION = app_settings.remote_db_tunnel


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
        port = app_settings.db_port

    db_user = app_settings.db_user
    db_password = app_settings.db_password
    db_host = app_settings.db_host
    db_name = app_settings.db_name

    SQLALCHEMY_DATABASE_URL = (
        f"mysql+mysqlconnector://{db_user}:{db_password}"
        f"@{db_host}:{port}/{db_name}"
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
