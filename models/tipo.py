from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from db.database import Base

class Tipo(Base):
    __tablename__ = "tipo"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True)

    pokemons = relationship("Pokemon", secondary="pokemon_tipo", back_populates="tipos")

