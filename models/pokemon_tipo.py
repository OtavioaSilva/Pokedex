from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from db.database import Base

class PokemonTipo(Base):
    __tablename__ = "pokemon_tipo"

    id = Column(Integer, primary_key=True, index=True)
    id_pokemon = Column(Integer, ForeignKey("pokemon.id"))
    id_tipo = Column(Integer, ForeignKey("tipo.id"))

    pokemon = relationship("Pokemon", back_populates="pokemon_tipos")
    tipo = relationship("Tipo", back_populates="pokemon_tipos")