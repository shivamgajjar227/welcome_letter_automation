from sqlalchemy.orm import Session


def close_db(db: Session):
    db.close()