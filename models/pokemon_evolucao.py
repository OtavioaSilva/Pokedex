from sqlalchemy import Column, Integer, ForeignKey
from db.database import Base

class PokemonEvolucao(Base):
    __tablename__ = "pokemon_evolucao"  # tabela intermediária N:N

    id = Column(Integer, primary_key=True, index=True)
    id_pokemon = Column(Integer, ForeignKey("pokemon.id"))  # Pokémon base
    id_evolucao = Column(Integer, ForeignKey("pokemon.id"))  # Pokémon evoluído
