"""Telling the time on a 12-hour clock face, in five-minute steps. Pure rules.

Everyday spoken forms, one standard form per language (regional variants such as German
"viertel vier" or "zehn vor halb" are not used):

- German: "fünf nach drei", "Viertel nach drei", "fünf vor halb vier", "halb vier",
  "Viertel vor vier", "drei Uhr", "ein Uhr".
- French: "trois heures cinq", "trois heures et quart", "trois heures et demie",
  "quatre heures moins le quart", "une heure", "midi" (the clock is read as daytime).
- Italian: "sono le tre e cinque", "sono le tre e un quarto", "sono le tre e mezza",
  "sono le quattro meno un quarto", "è l'una", "è mezzogiorno".
- British English: "five past three", "quarter past three", "half past three",
  "twenty-five to four", "three o'clock".

The Czech line is the learner's anchor and the classic trap: Czech "čtvrt na čtyři" is 3:15,
which German says "Viertel nach drei". It is given for full, quarter and half hours; other times
show digits.
"""

from dataclasses import dataclass

from app.domain.enums import Language
from app.domain.numbers import spell

# fmt: off
_DE_HOURS = ["zwölf", "eins", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun",
             "zehn", "elf", "zwölf"]
_FR_HOURS = ["midi", "une heure", "deux heures", "trois heures", "quatre heures", "cinq heures",
             "six heures", "sept heures", "huit heures", "neuf heures", "dix heures",
             "onze heures", "midi"]
_IT_HOURS = ["mezzogiorno", "l'una", "le due", "le tre", "le quattro", "le cinque", "le sei",
             "le sette", "le otto", "le nove", "le dieci", "le undici", "mezzogiorno"]
_CS_COUNT = ["dvanáct", "jedna", "dvě", "tři", "čtyři", "pět", "šest", "sedm", "osm", "devět",
             "deset", "jedenáct", "dvanáct"]
_CS_ON = ["dvanáct", "jednu", "dvě", "tři", "čtyři", "pět", "šest", "sedm", "osm", "devět",
          "deset", "jedenáct", "dvanáct"]  # čtvrt na jednu
_CS_HALF = ["dvanácté", "jedné", "druhé", "třetí", "čtvrté", "páté", "šesté", "sedmé", "osmé",
            "deváté", "desáté", "jedenácté", "dvanácté"]  # půl jedné
# fmt: on
MINUTES = tuple(range(0, 60, 5))


@dataclass(frozen=True, slots=True)
class Time:
    hour: int  # 1..12
    minute: int  # 0, 5, ... 55

    def __post_init__(self) -> None:
        if not 1 <= self.hour <= 12 or self.minute not in MINUTES:
            raise ValueError(f"not a clock time: {self.hour}:{self.minute}")

    @property
    def next_hour(self) -> int:
        return self.hour % 12 + 1

    @property
    def digits(self) -> str:
        return f"{self.hour}:{self.minute:02d}"

    def shifted(self, minutes: int) -> "Time":
        total = ((self.hour % 12) * 60 + self.minute + minutes) % 720
        h, m = divmod(total, 60)
        return Time(h or 12, m)


def _de(t: Time) -> str:
    h, n, m = _DE_HOURS[t.hour], _DE_HOURS[t.next_hour], t.minute
    if m == 0:
        return f"{'ein' if t.hour == 1 else h} Uhr"
    if m == 15:
        return f"Viertel nach {h}"
    if m == 30:
        return f"halb {n}"
    if m == 45:
        return f"Viertel vor {n}"
    if m < 25:
        return f"{spell(m, 'de')} nach {h}"
    if m == 25:
        return f"fünf vor halb {n}"
    if m == 35:
        return f"fünf nach halb {n}"
    return f"{spell(60 - m, 'de')} vor {n}"


def _fr(t: Time) -> str:
    h, n, m = _FR_HOURS[t.hour], _FR_HOURS[t.next_hour], t.minute
    if m == 0:
        return h
    if m == 15:
        return f"{h} et quart"
    if m == 30:
        # "midi et demi": demi agrees with the masculine midi; "heure(s) et demie".
        return f"{h} et demi" if t.hour == 12 else f"{h} et demie"
    if m == 45:
        return f"{n} moins le quart"
    if m < 30:
        return f"{h} {spell(m, 'fr')}"
    return f"{n} moins {spell(60 - m, 'fr')}"


def _it(t: Time) -> str:
    def verb(hour: int) -> str:
        return "è" if hour in (1, 12) else "sono"

    h, n, m = _IT_HOURS[t.hour], _IT_HOURS[t.next_hour], t.minute
    if m == 0:
        return f"{verb(t.hour)} {h}"
    if m == 15:
        return f"{verb(t.hour)} {h} e un quarto"
    if m == 30:
        return f"{verb(t.hour)} {h} e mezza"
    if m == 45:
        return f"{verb(t.next_hour)} {n} meno un quarto"
    if m < 30:
        return f"{verb(t.hour)} {h} e {spell(m, 'it')}"
    return f"{verb(t.next_hour)} {n} meno {spell(60 - m, 'it')}"


def _en(t: Time) -> str:
    h, n, m = spell(t.hour, "en"), spell(t.next_hour, "en"), t.minute
    if m == 0:
        return f"{h} o'clock"
    if m == 15:
        return f"quarter past {h}"
    if m == 30:
        return f"half past {h}"
    if m == 45:
        return f"quarter to {n}"
    if m < 30:
        return f"{spell(m, 'en')} past {h}"
    return f"{spell(60 - m, 'en')} to {n}"


def say(t: Time, language: Language) -> str:
    return {"de": _de, "fr": _fr, "it": _it, "en": _en}[language](t)


def czech(t: Time) -> str:
    """The everyday Czech form for full, quarter and half hours; digits otherwise."""
    m = t.minute
    if m == 0:
        unit = "hodina" if t.hour == 1 else "hodiny" if t.hour in (2, 3, 4) else "hodin"
        return f"{_CS_COUNT[t.hour]} {unit}"
    if m == 15:
        return f"čtvrt na {_CS_ON[t.next_hour]}"
    if m == 30:
        return f"půl {_CS_HALF[t.next_hour]}"
    if m == 45:
        return f"tři čtvrtě na {_CS_ON[t.next_hour]}"
    return t.digits


def distractors(t: Time) -> list[Time]:
    """Times learners confuse with t, most tempting first, without duplicates."""
    out: list[Time] = []
    for c in (
        t.shifted(-60) if t.minute in (15, 30, 45) else t.shifted(60),  # the Czech-anchor trap
        Time(t.hour, (60 - t.minute) % 60) if t.minute not in (0, 30) else t.shifted(30),
        t.shifted(60) if t.minute in (15, 30, 45) else t.shifted(-60),
        t.shifted(5),
        t.shifted(-5),
        t.shifted(30),
    ):
        if c != t and c not in out:
            out.append(c)
    return out
