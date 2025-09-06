from typing import List

from bs4 import BeautifulSoup, PageElement, NavigableString
from dataclasses import asdict

import asyncio
import aiohttp
import json

from demon import Demon

MEGATEN_URL = 'https://megamitensei.fandom.com'
MAX_CONCURRENT_REQUESTS = 100  # Máximo de requests simultáneas
BATCH_SIZE = 100               # Tamaño de cada lote

async def main():
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    results: List[Demon] = []

    routes = await get_routes()

    for i in range(0, len(routes), BATCH_SIZE):
        batch = routes[i:i + BATCH_SIZE]
        print(f"Procesando lote {i // BATCH_SIZE + 1}...")
        batch_results = await process_batch(batch, semaphore)
        results.extend(batch_results)

    demons : list[dict] = []
    for result in results:
        if result is None:
            continue
        demons.append(asdict(result))

    with open("../../result.json", "w", encoding="utf-8") as f:
        json.dump(demons, f, ensure_ascii=False, indent=2)

    print(f"Guardado {len(demons)} resultados en result.json")



async def get_routes() -> List[str]:
    text: str | None = None

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{MEGATEN_URL}/wiki/List_of_Demons_in_the_Franchise") as response:
            text = await response.text()

    if text is None:
        return []

    soup = BeautifulSoup(text, 'html.parser')
    container = soup.find('div', attrs={'class': 'mw-content-ltr mw-parser-output'})

    megaten_list = container.find_all('ul')

    routes: List[str] = []

    for megaten in megaten_list:
        for li in megaten.find_all('li'):
            classes = li.attrs.get('class', [])
            if 'toclevel-1' in classes:
                continue
            routes.append(f"{MEGATEN_URL}{li.find('a').attrs['href']}")

    return routes

async def fetch(session, url, semaphore)-> Demon | None:
    async with semaphore:
        try:
            async with session.get(url) as response:
                raw_html = await response.text()
                demon = get_demon(raw_html)
                if demon is None:
                    print(f'Invalid demon - url {url}')
                return demon
        except Exception as e:
            print(f"Error: {e}")
            return None

async def process_batch(batch, semaphore) -> List[Demon | None]:
    async with aiohttp.ClientSession() as session:
        tasks = [fetch(session, url, semaphore) for url in batch]
        return await asyncio.gather(*tasks)

def get_demon(raw_html) -> Demon | None:
    soup = BeautifulSoup(raw_html, 'html.parser')

    container = soup.find('aside', attrs={'role': 'region'})
    if container is None:
        return None

    name = get_element_text(container, 'h2', attrs={'data-source': "name"})

    pictures: List[str] = []
    picture_tags: list[PageElement | BeautifulSoup | NavigableString]  = []
    pictures_container = container.find(attrs={'data-source': "image"})
    if pictures_container:
        picture_tags = pictures_container.find_all('img')

    for picture_tag in picture_tags:
        pictures.append(picture_tag.get('src'))

    romaji = get_element_text(container, 'i', attrs={'data-source': "romaji"})

    origin = get_element_text(container, 'a', attrs={'data-source': "origin"})

    first_appearance = get_element_text(container, 'a', attrs={'data-source': "first appearance"})

    alignments = get_element_text(container, 'div', attrs={'data-source': "alignments"})

    races: List[str] = []
    race_tags: list[PageElement | BeautifulSoup | NavigableString] = []
    race_container = container.find(attrs={'data-source': "race"})
    if race_container:
        race_tags = race_container.find_all('a')

    for race_tag in race_tags:
        races.append(race_tag.text)

    allied_humans: List[str] = []
    allied_humans_tags:  list[PageElement | BeautifulSoup | NavigableString] = []
    allied_humans_container = container.find(attrs={'data-source': "alliedhuman"})
    if allied_humans_container:
        allied_humans_tags = allied_humans_container.find_all('a')

    for allied_human_tag in allied_humans_tags:
        allied_humans.append(allied_human_tag.text)

    return Demon(name=name,
                  romaji=romaji,
                  origin=origin,
                  races=races,
                  allied_humans=allied_humans,
                  first_appearance=first_appearance,
                  pictures=pictures,
                  alignments=alignments)

def get_element_text(container:  PageElement | BeautifulSoup | NavigableString | None, element_name: str = '', **attrs: dict[str, str]) -> str:
    if container is None:
        return ''

    element = container.find(element_name, **attrs)
    if element is None:
        return ''

    return element.text


if __name__ == "__main__":
    asyncio.run(main())
