from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
import requests

#importando os banco e modelos
from db.database import get_db, Base, engine
from models import *
# from models.pokemon import Pokemon
# from models.tipo import Tipo
# from models.pokemon_tipo import PokemonTipo

#cria todas as tabelas definidas nos modelos
Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/")
def root():
    return {"mensagem": "API Funcionando"}

@app.get("/pokemon/{nome}")
def pegar_pokemon(nome: str, db: Session = Depends(get_db)):
    pokemon_db = db.query(Pokemon).filter(Pokemon.nome == nome.lower()).first()
    if pokemon_db:
        return{
            "id": pokemon_db.id,
            "nome": pokemon_db.nome,
            "altura": pokemon_db.altura,
            "peso": pokemon_db.peso,
            "tipos": pokemon_db.tipos.split(",")
        }
    
    url = f"https://pokeapi.co/api/v2/pokemon/{nome.lower()}"
    resposta = requests.get(url)

    if resposta.status_code != 200:
        return {"Erro: ": "Pokemon não encontrado."}
    
    dados = resposta.json()

    novo = Pokemon (
        id= dados["id"],
        nome= dados["name"],
        altura= dados["height"],
        peso= dados["weight"],
        tipos= [t["type"]["name"] for t in dados ["types"]]
    )
    db.add(novo)
    db.commit()

    return {
        "id": novo.id,
        "nome": novo.nome,
        "altura": novo.altura,
        "peso": novo.peso,
        "tipos": novo.tipos.split(",")
    }