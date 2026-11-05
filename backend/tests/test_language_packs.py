"""Every target language has one complete pack, and the frontend keyboard matches it."""

import re
from pathlib import Path

from app.domain.enums import Language
from app.domain.grammar import ErrorTag
from app.domain.language_packs import PACKS, pack
from app.domain.voices import CATALOG, DEFAULT_VOICES, SAMPLES

KEYBOARD_TS = Path(__file__).resolve().parents[2] / "frontend" / "lib" / "keyboard.ts"


def test_every_language_has_a_pack_and_a_voice():
    assert set(PACKS) == set(Language)
    for lang, p in PACKS.items():
        assert p.language == lang and p.name_cs and p.citation_articles and p.determiners
        assert SAMPLES[lang] == p.voice_sample != ""
        assert DEFAULT_VOICES[lang] in {v.id for v in CATALOG if v.language == lang}
        assert set(p.tag_hints) <= {t.value for t in ErrorTag}


def test_pack_rules_are_consistent():
    for p in PACKS.values():
        assert set(p.definite_articles) <= p.determiners
        for real, typed, note in p.spelling_variants:
            assert real != typed and note
        for real, typed in p.sentence_fallbacks:
            assert (real, typed) in {(r, t) for r, t, _ in p.spelling_variants}
        for lower, upper in p.alt_chars.values():
            assert lower in p.special_chars or lower == "œ"
            assert upper == lower.upper() or (lower, upper) == ("ß", "ẞ")


def test_unfallback_reads_keyboard_substitutes_in_german_only():
    assert pack(Language.DE).unfallback("Strasse fuer Baeren") == "Straße für Bären"
    assert pack(Language.FR).unfallback("poete") == "poete"


def _ts_table(name: str) -> str:
    src = KEYBOARD_TS.read_text(encoding="utf-8")
    m = re.search(rf"const {name}[^=]*= \{{(.*?)\n\}};", src, re.S)
    assert m, f"{name} not found in keyboard.ts"
    return m.group(1)


def test_frontend_keyboard_matches_the_packs():
    special = _ts_table("SPECIAL_CHARS")
    for lang, p in PACKS.items():
        m = re.search(rf"\b{lang.value}: \[(.*?)\]", special)
        assert m, lang
        assert tuple(re.findall(r'"([^"]+)"', m.group(1))) == p.special_chars, lang
    alt = _ts_table("ALT_CHARS")
    for lang, p in PACKS.items():
        m = re.search(rf"\b{lang.value}: \{{(.*?)\}},?(?:\n|$)", alt)
        found = (
            dict(
                (k, (a, b))
                for k, a, b in re.findall(r'(Key\w): \["([^"]+)", "([^"]+)"\]', m.group(1))
            )
            if m
            else {}
        )
        assert found == p.alt_chars, lang
