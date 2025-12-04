from sqlalchemy import Column, Integer, ForeignKey
from db.database import Base

class TipoFraqueza(Base):
    __tablename__ = "tipo_fraqueza"  # tabela intermediária N:N

    id = Column(Integer, primary_key=True, index=True)
    id_tipo = Column(Integer, ForeignKey("tipo.id"))  # tipo que tem fraqueza
    id_fraco_contra = Column(Integer, ForeignKey("tipo.id"))  # tipo que causa a fraqueza
