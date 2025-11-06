from sqlalchemy import Column, Integer, String
from db.database import Base

class Pokemon(Base):
    __tablename__ = "pokemon"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True)
    tipos = Column(String)
    altura = Column(Integer)
    peso = Column(Integer)