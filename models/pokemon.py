from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from db.database import Base

class Pokemon(Base):
    __tablename__ = "pokemon"

    id = Column(Integer, primary_key=True, index=True) #id pokeapi
    nome = Column(String, unique=True, index=True)
    altura = Column(Integer)
    peso = Column(Integer)

    #relação para tipos n:n
    pokemon_tipos = relationship("PokemonTipo", back_populates="pokemon")
    tipos = relationship("Tipo", secondary="pokemon_tipo", back_populates="pokemons")