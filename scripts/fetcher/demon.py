from dataclasses import dataclass

@dataclass
class Demon:
    name: str
    romaji: str
    origin: str
    first_appearance: str
    pictures: list[str]
    races: list[str]
    alignments: str
    allied_humans: list[str]
