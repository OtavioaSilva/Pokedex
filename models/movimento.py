from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from db.database import Base

class Movimento(Base):
    __tablename__ = "movimento"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True)

    # Relacionamento N:N com Pokémon
    pokemons = relationship("Pokemon", secondary="pokemon_movimento", back_populates="movimentos")
