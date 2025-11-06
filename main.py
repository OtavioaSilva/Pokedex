from fastapi import FastAPI
import requests

app = FastAPI()

@app.get("/")
def root():
    return {"mensagem": "API Funcionando"}

@app.get("/pokemon/{nome}")
def pegar_pokemon(nome: str):
    url = f"https://pokeapi.co/api/v2/pokemon/{nome.lower()}"
    resposta = requests.get(url)

    if resposta.status_code != 200:
        return {"Erro: ": "Pokemon não encontrado."}
    
    dados = resposta.json()

    pokemon = {
        "id": dados["id"],
        "nome": dados["name"],
        "altura": dados["height"],
        "peso": dados["weight"],
        "tipos": [t["type"]["name"] for t in dados ["types"]]
    }

    return pokemon