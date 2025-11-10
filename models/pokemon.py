from sqlalchemy import Column, Integer, String
from db.database import Base

class Pokemon(Base):
    __tablename__ = "pokemon"

    id = Column(Integer, primary_key=True, index=True) #id pokeapi
    nome = Column(String, unique=True, index=True)
    altura = Column(Integer)
    peso = Column(Integer)