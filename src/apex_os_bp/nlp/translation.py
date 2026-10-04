"""Language translation using a dictionary-based approach.

This module provides a lightweight translation system that works offline
using built-in dictionaries for common language pairs. For production use,
this can be extended to use external translation APIs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class LanguageCode(str, Enum):
    """Supported language codes (ISO 639-1)."""

    EN = "en"  # English
    ES = "es"  # Spanish
    FR = "fr"  # French
    DE = "de"  # German
    IT = "it"  # Italian
    PT = "pt"  # Portuguese
    NL = "nl"  # Dutch
    RU = "ru"  # Russian
    ZH = "zh"  # Chinese
    JA = "ja"  # Japanese
    KO = "ko"  # Korean
    AR = "ar"  # Arabic
    HI = "hi"  # Hindi
    TR = "tr"  # Turkish
    PL = "pl"  # Polish
    SV = "sv"  # Swedish
    DA = "da"  # Danish
    NO = "no"  # Norwegian
    FI = "fi"  # Finnish
    EL = "el"  # Greek
    CS = "cs"  # Czech
    HU = "hu"  # Hungarian
    RO = "ro"  # Romanian
    TH = "th"  # Thai
    VI = "vi"  # Vietnamese
    ID = "id"  # Indonesian
    UK = "uk"  # Ukrainian
    HE = "he"  # Hebrew


# Translation dictionaries: (source_lang, target_lang) -> {source: target}
# This is a simplified dictionary for demonstration. In production,
# you would use a comprehensive dictionary or external API.
_DICTIONARIES: Dict[Tuple[str, str], Dict[str, str]] = {
    # English -> Spanish
    ("en", "es"): {
        "hello": "hola", "world": "mundo", "good": "bueno", "morning": "mañana",
        "night": "noche", "day": "día", "time": "tiempo", "year": "año",
        "person": "gente", "way": "camino", "thing": "cosa", "man": "hombre",
        "woman": "mujer", "child": "niño", "life": "vida", "hand": "mano",
        "part": "parte", "place": "lugar", "case": "caso", "week": "semana",
        "company": "empresa", "system": "sistema", "program": "programa",
        "question": "pregunta", "work": "trabajo", "government": "gobierno",
        "number": "número", "night": "noche", "point": "punto", "home": "casa",
        "water": "agua", "room": "habitación", "mother": "madre", "area": "área",
        "money": "dinero", "story": "historia", "fact": "hecho", "month": "mes",
        "lot": "loto", "right": "derecho", "study": "estudio", "book": "libro",
        "eye": "ojo", "job": "trabajo", "word": "palabra", "business": "negocio",
        "issue": "problema", "side": "lado", "kind": "tipo", "head": "cabeza",
        "house": "casa", "service": "servicio", "friend": "amigo", "father": "padre",
        "power": "poder", "hour": "hora", "game": "juego", "line": "línea",
        "end": "fin", "member": "miembro", "law": "ley", "car": "coche",
        "city": "ciudad", "community": "comunidad", "name": "nombre",
        "team": "equipo", "minute": "minuto", "idea": "idea", "kid": "niño",
        "body": "cuerpo", "information": "información", "back": "espalda",
        "parent": "padre", "face": "cara", "others": "otros", "level": "nivel",
        "office": "oficina", "door": "puerta", "health": "salud",
        "person": "persona", "art": "arte", "war": "guerra", "history": "historia",
        "party": "fiesta", "result": "resultado", "change": "cambio",
        "morning": "mañana", "reason": "razón", "research": "investigación",
        "girl": "chica", "boy": "chico", "moment": "momento", "air": "aire",
        "teacher": "maestro", "force": "fuerza", "education": "educación",
        "foot": "pie", "boy": "chico", "age": "edad", "policy": "política",
        "process": "proceso", "music": "música", "market": "mercado",
        "sense": "sentido", "nation": "nación", "plan": "plan", "college": "universidad",
        "interest": "interés", "death": "muerte", "experience": "experiencia",
        "effect": "effecto", "use": "uso", "class": "clase", "control": "control",
        "care": "cuidado", "field": "campo", "development": "desarrollo",
        "role": "papel", "effort": "esfuerzo", "rate": "tasa", "heart": "corazón",
        "drug": "droga", "show": "espectáculo", "leader": "líder", "light": "luz",
        "voice": "voz", "wife": "esposa", "mind": "mente", "price": "precio",
        "report": "informe", "decision": "decisión", "son": "hijo", "view": "vista",
        "relationship": "relación", "town": "pueblo", "road": "carretera",
        "arm": "brazo", "difference": "diferencia", "value": "valor",
        "building": "edificio", "action": "acción", "model": "modelo",
        "season": "temporada", "society": "sociedad", "tax": "impuesto",
        "director": "director", "position": "posición", "player": "jugador",
        "record": "registro", "paper": "papel", "space": "espacio",
        "ground": "suelo", "form": "forma", "event": "evento", "official": "oficial",
        "matter": "asunto", "center": "centro", "couple": "pareja",
        "site": "sitio", "project": "proyecto", "activity": "actividad",
        "star": "estrella", "table": "mesa", "need": "necesidad", "court": "corte",
        "oil": "aceite", "situation": "situación", "cost": "costo",
        "industry": "industria", "figure": "figura", "street": "calle",
        "image": "imagen", "phone": "teléfono", "data": "datos", "picture": "imagen",
        "practice": "práctica", "piece": "pedazo", "land": "tierra",
        "product": "producto", "doctor": "médico", "wall": "muro", "patient": "paciente",
        "worker": "trabajador", "news": "noticias", "test": "prueba",
        "movie": "película", "north": "norte", "love": "amor",
        "support": "apoyo", "technology": "tecnología", "step": "paso",
        "baby": "bebé", "computer": "ordenador", "type": "tipo",
        "attention": "atención", "draw": "dibujar", "film": "película",
        "tree": "árbol", "source": "fuente", "look": "mirada", "evidence": "evidencia",
    },
    # English -> French
    ("en", "fr"): {
        "hello": "bonjour", "world": "monde", "good": "bon", "morning": "matin",
        "night": "nuit", "day": "jour", "time": "temps", "year": "année",
        "person": "personne", "way": "façon", "thing": "chose", "man": "homme",
        "woman": "femme", "child": "enfant", "life": "vie", "hand": "main",
        "part": "partie", "place": "endroit", "case": "cas", "week": "semaine",
        "company": "entreprise", "system": "système", "program": "programme",
        "question": "question", "work": "travail", "government": "gouvernement",
        "number": "numéro", "point": "point", "home": "maison",
        "water": "eau", "room": "chambre", "mother": "mère", "area": "zone",
        "money": "argent", "story": "histoire", "fact": "fait", "month": "mois",
        "right": "droit", "study": "étude", "book": "livre", "eye": "œil",
        "job": "emploi", "word": "mot", "business": "affaires",
        "issue": "problème", "side": "côté", "kind": "genre", "head": "tête",
        "house": "maison", "service": "service", "friend": "ami",
        "father": "père", "power": "pouvoir", "hour": "heure", "game": "jeu",
        "line": "ligne", "end": "fin", "member": "membre", "law": "loi",
        "car": "voiture", "city": "ville", "community": "communauté",
        "name": "nom", "team": "équipe", "minute": "minute", "idea": "idée",
        "body": "corps", "information": "information", "back": "dos",
        "parent": "parent", "face": "visage", "level": "niveau",
        "office": "bureau", "door": "porte", "health": "santé",
        "art": "art", "war": "guerre", "history": "histoire",
        "party": "fête", "result": "résultat", "change": "changement",
        "reason": "raison", "research": "recherche", "girl": "fille",
        "boy": "garçon", "moment": "moment", "air": "air",
        "teacher": "professeur", "force": "force", "education": "éducation",
        "foot": "pied", "age": "âge", "policy": "politique",
        "process": "processus", "music": "musique", "market": "marché",
        "sense": "sens", "nation": "nation", "plan": "plan",
        "college": "collège", "interest": "intérêt", "death": "mort",
        "experience": "expérience", "use": "utilisation", "class": "classe",
        "control": "contrôle", "care": "soin", "field": "domaine",
        "development": "développement", "role": "rôle", "effort": "effort",
        "rate": "taux", "heart": "cœur", "show": "spectacle",
        "leader": "chef", "light": "lumière", "voice": "voix",
        "wife": "femme", "mind": "esprit", "price": "prix",
        "report": "rapport", "decision": "décision", "son": "fils",
        "view": "vue", "relationship": "relation", "town": "ville",
        "road": "route", "arm": "bras", "difference": "différence",
        "value": "valeur", "building": "bâtiment", "action": "action",
        "model": "modèle", "season": "saison", "society": "société",
        "tax": "impôt", "director": "directeur", "position": "position",
        "player": "joueur", "record": "record", "paper": "papier",
        "space": "espace", "ground": "sol", "form": "forme",
        "event": "événement", "official": "officiel", "matter": "matière",
        "center": "centre", "couple": "couple", "site": "site",
        "project": "projet", "activity": "activité", "star": "étoile",
        "table": "table", "need": "besoin", "court": "cour",
        "oil": "huile", "situation": "situation", "cost": "coût",
        "industry": "industrie", "figure": "figure", "street": "rue",
        "image": "image", "phone": "téléphone", "data": "données",
        "picture": "image", "practice": "pratique", "piece": "morceau",
        "land": "terre", "product": "produit", "doctor": "médecin",
        "wall": "mur", "patient": "patient", "worker": "travailleur",
        "news": "nouvelles", "test": "test", "movie": "film",
        "north": "nord", "love": "amour", "support": "soutien",
        "technology": "technologie", "step": "étape", "baby": "bébé",
        "computer": "ordinateur", "type": "type", "attention": "attention",
        "draw": "dessiner", "film": "film", "tree": "arbre",
        "source": "source", "look": "regard", "evidence": "preuve",
    },
    # English -> German
    ("en", "de"): {
        "hello": "hallo", "world": "Welt", "good": "gut", "morning": "Morgen",
        "night": "Nacht", "day": "Tag", "time": "Zeit", "year": "Jahr",
        "person": "Person", "way": "Weg", "thing": "Ding", "man": "Mann",
        "woman": "Frau", "child": "Kind", "life": "Leben", "hand": "Hand",
        "part": "Teil", "place": "Ort", "case": "Fall", "week": "Woche",
        "company": "Unternehmen", "system": "System", "program": "Programm",
        "question": "Frage", "work": "Arbeit", "government": "Regierung",
        "number": "Nummer", "point": "Punkt", "home": "Zuhause",
        "water": "Wasser", "room": "Zimmer", "mother": "Mutter",
        "area": "Bereich", "money": "Geld", "story": "Geschichte",
        "fact": "Tatsache", "month": "Monat", "right": "Recht",
        "study": "Studium", "book": "Buch", "eye": "Auge", "job": "Job",
        "word": "Wort", "business": "Geschäft", "issue": "Problem",
        "side": "Seite", "kind": "Art", "head": "Kopf", "house": "Haus",
        "service": "Dienst", "friend": "Freund", "father": "Vater",
        "power": "Macht", "hour": "Stunde", "game": "Spiel",
        "line": "Linie", "end": "Ende", "member": "Mitglied",
        "law": "Gesetz", "car": "Auto", "city": "Stadt",
        "community": "Gemeinschaft", "name": "Name", "team": "Team",
        "minute": "Minute", "idea": "Idee", "body": "Körper",
        "information": "Information", "back": "Rücken", "parent": "Elternteil",
        "face": "Gesicht", "level": "Ebene", "office": "Büro",
        "door": "Tür", "health": "Gesundheit", "art": "Kunst",
        "war": "Krieg", "history": "Geschichte", "party": "Party",
        "result": "Ergebnis", "change": "Änderung", "reason": "Grund",
        "research": "Forschung", "girl": "Mädchen", "boy": "Junge",
        "moment": "Moment", "air": "Luft", "teacher": "Lehrer",
        "force": "Kraft", "education": "Bildung", "foot": "Fuß",
        "age": "Alter", "policy": "Politik", "process": "Prozess",
        "music": "Musik", "market": "Markt", "sense": "Sinn",
        "nation": "Nation", "plan": "Plan", "college": "Hochschule",
        "interest": "Interesse", "death": "Tod", "experience": "Erfahrung",
        "use": "Verwendung", "class": "Klasse", "control": "Kontrolle",
        "care": "Pflege", "field": "Feld", "development": "Entwicklung",
        "role": "Rolle", "effort": "Anstrengung", "rate": "Rate",
        "heart": "Herz", "show": "Show", "leader": "Führer",
        "light": "Licht", "voice": "Stimme", "wife": "Frau",
        "mind": "Geist", "price": "Preis", "report": "Bericht",
        "decision": "Entscheidung", "son": "Sohn", "view": "Aussicht",
        "relationship": "Beziehung", "town": "Stadt", "road": "Straße",
        "arm": "Arm", "difference": "Unterschied", "value": "Wert",
        "building": "Gebäude", "action": "Aktion", "model": "Modell",
        "season": "Jahreszeit", "society": "Gesellschaft", "tax": "Steuer",
        "director": "Direktor", "position": "Position", "player": "Spieler",
        "record": "Rekord", "paper": "Papier", "space": "Raum",
        "ground": "Boden", "form": "Form", "event": "Ereignis",
        "official": "Beamter", "matter": "Angelegenheit",
        "center": "Zentrum", "couple": "Paar", "site": "Seite",
        "project": "Projekt", "activity": "Aktivität", "star": "Stern",
        "table": "Tisch", "need": "Bedarf", "court": "Gericht",
        "oil": "Öl", "situation": "Situation", "cost": "Kosten",
        "industry": "Industrie", "figure": "Figur", "street": "Straße",
        "image": "Bild", "phone": "Telefon", "data": "Daten",
        "picture": "Bild", "practice": "Praxis", "piece": "Stück",
        "land": "Land", "product": "Produkt", "doctor": "Arzt",
        "wall": "Wand", "patient": "Patient", "worker": "Arbeiter",
        "news": "Nachrichten", "test": "Test", "movie": "Film",
        "north": "Norden", "love": "Liebe", "support": "Unterstützung",
        "technology": "Technologie", "step": "Schritt", "baby": "Baby",
        "computer": "Computer", "type": "Typ", "attention": "Aufmerksamkeit",
        "draw": "zeichnen", "film": "Film", "tree": "Baum",
        "source": "Quelle", "look": "Blick", "evidence": "Beweis",
    },
    # English -> Italian
    ("en", "it"): {
        "hello": "ciao", "world": "mondo", "good": "buono", "morning": "mattina",
        "night": "notte", "day": "giorno", "time": "tempo", "year": "anno",
        "person": "persona", "way": "modo", "thing": "cosa", "man": "uomo",
        "woman": "donna", "child": "bambino", "life": "vita", "hand": "mano",
        "part": "parte", "place": "posto", "case": "caso", "week": "settimana",
        "company": "azienda", "system": "sistema", "program": "programma",
        "question": "domanda", "work": "lavoro", "government": "governo",
        "number": "numero", "point": "punto", "home": "casa",
        "water": "acqua", "room": "stanza", "mother": "madre",
        "area": "area", "money": "soldi", "story": "storia",
        "fact": "fatto", "month": "mese", "right": "diritto",
        "study": "studio", "book": "libro", "eye": "occhio", "job": "lavoro",
        "word": "parola", "business": "affari", "issue": "problema",
        "side": "lato", "kind": "tipo", "head": "testa", "house": "casa",
        "service": "servizio", "friend": "amico", "father": "padre",
        "power": "potere", "hour": "ora", "game": "gioco",
        "line": "linea", "end": "fine", "member": "membro",
        "law": "legge", "car": "macchina", "city": "città",
        "community": "comunità", "name": "nome", "team": "squadra",
        "minute": "minuto", "idea": "idea", "body": "corpo",
        "information": "informazione", "back": "schiena", "parent": "genitore",
        "face": "faccia", "level": "livello", "office": "ufficio",
        "door": "porta", "health": "salute", "art": "arte",
        "war": "guerra", "history": "storia", "party": "festa",
        "result": "risultato", "change": "cambiamento", "reason": "ragione",
        "research": "ricerca", "girl": "ragazza", "boy": "ragazzo",
        "moment": "momento", "air": "aria", "teacher": "insegnante",
        "force": "forza", "education": "istruzione", "foot": "piede",
        "age": "età", "policy": "politica", "process": "processo",
        "music": "musica", "market": "mercato", "sense": "senso",
        "nation": "nazione", "plan": "piano", "college": "college",
        "interest": "interesse", "death": "morte", "experience": "esperienza",
        "use": "uso", "class": "classe", "control": "controllo",
        "care": "cura", "field": "campo", "development": "sviluppo",
        "role": "ruolo", "effort": "sforzo", "rate": "tasso",
        "heart": "cuore", "show": "spettacolo", "leader": "leader",
        "light": "luce", "voice": "voce", "wife": "moglie",
        "mind": "mente", "price": "prezzo", "report": "rapporto",
        "decision": "decisione", "son": "figlio", "view": "vista",
        "relationship": "relazione", "town": "città", "road": "strada",
        "arm": "braccio", "difference": "differenza", "value": "valore",
        "building": "edificio", "action": "azione", "model": "modello",
        "season": "stagione", "society": "società", "tax": "tassa",
        "director": "direttore", "position": "posizione", "player": "giocatore",
        "record": "record", "paper": "carta", "space": "spazio",
        "ground": "terra", "form": "forma", "event": "evento",
        "official": "ufficiale", "matter": "materia", "center": "centro",
        "couple": "coppia", "site": "sito", "project": "progetto",
        "activity": "attività", "star": "stella", "table": "tavolo",
        "need": "bisogno", "court": "corte", "oil": "olio",
        "situation": "situazione", "cost": "costo", "industry": "industria",
        "figure": "figura", "street": "strada", "image": "immagine",
        "phone": "telefono", "data": "dati", "picture": "immagine",
        "practice": "pratica", "piece": "pezzo", "land": "terra",
        "product": "prodotto", "doctor": "dottore", "wall": "muro",
        "patient": "paziente", "worker": "lavoratore", "news": "notizie",
        "test": "test", "movie": "film", "north": "nord",
        "love": "amore", "support": "supporto", "technology": "tecnologia",
        "step": "passo", "baby": "bambino", "computer": "computer",
        "type": "tipo", "attention": "attenzione", "draw": "disegnare",
        "film": "film", "tree": "albero", "source": "fonte",
        "look": "sguardo", "evidence": "prova",
    },
    # English -> Portuguese
    ("en", "pt"): {
        "hello": "olá", "world": "mundo", "good": "bom", "morning": "manhã",
        "night": "noite", "day": "dia", "time": "tempo", "year": "ano",
        "person": "pessoa", "way": "caminho", "thing": "coisa", "man": "homem",
        "woman": "mulher", "child": "criança", "life": "vida", "hand": "mão",
        "part": "parte", "place": "lugar", "case": "caso", "week": "semana",
        "company": "empresa", "system": "sistema", "program": "programa",
        "question": "pergunta", "work": "trabalho", "government": "governo",
        "number": "número", "point": "ponto", "home": "casa",
        "water": "água", "room": "quarto", "mother": "mãe",
        "area": "área", "money": "dinheiro", "story": "história",
        "fact": "fato", "month": "mês", "right": "direito",
        "study": "estudo", "book": "livro", "eye": "olho", "job": "emprego",
        "word": "palavra", "business": "negócio", "issue": "problema",
        "side": "lado", "kind": "tipo", "head": "cabeça", "house": "casa",
        "service": "serviço", "friend": "amigo", "father": "pai",
        "power": "poder", "hour": "hora", "game": "jogo",
        "line": "linha", "end": "fim", "member": "membro",
        "law": "lei", "car": "carro", "city": "cidade",
        "community": "comunidade", "name": "nome", "team": "equipe",
        "minute": "minuto", "idea": "ideia", "body": "corpo",
        "information": "informação", "back": "costas", "parent": "pai",
        "face": "rosto", "level": "nível", "office": "escritório",
        "door": "porta", "health": "saúde", "art": "arte",
        "war": "guerra", "history": "história", "party": "festa",
        "result": "resultado", "change": "mudança", "reason": "razão",
        "research": "pesquisa", "girl": "menina", "boy": "menino",
        "moment": "momento", "air": "ar", "teacher": "professor",
        "force": "força", "education": "educação", "foot": "pé",
        "age": "idade", "policy": "política", "process": "processo",
        "music": "música", "market": "mercado", "sense": "sentido",
        "nation": "nação", "plan": "plano", "college": "faculdade",
        "interest": "interesse", "death": "morte", "experience": "experiência",
        "use": "uso", "class": "classe", "control": "controle",
        "care": "cuidado", "field": "campo", "development": "desenvolvimento",
        "role": "papel", "effort": "esforço", "rate": "taxa",
        "heart": "coração", "show": "show", "leader": "líder",
        "light": "luz", "voice": "voz", "wife": "esposa",
        "mind": "mente", "price": "preço", "report": "relatório",
        "decision": "decisão", "son": "filho", "view": "vista",
        "relationship": "relacionamento", "town": "cidade", "road": "estrada",
        "arm": "braço", "difference": "diferença", "value": "valor",
        "building": "prédio", "action": "ação", "model": "modelo",
        "season": "estação", "society": "sociedade", "tax": "imposto",
        "director": "diretor", "position": "posição", "player": "jogador",
        "record": "recorde", "paper": "papel", "space": "espaço",
        "ground": "chão", "form": "forma", "event": "evento",
        "official": "oficial", "matter": "assunto", "center": "centro",
        "couple": "casal", "site": "site", "project": "projeto",
        "activity": "atividade", "star": "estrela", "table": "mesa",
        "need": "necessidade", "court": "tribunal", "oil": "óleo",
        "situation": "situação", "cost": "custo", "industry": "indústria",
        "figure": "figura", "street": "rua", "image": "imagem",
        "phone": "telefone", "data": "dados", "picture": "imagem",
        "practice": "prática", "piece": "pedaço", "land": "terra",
        "product": "produto", "doctor": "médico", "wall": "parede",
        "patient": "paciente", "worker": "trabalhador", "news": "notícias",
        "test": "teste", "movie": "filme", "north": "norte",
        "love": "amor", "support": "suporte", "technology": "tecnologia",
        "step": "passo", "baby": "bebê", "computer": "computador",
        "type": "tipo", "attention": "atenção", "draw": "desenhar",
        "film": "filme", "tree": "árvore", "source": "fonte",
        "look": "olhar", "evidence": "evidência",
    },
}

# Reverse dictionaries for target -> source
_REVERSE_DICTS: Dict[Tuple[str, str], Dict[str, str]] = {}
for (src, tgt), mapping in _DICTIONARIES.items():
    _REVERSE_DICTS[(tgt, src)] = {v: k for k, v in mapping.items()}


@dataclass
class TranslationResult:
    """Result of a translation."""

    original_text: str = ""
    translated_text: str = ""
    source_language: str = "en"
    target_language: str = "es"
    confidence: float = 0.0
    word_count: int = 0
    translated_word_count: int = 0
    untranslated_words: List[str] = field(default_factory=list)


class Translator:
    """Dictionary-based translator for common language pairs."""

    def __init__(self) -> None:
        self.dictionaries = _DICTIONARIES
        self.reverse_dicts = _REVERSE_DICTS
        self.supported_pairs = set(_DICTIONARIES.keys())

    def is_supported_pair(self, source: str, target: str) -> bool:
        """Check if a language pair is supported."""
        return (source, target) in self.supported_pairs

    def get_supported_languages(self) -> List[str]:
        """Get list of all supported language codes."""
        langs = set()
        for src, tgt in self.supported_pairs:
            langs.add(src)
            langs.add(tgt)
        return sorted(langs)

    def get_supported_pairs(self) -> List[Tuple[str, str]]:
        """Get list of all supported language pairs."""
        return sorted(self.supported_pairs)

    def _get_dictionary(self, source: str, target: str) -> Dict[str, str]:
        """Get the translation dictionary for a language pair."""
        return self.dictionaries.get((source, target), {})

    def translate_word(self, word: str, source: str, target: str) -> Optional[str]:
        """Translate a single word."""
        dictionary = self._get_dictionary(source, target)
        return dictionary.get(word.lower())

    def translate(self, text: str, source: str = "en", target: str = "es") -> TranslationResult:
        """Translate text from source language to target language.

        Uses a word-by-word dictionary approach. Words not found in the
        dictionary are kept as-is.
        """
        if not text:
            return TranslationResult(
                original_text=text,
                translated_text="",
                source_language=source,
                target_language=target,
            )

        if not self.is_supported_pair(source, target):
            return TranslationResult(
                original_text=text,
                translated_text=text,
                source_language=source,
                target_language=target,
                confidence=0.0,
            )

        dictionary = self._get_dictionary(source, target)
        words = re.findall(r"[a-zA-Z']+|\S|\s+", text)

        translated_words = []
        untranslated = []
        translated_count = 0

        for word in words:
            if word.isspace():
                translated_words.append(word)
                continue

            # Try to translate the word
            lower_word = word.lower()
            translation = dictionary.get(lower_word)

            if translation:
                # Preserve capitalization
                if word[0].isupper():
                    translation = translation[0].upper() + translation[1:]
                translated_words.append(translation)
                translated_count += 1
            else:
                translated_words.append(word)
                if lower_word.isalpha():
                    untranslated.append(lower_word)

        translated_text = "".join(translated_words)
        word_count = len([w for w in words if w.strip()])
        confidence = translated_count / max(word_count, 1)

        return TranslationResult(
            original_text=text,
            translated_text=translated_text,
            source_language=source,
            target_language=target,
            confidence=round(confidence, 4),
            word_count=word_count,
            translated_word_count=translated_count,
            untranslated_words=untranslated,
        )

    def detect_and_translate(self, text: str, target: str = "en") -> TranslationResult:
        """Auto-detect source language and translate to target.

        Note: This is a simplified detection. For production, use a
        proper language detection library.
        """
        # Simple detection: check which source language has most matches
        best_source = "en"
        best_score = 0

        for src_lang in self.get_supported_languages():
            if src_lang == target:
                continue
            dictionary = self._get_dictionary(src_lang, target)
            if not dictionary:
                continue
            words = set(re.findall(r"[a-zA-Z']+", text.lower()))
            score = len(words & set(dictionary.keys()))
            if score > best_score:
                best_score = score
                best_source = src_lang

        return self.translate(text, source=best_source, target=target)

    def batch_translate(
        self, texts: List[str], source: str = "en", target: str = "es"
    ) -> List[TranslationResult]:
        """Translate a batch of texts."""
        return [self.translate(t, source=source, target=target) for t in texts]

    def add_translation(
        self, source: str, target: str, source_word: str, target_word: str
    ) -> None:
        """Add a custom translation to the dictionary."""
        key = (source, target)
        if key not in self.dictionaries:
            self.dictionaries[key] = {}
            self.supported_pairs.add(key)
        self.dictionaries[key][source_word.lower()] = target_word.lower()
