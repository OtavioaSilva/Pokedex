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

def get_or_create_habilidade(db: Session, nome: str):
    habilidade = db.query(Habilidade).filter(Habilidade.nome == nome).first()
    if not habilidade:
        habilidade = Habilidade(nome=nome)
        db.add(habilidade)
        db.flush()
    return habilidade

def get_or_create_movimento(db: Session, nome: str):
    movimento = db.query(Movimento).filter(Movimento.nome == nome).first()
    if not movimento:
        movimento = Movimento(nome=nome)
        db.add(movimento)
        db.flush()
    return movimento



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
            "sprite": pokemon_db.sprite,
            "tipos": [t.nome for t in pokemon_db.tipos],
            "habilidades": [h.nome for h in pokemon_db.habilidades],
            "movimentos": [m.nome for m in pokemon_db.movimentos],
            "evolucoes": [e.nome for e in pokemon_db.evolucoes]
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
        peso=dados["weight"],
        sprite=dados["sprites"]["front_default"]
    )

    db.add(novo_pokemon)

    # associa os tipos usando a função get_or_create_tipo
    for t in dados["types"]:
        tipo_nome = t["type"]["name"]
        tipo_db = get_or_create_tipo(db, tipo_nome)
        novo_pokemon.tipos.append(tipo_db)
    #associando as habilidades
    for h in dados["abilities"]:
        habilidade_nome =h["ability"]["name"]
        habilidade_db = get_or_create_habilidade(db, habilidade_nome)
        novo_pokemon.habilidades.append(habilidade_db)
    
    for m in dados["moves"]:
        movimento_nome = m["move"]["name"]
        movimento_db = get_or_create_movimento(db, movimento_nome)
        novo_pokemon.movimentos.append(movimento_db)

    #associando as Evoluções
    evol_url = f"https://pokeapi.co/api/v2/pokemon-species/{nome}"
    evol_resposta = requests.get(evol_url)
    if evol_resposta.status_code == 200:
        evol_data = evol_resposta.json()
        chain_url = evol_data["evolution_chain"]["url"]
        chain_resposta = requests.get(chain_url)
        if chain_resposta.status_code == 200:
            chain = chain_resposta.json()["chain"]

            def parse_chain(chain_node):
                nome_chain = chain_node["species"]["name"].lower()
                if nome_chain != nome:
                    evo_db = db.query(Pokemon).filter(Pokemon.nome == nome_chain).first()
                    
                    if not evo_db:
                        evol_url = f"https://pokeapi.co/api/v2/pokemon/{nome_chain}"
                        evo_resposta = requests.get(evol_url)
                        if evo_resposta.status_code == 200:
                            evo_dados = evo_resposta.json()
                            evo_db = Pokemon(
                                id=evo_dados["id"],
                                nome=evo_dados["name"].lower(),
                                altura=evo_dados["height"],
                                peso=evo_dados["weight"],
                                sprite=evo_dados["sprites"]["front_default"]
                            )
                            db.add(evo_db)

                            # Associa tipos, habilidades e movimentos da evolução
                            for t in evo_dados["types"]:
                                tipo_db = get_or_create_tipo(db, t["type"]["name"])
                                evo_db.tipos.append(tipo_db)
                            for h in evo_dados["abilities"]:
                                hab_db = get_or_create_habilidade(db, h["ability"]["name"])
                                evo_db.habilidades.append(hab_db)
                            for m in evo_dados["moves"]:
                                mov_db = get_or_create_movimento(db, m["move"]["name"])
                                evo_db.movimentos.append(mov_db)
                        
                            db.flush()  # garante que evo_db tenha ID

                    if evo_db:
                        novo_pokemon.evolucoes.append(evo_db)
                for next_node in chain_node["evolves_to"]:
                    parse_chain(next_node)
            
            parse_chain(chain)

    # commit único após adicionar Pokémon e tipos
    db.commit()
    db.refresh(novo_pokemon)

    return {
        "id": novo_pokemon.id,
        "nome": novo_pokemon.nome,
        "altura": novo_pokemon.altura,
        "peso": novo_pokemon.peso,
        "sprite": novo_pokemon.sprite,
        "tipos": [tipo.nome for tipo in novo_pokemon.tipos],
        "habilidades": [h.nome for h in novo_pokemon.habilidades],
        "movimentos": [m.nome for m in novo_pokemon.movimentos],
        "evolucoes": [e.nome for e in novo_pokemon.evolucoes]
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
