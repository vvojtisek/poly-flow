"""Numbers 0 to 9999 written out in German, French, Italian and (British) English. Pure rules.

`spell(n, language)` gives the standard written form; `accepted(n, language)` the forms a learner
may also write: German "einhundert" / "eintausend" and "elfhundert"; French with the 1990
spelling reform (hyphens everywhere: "vingt-et-un", "deux-cents") as well as the traditional one,
which the hyphen-or-space rule below covers, and "onze cents"; Italian "centootto" next to
"centotto"; English with or without "and", and "a hundred" / "a thousand". Comparison ignores
case, surrounding space and the difference between a hyphen and a space, but not the letters:
"quatre-vingt" for 80 is wrong (it is "quatre-vingts").
"""

import re

from app.domain.enums import Language

MAX = 9999

# fmt: off
_DE_ONES = ["null", "eins", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun",
            "zehn", "elf", "zwölf", "dreizehn", "vierzehn", "fünfzehn", "sechzehn", "siebzehn",
            "achtzehn", "neunzehn"]
_DE_TENS = ["", "", "zwanzig", "dreißig", "vierzig", "fünfzig", "sechzig", "siebzig", "achtzig",
            "neunzig"]
_FR_ONES = ["zéro", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf", "dix",
            "onze", "douze", "treize", "quatorze", "quinze", "seize", "dix-sept", "dix-huit",
            "dix-neuf"]
_FR_TENS = ["", "", "vingt", "trente", "quarante", "cinquante", "soixante"]
_IT_ONES = ["zero", "uno", "due", "tre", "quattro", "cinque", "sei", "sette", "otto", "nove",
            "dieci", "undici", "dodici", "tredici", "quattordici", "quindici", "sedici",
            "diciassette", "diciotto", "diciannove"]
_IT_TENS = ["", "", "venti", "trenta", "quaranta", "cinquanta", "sessanta", "settanta", "ottanta",
            "novanta"]
_EN_ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
            "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
            "eighteen", "nineteen"]
_EN_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
# fmt: on


def _check(n: int) -> None:
    if not 0 <= n <= MAX:
        raise ValueError(f"number out of range 0..{MAX}: {n}")


# German ------------------------------------------------------------------------------------


def _de_below_100(n: int) -> str:
    if n < 20:
        return _DE_ONES[n]
    tens, ones = divmod(n, 10)
    if ones == 0:
        return _DE_TENS[tens]
    unit = "ein" if ones == 1 else _DE_ONES[ones]
    return f"{unit}und{_DE_TENS[tens]}"


def _de(n: int, one_thousand: bool = False, one_hundred: bool = False) -> str:
    """The flags write "eintausend" / "einhundert" instead of "tausend" / "hundert"."""
    if n < 100:
        return _de_below_100(n)
    out = ""
    thousands, rest = divmod(n, 1000)
    hundreds, rest = divmod(rest, 100)
    for count, word, explicit in (
        (thousands, "tausend", one_thousand),
        (hundreds, "hundert", one_hundred),
    ):
        if count:
            lead = "ein" if count == 1 else _DE_ONES[count]
            out += (lead if count > 1 or explicit else "") + word
    if rest:
        out += _de_below_100(rest)
    return out


# French ------------------------------------------------------------------------------------


def _fr_below_100(n: int) -> str:
    """Traditional spelling: hyphens below 100 except around "et"."""
    if n < 20:
        return _FR_ONES[n]
    if n < 70:
        tens, ones = divmod(n, 10)
        if ones == 0:
            return _FR_TENS[tens]
        if ones == 1:
            return f"{_FR_TENS[tens]} et un"
        return f"{_FR_TENS[tens]}-{_FR_ONES[ones]}"
    if n < 80:
        if n == 71:
            return "soixante et onze"
        return f"soixante-{_FR_ONES[n - 60]}"
    if n == 80:
        return "quatre-vingts"
    return f"quatre-vingt-{_FR_ONES[n - 80]}"


def _fr_below_1000(n: int) -> str:
    hundreds, rest = divmod(n, 100)
    if not hundreds:
        return _fr_below_100(rest)
    head = "cent" if hundreds == 1 else f"{_FR_ONES[hundreds]} cent"
    if rest == 0:
        return head + ("s" if hundreds > 1 else "")
    return f"{head} {_fr_below_100(rest)}"


def _fr(n: int) -> str:
    thousands, rest = divmod(n, 1000)
    if not thousands:
        return _fr_below_1000(rest)
    # "mille" never takes an s; "cents"/"vingts" before mille lose it (deux cent mille), but
    # thousands here are below 10, so that case does not arise.
    head = "mille" if thousands == 1 else f"{_FR_ONES[thousands]} mille"
    return head if rest == 0 else f"{head} {_fr_below_1000(rest)}"


# Italian -----------------------------------------------------------------------------------


def _it_below_100(n: int) -> str:
    if n < 20:
        return _IT_ONES[n]
    tens, ones = divmod(n, 10)
    t = _IT_TENS[tens]
    if ones == 0:
        return t
    if ones in (1, 8):
        t = t[:-1]  # ventuno, ventotto
    return t + ("tré" if ones == 3 else _IT_ONES[ones])


def _it(n: int) -> str:
    out = ""
    thousands, rest = divmod(n, 1000)
    if thousands:
        out += "mille" if thousands == 1 else _IT_ONES[thousands] + "mila"
    hundreds, rest = divmod(rest, 100)
    if hundreds:
        out += "cento" if hundreds == 1 else _IT_ONES[hundreds] + "cento"
    if rest:
        # centootto/centotto: the elided form is the common written one.
        tail = _it_below_100(rest)
        if hundreds and tail.startswith("ott"):
            out = out[:-1]
        out += "tré" if rest == 3 and (thousands or hundreds) else tail
    return out or _IT_ONES[0]


# English -----------------------------------------------------------------------------------


def _en_below_100(n: int) -> str:
    if n < 20:
        return _EN_ONES[n]
    tens, ones = divmod(n, 10)
    return _EN_TENS[tens] + (f"-{_EN_ONES[ones]}" if ones else "")


def _en(n: int, use_and: bool = True) -> str:
    if n < 100:
        return _en_below_100(n)
    parts: list[str] = []
    thousands, rest = divmod(n, 1000)
    if thousands:
        parts.append(f"{_EN_ONES[thousands]} thousand")
    hundreds, rest = divmod(rest, 100)
    if hundreds:
        parts.append(f"{_EN_ONES[hundreds]} hundred")
    if rest:
        if parts and use_and:
            parts.append("and")
        parts.append(_en_below_100(rest))
    return " ".join(parts)


# Public ------------------------------------------------------------------------------------


def spell(n: int, language: Language) -> str:
    _check(n)
    if language == "de":
        return _de(n)
    if language == "fr":
        return _fr(n)
    if language == "it":
        return _it(n)
    return _en(n)


def accepted(n: int, language: Language) -> set[str]:
    """Every written form accepted for n, normalised with `normalise`."""
    forms = {spell(n, language)}
    hundreds_over_1000 = 1100 <= n <= 1999  # elfhundert, onze cents, eleven hundred
    if language == "de":
        forms |= {_de(n, a, b) for a in (False, True) for b in (False, True)}
        if hundreds_over_1000:
            rest = n % 100
            forms.add(_DE_ONES[n // 100] + "hundert" + (_de_below_100(rest) if rest else ""))
    elif language == "fr":
        if hundreds_over_1000:
            rest = n % 100
            head = f"{_FR_ONES[n // 100]} cent"
            forms.add(f"{head} {_fr_below_100(rest)}" if rest else head + "s")
    elif language == "it":
        s = spell(n, language)
        if n % 100 == 8 and n % 1000 >= 100:
            forms.add(s.replace("centotto", "centootto"))
        if n % 100 == 1 and n % 1000 >= 100:
            forms.add(s.removesuffix("ouno") + "uno")  # centuno next to centouno
        forms.add(s.replace("tré", "tre"))  # a missing accent is a common slip; still accepted
    else:
        forms.add(_en(n, use_and=False))
        if hundreds_over_1000:
            rest = n % 100
            head = f"{_EN_ONES[n // 100]} hundred"
            if rest:
                forms |= {f"{head} and {_en_below_100(rest)}", f"{head} {_en_below_100(rest)}"}
            else:
                forms.add(head)
        for f in list(forms):
            if f.startswith(("one hundred", "one thousand")):
                forms.add("a" + f.removeprefix("one"))
    return {normalise(f) for f in forms}


def normalise(text: str) -> str:
    """Lowercase, trimmed, hyphens and runs of space as one space, including typographic hyphens."""
    return re.sub(r"[\s\-\u2010\u2011]+", " ", text.strip().lower())


def check(n: int, answer: str, language: Language) -> bool:
    return normalise(answer) in accepted(n, language)


def parse_digits(answer: str) -> int | None:
    """A typed number (spaces and dots as thousand separators allowed), or None."""
    cleaned = re.sub(r"[\s.]", "", answer.strip())
    return int(cleaned) if re.fullmatch(r"\d{1,4}", cleaned) else None
