from sqlalchemy import Column, Integer, ForeignKey
from db.database import Base

class PokemonMovimento(Base):
    __tablename__ = "pokemon_movimento"

    id = Column(Integer, primary_key=True, index=True)
    id_pokemon = Column(Integer, ForeignKey("pokemon.id"))
    id_movimento = Column(Integer, ForeignKey("movimento.id"))
