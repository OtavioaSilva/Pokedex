from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from db.database import Base
from models.tipo_forca import TipoForca
from models.tipo_fraqueza import TipoFraqueza

class Tipo(Base):
    __tablename__ = "tipo"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True)

    pokemons = relationship("Pokemon", secondary="pokemon_tipo", back_populates="tipos")
    forte_contra = relationship("Tipo", secondary="tipo_forca", primaryjoin="Tipo.id==TipoForca.id_tipo", secondaryjoin="Tipo.id==TipoForca.id_forte_contra", viewonly=True
)
    fraco_contra = relationship("Tipo", secondary="tipo_fraqueza", primaryjoin="Tipo.id==TipoFraqueza.id_tipo", secondaryjoin="Tipo.id==TipoFraqueza.id_fraco_contra", viewonly=True
    )

