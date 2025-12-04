import asyncio
import httpx
import argparse
import sys
from httpx import HTTPStatusError
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, OperationalError
from typing import List, Dict, Any, Tuple
import time # Importado para delay no retry

sys.path.append(str(Path(__file__).resolve().parent.parent))

from db.database import SessionLocal, engine, Base
from models import Pokemon, Tipo, Habilidade, Movimento

POKEAPI_LIST_URL = "https://pokeapi.co/api/v2/pokemon?limit=5000"
POKEAPI_POKEMON_URL = "https://pokeapi.co/api/v2/pokemon/{}"
POKEAPI_SPECIES_URL = "https://pokeapi.co/api/v2/pokemon-species/{}"
DEFAULT_CONCURRENCY = 10
MAX_RETRIES = 15

def get_or_create_tipo(db: Session, nome: str):
    tipo = db.query(Tipo).filter(Tipo.nome == nome).first()
    if not tipo:
        tipo = Tipo(nome=nome)
        db.add(tipo)
        
    return tipo

def get_or_create_habilidade(db: Session, nome: str):
    hab = db.query(Habilidade).filter(Habilidade.nome == nome).first()
    if not hab:
        hab = Habilidade(nome=nome)
        db.add(hab)
        
    return hab

def get_or_create_movimento(db: Session, nome: str):
    mov = db.query(Movimento).filter(Movimento.nome == nome).first()
    if not mov:
        mov = Movimento(nome=nome)
        db.add(mov)
        
    return mov



async def get_pokemon_list() -> list[dict]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(POKEAPI_LIST_URL)
        resp.raise_for_status()
        return resp.json().get("results", [])

async def fetch_pokemon_detail(client: httpx.AsyncClient, identifier: int | str, retries: int = MAX_RETRIES) -> dict | None:
    url = POKEAPI_POKEMON_URL.format(identifier)
    for attempt in range(1, retries + 1):
        try:
            resp = await client.get(url)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
        except (httpx.RequestError, HTTPStatusError) as e:
            await asyncio.sleep(attempt)
    return None

async def fetch_evolution_chain(client: httpx.AsyncClient, species_id: int) -> List[str]:
    species_url = POKEAPI_SPECIES_URL.format(species_id)
    try:
        species_resp = await client.get(species_url)
        species_resp.raise_for_status()
        species_data = species_resp.json()
        
        chain_url = species_data.get("evolution_chain", {}).get("url")
        if not chain_url:
            return []
            
        chain_resp = await client.get(chain_url)
        chain_resp.raise_for_status()
        chain_data = chain_resp.json()["chain"]

        def extract_chain(chain_node, names=None):
            if names is None:
                names = []
            
            names.append(chain_node["species"]["name"].lower())

            for evolves_to in chain_node["evolves_to"]:
                extract_chain(evolves_to, names)
            
            return names

        all_names = extract_chain(chain_data)
        return list(set(all_names))
        
    except Exception as e:
        return []

def create_tables_if_needed():
    Base.metadata.create_all(bind=engine)



def insert_base_pokemon_sync(db: Session, dados: dict, max_retries: int = 15) -> Tuple[int, str, List[str]] | None:
    
    poke_id = dados.get("id")
    nome = dados["name"].lower()
    
    for attempt in range(1, max_retries + 1):
        try:
            # Checa se o Pokémon Base já foi inserido
            existing = db.query(Pokemon).filter(Pokemon.id == poke_id).first()
            if existing:
                return None
            
            # Cria o Pokémon Base
            novo_pokemon = Pokemon(
                id=poke_id,
                nome=nome,
                altura=dados.get("height"),
                peso=dados.get("weight"),
                sprite=dados.get("sprites", {}).get("front_default")
            )
            db.add(novo_pokemon)
            
            # 
            for t in dados.get("types", []):
                novo_pokemon.tipos.append(get_or_create_tipo(db, t["type"]["name"]))
            for h in dados.get("abilities", []):
                novo_pokemon.habilidades.append(get_or_create_habilidade(db, h["ability"]["name"]))
            for m in dados.get("moves", []):
                novo_pokemon.movimentos.append(get_or_create_movimento(db, m["move"]["name"]))

            
            db.commit() 
            
            types_list = [t.nome for t in novo_pokemon.tipos]
            print(f"[{poke_id}] Importado Base: {nome} -> Tipos: {', '.join(types_list)}")
            
            return (poke_id, nome, types_list)

        except IntegrityError as e:
            
            db.rollback() 
            if attempt < max_retries:
                
                time.sleep(0.01 * attempt) # Pequeno delay para evitar deadlock
                continue
            else:
                raise e # Lança o erro se as retries acabarem
        
        except Exception as e:
            db.rollback()
            raise e # Lança o erro se for qualquer outra exceção

    return None 

async def process_pokemon_base(client: httpx.AsyncClient, identifier: int | str, semaphore: asyncio.Semaphore) -> Tuple[str, int | None, List[str] | None]:
    #Processa a importação básica na Fase 1. A fase 1 é onde ele vai apenas importar no banco de dados, sem atribuir relações as evoluções
    async with semaphore:
        db = SessionLocal(expire_on_commit=False)
        try:
            dados = await fetch_pokemon_detail(client, identifier)
            if not dados:
                return ("skipped", None, None)
            
            try:
                
                result = await asyncio.to_thread(insert_base_pokemon_sync, db, dados)
                
                if not result:
                    return ("skipped", dados["id"], None) 
                
                return ("imported", result[0], [result[1]]) 
            
            except Exception as thread_e:
                
                if isinstance(thread_e, IntegrityError):
                    print(f"[ERRO FINAL] ID {identifier} falhou após {15} retries por Colisão de Integridade.")
                else:
                    print(f"[ERRO DB INSERÇÃO] ID {identifier}: {thread_e.__class__.__name__}: {thread_e}")
                
                return ("error", None, None)
            
        except Exception as e:
            
            return ("error", None, None)
        finally:
            db.close()

#Fase 2 criando as relações de evolução. Nessa fase ele vai atribuir as evoluções aos pokémons já importados na fase 1.

def resolve_evolution_relations_sync(db: Session, current_pokemon_id: int, chain_names: list[str]) -> int:
    #Cria as relações de evolução N:N no DB.
    if not chain_names:
        return 0

    pokemon_base = db.query(Pokemon).filter(Pokemon.id == current_pokemon_id).first()
    if not pokemon_base:
         return 0 

    relations_created = 0
    
    all_pokemons_in_chain = db.query(Pokemon.nome, Pokemon.id).filter(Pokemon.nome.in_(chain_names)).all()
    name_to_id_map = {name: id for name, id in all_pokemons_in_chain}

    for evo_name in chain_names:
        evo_id = name_to_id_map.get(evo_name)
        if evo_id and evo_id != current_pokemon_id:
            pokemon_evolucao = db.query(Pokemon).filter(Pokemon.id == evo_id).first()
            if pokemon_evolucao:
                if pokemon_evolucao not in pokemon_base.evolucoes:
                    pokemon_base.evolucoes.append(pokemon_evolucao)
                    relations_created += 1

    try:
        db.commit() 
    except Exception as e:
        db.rollback()
        raise e # Garante que o erro seja propagado
        
    return relations_created


async def process_pokemon_relations(client: httpx.AsyncClient, identifier: int | str, semaphore: asyncio.Semaphore) -> Tuple[str, int, int]:
    #Processa a criação de relações na Fase 2.
    async with semaphore:
        db = SessionLocal(expire_on_commit=False)
        try:
            existing = db.query(Pokemon).filter(Pokemon.id == identifier if isinstance(identifier, int) else Pokemon.nome == identifier).first()
            if not existing:
                return ("skipped", identifier, 0)

            chain_names = await fetch_evolution_chain(client, existing.id)
            
            try:
                evo_relations_created = await asyncio.to_thread(resolve_evolution_relations_sync, db, existing.id, chain_names)
                print(f"[{existing.id}] Relações: {existing.nome} -> {evo_relations_created} novas evoluções ligadas.")
                return ("processed", existing.id, evo_relations_created)
            except Exception as thread_e:
                 db.rollback()
                 print(f"[ERRO DB LIGAÇÃO] ID {identifier}: {thread_e.__class__.__name__}: {thread_e}")
                 return ("error", identifier, 0)
            
        except Exception as e:
            db.rollback()
            return ("error", identifier, 0)
        finally:
            db.close()


async def import_all_async(start: int = 1, end: int | None = None, concurrency: int = DEFAULT_CONCURRENCY):
    create_tables_if_needed()

    list_data = await get_pokemon_list()
    ids = [int(item["url"].rstrip("/").split("/")[-1]) for item in list_data]
    if end is None:
        end = max(ids)
    ids_to_process = [i for i in ids if start <= i <= end]

    print(f"--- FASE 1: Importando {len(ids_to_process)} Pokémons (Base) com {concurrency} requisições simultâneas ---")

    semaphore = asyncio.Semaphore(concurrency)
    
    #Executa a fase 1 (Importação Base)
    async with httpx.AsyncClient(timeout=30.0) as client:
        base_tasks = [process_pokemon_base(client, poke_id, semaphore) for poke_id in ids_to_process]
        base_results = await asyncio.gather(*base_tasks)

    # Coleta os IDs dos Pokémons importados para a Fase 2
    imported_ids = [result[1] for result in base_results if result[0] == "imported" and result[1] is not None]

    processed = len(base_results)
    imported = sum(1 for status, id, name in base_results if status == "imported")
    skipped = sum(1 for status, id, name in base_results if status == "skipped")
    errors = sum(1 for status, id, name in base_results if status == "error")

    print(f"\n--- FASE 1 Concluída. Importados: {imported} | Pulados: {skipped} | Erros: {errors} ---")
    
    if imported_ids:
        print(f"\n--- FASE 2: Criando Relações de Evolução para {len(imported_ids)} Pokémons ---")
        
        #Executa a fase 2 de Relações de Evolução
        async with httpx.AsyncClient(timeout=30.0) as client:
            relation_tasks = [process_pokemon_relations(client, poke_id, semaphore) for poke_id in imported_ids]
            relation_results = await asyncio.gather(*relation_tasks)

        relations_linked = sum(result[2] for result in relation_results if result[0] == "processed")
        
        errors_fase2 = sum(1 for result in relation_results if result[0] == "error")

        print(f"\n--- FASE 2 Concluída. Total de Novas Relações Ligadas: {relations_linked} ---")

    # Resumo Final
    print("\n-- Resumo Final do Processo --")
    print(f"Total de Pokémons Tentados: {processed}")
    print(f"Pokémons Base Importados com Sucesso: {imported}")
    print(f"Erros na Fase de Importação Base: {errors}")
    if imported_ids:
        print(f"Relações de Evolução Criadas: {relations_linked}")
        print(f"Erros na Fase de Ligação de Evoluções: {errors_fase2}")


def parse_args_and_run() -> None:
    parser = argparse.ArgumentParser(description="Importar pokemons da PokeAPI para banco local (async).")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=None)
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    args = parser.parse_args()
    asyncio.run(import_all_async(start=args.start, end=args.end, concurrency=args.concurrency))

if __name__ == "__main__":
    parse_args_and_run()