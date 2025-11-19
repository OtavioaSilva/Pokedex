import time
import asyncio
import httpx
import argparse
import sys
#import requests
from httpx import HTTPStatusError
from requests.exceptions import RequestException
from pathlib import Path

# adiciona a raiz do projeto ao sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from db.database import SessionLocal, engine, Base
from models import Pokemon, Tipo



#Configuração
POKEAPI_LIST_URL = "https://pokeapi.co/api/v2/pokemon?limit=5000"
POKEAPI_POKEMON_URL = "https://pokeapi.co/api/v2/pokemon/{}"
DEFAULT_CONCURRENCY = 10 # numero máximo das requisições simultâneas do async
MAX_RETRIES = 3

async def get_pokemon_list() -> list[dict]:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(POKEAPI_LIST_URL)
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])

async def fetch_pokemon_detail(client: httpx.AsyncClient, identifier: int, retries: int = MAX_RETRIES) -> dict | None:
    url = POKEAPI_POKEMON_URL.format(identifier)
    for attempt in range(1, retries + 1):
        try:
            resp = await client.get(url)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
        except (httpx.RequestError, HTTPStatusError) as e:
            wait = attempt
            print(f"[Aviso] erro ao buscar {identifier}: {e}. retry {attempt}/{retries} (espera) {wait}s)...")
            await asyncio.sleep(wait)
    
    print(f" [ERRO] não foi possível buscar {identifier} depois de {retries} tentativas.")
    return None

def create_tables_if_needed():
     Base.metadata.create_all(bind=engine)

async def process_pokemon(client: httpx.AsyncClient, poke_id: int, db: SessionLocal, semaphore: asyncio.Semaphore):
    async with semaphore:
        existing = db.query(Pokemon).filter(Pokemon.id == poke_id).first()
        if existing:
            print(f"[{poke_id}] Pulado - Já existe ({existing.nome})")
            return "skipped"

        print (f"[{poke_id}] Buscando...")
        dados = await fetch_pokemon_detail(client, poke_id)
        if dados is None:
            print(f"[{poke_id}] Não encontrado (404) - Pulando")
            return "skipped"
        
        # Criar o novo pokemon
        novo_pokemon = Pokemon(
            id=dados["id"],
            nome=dados["name"].lower(),
            altura=dados.get("height"),
            peso=dados.get("weight"),
        )
        db.add(novo_pokemon)
        db.commit()
        db.refresh(novo_pokemon)

        # Associar os tipos aos pokemons
        tipos_nomes = [t["type"]["name"].lower() for t in dados.get("types", [])]
        for tipo_nome in tipos_nomes:
            tipo_db = db.query(Tipo).filter(Tipo.nome == tipo_nome).first()
            if not tipo_db:
                tipo_db = Tipo(nome=tipo_nome)
                db.add(tipo_db)
                db.commit()
                db.refresh(tipo_db)
            novo_pokemon.tipos.append(tipo_db)
        db.add(novo_pokemon)
        db.commit()
        db.refresh(novo_pokemon)
        print(f"[{poke_id}] Importado : {novo_pokemon.nome} -> tipos: {', '.join(tipos_nomes)or '-'}")
        return "imported"

async def import_all_async(start: int = 1, end: int | None = None, concurrency: int = DEFAULT_CONCURRENCY):
    create_tables_if_needed()
    db = SessionLocal()
    try:
        lista = await get_pokemon_list()
        ids = [int(item["url"].rstrip("/").split("/")[-1]) for item in lista]
        if end is None:
            end = max(ids)
        ids = [i for i in ids if start <= i <= end]
        
        print(f"Importando {len(ids)} pokemons (IDs {start} a {end}) com {concurrency} requisições simultâneas")

        semaphore = asyncio.Semaphore(concurrency)

        async with httpx.AsyncClient(timeout=10) as client:
            tasks = [process_pokemon(client, poke_id, db, semaphore) for poke_id in ids]
            results = await asyncio.gather(*tasks)
        

        # Resumo do processo
        processed = len(results)
        imported = results.count("imported")
        skipped = results.count("skipped")
        print("-- Resumo -- ")
        print(f"Processados: {processed} Importados: {imported} Pulados {skipped}")
    finally:
        db.close()


def parse_args_and_run() -> None:
    parser = argparse.ArgumentParser(description="Importar pokemons da PokeAPI para banco local (async).")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=None)
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)  # <- precisa estar aqui
    args = parser.parse_args()
    asyncio.run(import_all_async(start=args.start, end=args.end, concurrency=args.concurrency))

if __name__ == "__main__":
    parse_args_and_run()
