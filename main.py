from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
import requests

# importando o banco e modelos
from db.database import get_db, Base, engine
from models import *

# cria todas as tabelas definidas nos modelos
Base.metadata.create_all(bind=engine)

app = FastAPI()


@app.get("/")
def root():
    return {"mensagem": "API Funcionando"}



def get_or_create_tipo(db: Session, nome: str):
    
    tipo = db.query(Tipo).filter(Tipo.nome == nome).first()
    if not tipo:
        tipo = Tipo(nome=nome)
        db.add(tipo)
        db.flush()  
    return tipo


@app.get("/pokemon/{nome}")
def pegar_pokemon(nome: str, db: Session = Depends(get_db)):
    nome = nome.lower()
    pokemon_db = db.query(Pokemon).filter(Pokemon.nome == nome).first()

    if pokemon_db:  # busca a informação no banco
        return {
            "id": pokemon_db.id,
            "nome": pokemon_db.nome,
            "altura": pokemon_db.altura,
            "peso": pokemon_db.peso,
            "tipos": [t.nome for t in pokemon_db.tipos]
        }

    # se não tiver no banco, vai buscar na API
    url = f"https://pokeapi.co/api/v2/pokemon/{nome}"
    resposta = requests.get(url)

    if resposta.status_code != 200:
        return {"erro": "Pokemon não encontrado."}, 404

    dados = resposta.json()

    # criação do Pokémon
    novo_pokemon = Pokemon(
        id=dados["id"],
        nome=dados["name"].lower(),
        altura=dados["height"],
        peso=dados["weight"]
    )

    db.add(novo_pokemon)

    # associa os tipos usando a função get_or_create_tipo
    for t in dados["types"]:
        tipo_nome = t["type"]["name"]
        tipo_db = get_or_create_tipo(db, tipo_nome)
        novo_pokemon.tipos.append(tipo_db)

    # commit único após adicionar Pokémon e tipos
    db.commit()
    db.refresh(novo_pokemon)

    return {
        "id": novo_pokemon.id,
        "nome": novo_pokemon.nome,
        "altura": novo_pokemon.altura,
        "peso": novo_pokemon.peso,
        "tipos": [tipo.nome for tipo in novo_pokemon.tipos]
    }


@app.get("/pokemons")
def listar_pokemons(db: Session = Depends(get_db)):
    pokemons = db.query(Pokemon).all()

    resultado = []
    for p in pokemons:
        resultado.append({
            "id": p.id,
            "nome": p.nome,
            "altura": p.altura,
            "peso": p.peso,
            "tipos": [t.nome for t in p.tipos]
        })
    return resultado
