"""Grammar content packs and answer grading (pure, no DB)."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain.enums import Language
from app.domain.grammar import (
    LEVELS,
    ErrorTag,
    Exercise,
    ExerciseKind,
    GrammarPack,
    blank,
    classify,
    grade,
)

DATA = Path(__file__).resolve().parents[1] / "data" / "grammar"
DE = Language.DE


def test_shipped_packs_validate_and_cover_a1_to_b2():
    files = sorted(DATA.glob("*.grammar.json"))
    assert files, "no grammar packs shipped"
    for f in files:
        pack = GrammarPack.model_validate(json.loads(f.read_text(encoding="utf-8")))
        assert pack.review_status in ("unreviewed", "reviewed")
        assert pack.source and pack.license and pack.revision
        if pack.language == DE:
            assert {u.level for u in pack.units} == set(LEVELS)
        for u in pack.units:
            kinds = {e.kind for e in u.exercises}
            assert len(kinds) >= 2, f"{u.id}: needs varied exercise kinds"
            for e in u.exercises:
                # The shown answer always grades as correct (no self-contradicting item).
                g = grade(
                    pack.language,
                    e.kind,
                    e.answers,
                    text=None if e.kind == ExerciseKind.CHOICE else e.answers[0],
                    choice=e.answers[0] if e.kind == ExerciseKind.CHOICE else None,
                    case_sensitive_target=e.direction != "target-cs",
                )
                assert g.correct, f"{e.id}: shown answer does not grade as correct"


def test_shipped_de_pack_has_every_exercise_kind():
    pack = GrammarPack.model_validate_json((DATA / "de.grammar.json").read_text(encoding="utf-8"))
    kinds = {e.kind for u in pack.units for e in u.exercises}
    assert kinds == set(ExerciseKind)
    directions = {e.direction for u in pack.units for e in u.exercises if e.direction}
    assert directions == {"cs-target", "target-cs"}


def _ex(**kw) -> dict:
    base = {"id": "x-1", "explain": "proto", "answers": ["der"]}
    return base | kw


def test_choice_needs_its_answer_among_options():
    with pytest.raises(ValidationError):
        Exercise.model_validate(
            _ex(kind="choice", prompt="___ Hund", options=["die", "das"], answers=["der"])
        )


def test_gap_needs_exactly_one_blank():
    with pytest.raises(ValidationError):
        Exercise.model_validate(_ex(kind="gap", prompt="Ich ___ ___", answers=["bin"]))


def test_order_answer_must_use_the_tiles_and_tiles_must_be_shuffled():
    with pytest.raises(ValidationError):
        Exercise.model_validate(
            _ex(kind="order", prompt="Jsem", tokens=["bin", "ich"], answers=["Ich bin müde"])
        )
    with pytest.raises(ValidationError):
        Exercise.model_validate(
            _ex(kind="order", prompt="Jsem", tokens=["ich", "bin"], answers=["Ich bin"])
        )


def test_translate_needs_direction():
    with pytest.raises(ValidationError):
        Exercise.model_validate(_ex(kind="translate", prompt="Jsem", answers=["Ich bin"]))


def test_choice_grading_tags_article_swaps():
    g = grade(DE, ExerciseKind.CHOICE, ["den"], choice="der")
    assert not g.correct and g.error == ErrorTag.ARTICLE
    assert grade(DE, ExerciseKind.CHOICE, ["den"], choice="den").correct


def test_text_grading_ignores_punctuation_and_initial_capital():
    answers = ["Ich habe eine Idee"]
    assert grade(DE, ExerciseKind.TRANSLATE, answers, text="ich habe eine Idee.").correct
    assert grade(DE, ExerciseKind.TRANSLATE, answers, text="  Ich  habe eine Idee!  ").correct


def test_lower_case_german_noun_is_wrong_and_tagged():
    g = grade(DE, ExerciseKind.TRANSLATE, ["Ich habe eine Idee"], text="Ich habe eine idee")
    assert not g.correct and g.error == ErrorTag.CAPITALISATION and g.note == "de_noun_capital"


def test_umlaut_fallback_is_accepted_with_note():
    g = grade(DE, ExerciseKind.TRANSLATE, ["Ich habe zwei Brüder"], text="Ich habe zwei Brueder")
    assert g.correct and g.verdict == "accepted_variant" and g.note == "umlaut_as_e"
    g = grade(DE, ExerciseKind.GAP, ["heißt"], text="heisst")
    assert g.correct and g.verdict == "accepted_variant"


def test_czech_answer_free_word_order_and_missing_diacritics():
    answers = ["Nemá čas"]
    kw = {"case_sensitive_target": False}
    assert grade(DE, ExerciseKind.TRANSLATE, answers, text="čas nemá", **kw).correct
    g = grade(DE, ExerciseKind.TRANSLATE, answers, text="nema cas", **kw)
    assert g.correct and g.note == "cs_diacritics"


@pytest.mark.parametrize(
    ("expected", "answer", "tag"),
    [
        ("Ich sehe den Hund", "Ich sehe der Hund", ErrorTag.ARTICLE),
        ("Ich sehe den Hund", "Ich sehe Hund", ErrorTag.ARTICLE),
        ("Er arbeitet in Prag", "Er arbeitt in Prag", ErrorTag.ENDING),
        ("Du wohnst in Prag", "Du wohne in Prag", ErrorTag.ENDING),
        ("Heute gehe ich ins Kino", "Heute ich gehe ins Kino", ErrorTag.WORD_ORDER),
        ("Ich habe zwei Brüder", "Ich habe zwei Bruder", ErrorTag.DIACRITICS),
        ("Ich fahre mit dem Bus", "Ich fahre in dem Bus", ErrorTag.WORD_CHOICE),
        ("Der Hund schläft", "Die Katze isst etwas", ErrorTag.OTHER),
    ],
)
def test_classify_names_the_mistake(expected, answer, tag):
    assert classify(DE, expected, answer) == tag


def test_wrong_text_returns_the_closest_accepted_answer():
    answers = ["Heute gehe ich ins Kino", "Ich gehe heute ins Kino"]
    g = grade(DE, ExerciseKind.TRANSLATE, answers, text="Ich gehe heute in Kino")
    assert not g.correct and g.matched == "Ich gehe heute ins Kino"


def test_blank_fills_the_gap():
    assert blank("Ich ___ müde.", "bin") == "Ich bin müde."
    assert blank("Hast du ___ Bruder? (ein)", "einen") == "Hast du einen Bruder?"
