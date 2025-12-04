from sqlalchemy import Column, Integer, ForeignKey
from db.database import Base

class PokemonHabilidade(Base):
    __tablename__ = "pokemon_habilidade"

    id = Column(Integer, primary_key=True, index=True)
    id_pokemon = Column(Integer, ForeignKey("pokemon.id"))
    id_habilidade = Column(Integer, ForeignKey("habilidade.id"))
