from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class DPSQLAlchemyBase(Base):
    """
    Base SQLAlchemy for adding functionalities on the top of defined SQLAlchemy
    model classes
    """

    # setting abstract to True will ensure SQLAlchemy.Base class treat this class as metaclass
    # rather any model for table
    __abstract__ = True

    def __repr__(self):
        """repr method for object representation"""
        _dict = {attrs: getattr(self, attrs) for attrs in dir(self) if not attrs.startswith('_')}
        _str = f'{self.__class__.__name__}: {_dict}'
        return _str