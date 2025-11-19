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
#Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/")
def root():
    return {"mensagem": "API Funcionando"}

@app.get("/pokemon/{nome}")
def pegar_pokemon(nome: str, db: Session = Depends(get_db)):
    pokemon_db = db.query(Pokemon).filter(Pokemon.nome == nome.lower()).first()
    
    if pokemon_db: #Busca a informação no banco
        
        return{
            "id": pokemon_db.id,
            "nome": pokemon_db.nome,
            "altura": pokemon_db.altura,
            "peso": pokemon_db.peso,
            "tipos": [t.nome for t in pokemon_db.tipos]
        }
    
    #se não tiver no banco, vai buscar na api agora
    url = f"https://pokeapi.co/api/v2/pokemon/{nome.lower()}"
    resposta = requests.get(url)

    if resposta.status_code != 200:
        return {"Erro: ": "Pokemon não encontrado."}
    
    dados = resposta.json()

    #criação do pokemon
    novo_pokemon = Pokemon (
        id = dados["id"],
        nome = dados["name"].lower(),
        altura = dados["height"],
        peso = dados["weight"]
    )

    db.add(novo_pokemon)
    db.commit()
    db.refresh(novo_pokemon)

    for t in dados["types"]:
        tipo_nome = t["type"]["name"]
        
        #verifica se o tipo ja existe
        tipo_db = db.query(Tipo).filter(Tipo.nome == tipo_nome).first()
        if not tipo_db:
            tipo_db = Tipo(nome=tipo_nome)
            db.add(tipo_db)
            db.commit()
            db.refresh(tipo_db)

        novo_pokemon.tipos.append(tipo_db)
    
    db.commit()

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
        resultado.append({"id": p.id,
                          "nome": p.nome,
                          "altura": p.altura,
                          "peso": p.peso,
                          "tipos": [t.nome for t in p.tipos]
                          })
    return resultado