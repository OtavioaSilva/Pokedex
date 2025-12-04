from sqlalchemy import Column, Integer, ForeignKey
from db.database import Base

class TipoForca(Base):
    __tablename__ = "tipo_forca"  # tabela intermediária N:N

    id = Column(Integer, primary_key=True, index=True)
    id_tipo = Column(Integer, ForeignKey("tipo.id"))  # tipo que tem força
    id_forte_contra = Column(Integer, ForeignKey("tipo.id"))  # tipo que recebe a vantagem
