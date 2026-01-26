# models.py
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.dialects.postgresql import JSONB


class Base(DeclarativeBase):
    pass


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)

    def __repr__(self):
        return f"<Tag(id={self.id}, name='{self.name}')>"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    password = Column(String(255), nullable=False)
    interests = Column(JSONB)  # {tag: score}

    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}')>"
