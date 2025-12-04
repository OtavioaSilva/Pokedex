from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from db.database import Base


class Pokemon(Base):
    __tablename__ = "pokemon"

    id = Column(Integer, primary_key=True, index=True) #id pokeapi
    nome = Column(String, unique=True, index=True)
    altura = Column(Integer)
    peso = Column(Integer)
    sprite = Column(String)

    tipos = relationship("Tipo", secondary="pokemon_tipo", back_populates="pokemons")
    habilidades = relationship("Habilidade", secondary="pokemon_habilidade", back_populates="pokemons")
    movimentos = relationship("Movimento", secondary="pokemon_movimento", back_populates="pokemons")
    evolucoes = relationship("Pokemon", secondary="pokemon_evolucao", primaryjoin="Pokemon.id==PokemonEvolucao.id_pokemon", secondaryjoin="Pokemon.id==PokemonEvolucao.id_evolucao")