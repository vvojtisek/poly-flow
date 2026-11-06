"""CEFR diagnostic: item banks and the adaptive model (no database)."""

import json
import random
from collections import Counter
from pathlib import Path

import pytest

from app.domain import diagnostic as d
from app.domain.enums import CefrLevel, Language

DATA = Path(__file__).resolve().parents[1] / "data" / "diagnostic"


def load(lang: str) -> d.ItemBank:
    return d.ItemBank.model_validate(json.loads((DATA / f"{lang}.diagnostic.json").read_text()))


@pytest.mark.parametrize("lang", [x.value for x in Language])
def test_every_language_has_a_valid_bank_covering_all_bands_and_skills(lang):
    bank = load(lang)
    assert bank.language == lang and bank.review_status == "unreviewed"
    per_band = Counter(i.level for i in bank.items)
    assert all(per_band[b] >= d.MIN_ITEMS_PER_BAND for b in d.BANDS)
    skills = Counter(i.skill for i in bank.items)
    assert set(skills) == set(d.Skill)
    # B1 and above test idioms; every band has listening and reading.
    for b in d.BANDS:
        band_skills = {i.skill for i in bank.items if i.level == b}
        assert {d.Skill.READING, d.Skill.LISTENING} <= band_skills
    assert all(i.id.startswith(f"{lang}-") for i in bank.items)


def test_bank_rejects_an_answer_outside_the_options():
    with pytest.raises(ValueError, match="answer"):
        d.Item.model_validate(
            {
                "id": "x-1",
                "level": "A1",
                "skill": "grammar",
                "prompt": "a ___",
                "options": ["a", "b", "c"],
                "answer": "z",
                "explain": "e",
            }
        )


def test_listening_needs_audio_and_reading_needs_context():
    base = {"id": "x", "level": "A1", "prompt": "q", "options": ["a", "b", "c"], "answer": "a"}
    with pytest.raises(ValueError, match="audio"):
        d.Item.model_validate({**base, "skill": "listening", "explain": "e"})
    with pytest.raises(ValueError, match="context"):
        d.Item.model_validate({**base, "skill": "reading", "explain": "e"})


def test_band_labels_never_claim_c1():
    assert d.band_label(CefrLevel.C1) == "B2+"
    assert d.band_label(None) == "pre-A1"


def simulate(true_theta: float, rng: random.Random, prior: float = -1.0):
    bank = load("de")
    answered: list[tuple[d.Item, bool]] = []
    left = list(bank.items)
    trail = []
    while True:
        post = d.posterior([(i.difficulty, c) for i, c in answered], prior)
        if d.is_finished(post, len(answered), len(left)):
            break
        item = d.choose_item(left, [i.skill for i, _ in answered], post.mean, rng)
        left.remove(item)
        trail.append(item.level)
        answered.append((item, rng.random() < d.p_correct(true_theta, item.difficulty)))
    return d.result(answered, prior), trail


@pytest.mark.parametrize(
    ("theta", "band"),
    [(-1.14, CefrLevel.A1), (-0.14, CefrLevel.A2), (0.86, CefrLevel.B1), (1.86, CefrLevel.B2)],
)
def test_simulated_learners_land_in_or_next_to_their_band(theta, band):
    rng = random.Random(7)
    results = [simulate(theta, rng)[0] for _ in range(60)]
    exact = sum(r.level == band for r in results) / len(results)
    order = [None, *d.BANDS]
    adjacent = sum(abs(order.index(r.level) - order.index(band)) <= 1 for r in results)
    assert exact >= 0.6, exact
    assert adjacent == len(results)


def test_a_strong_learner_escalates_into_b1_and_b2_within_four_questions():
    rng = random.Random(3)
    _, trail = simulate(3.0, rng)
    assert any(level in (CefrLevel.B2, CefrLevel.C1) for level in trail[:4]), trail


def test_a_beginner_is_never_asked_b2_material_after_struggling():
    rng = random.Random(5)
    for _ in range(20):
        res, trail = simulate(-3.0, rng)
        assert CefrLevel.C1 not in trail[3:]
        assert res.level is None


def test_skills_rotate_between_equally_informative_items():
    bank = load("de")
    a2 = [i for i in bank.items if i.level == CefrLevel.A2]
    rng = random.Random(1)
    picked = d.choose_item(a2, [d.Skill.GRAMMAR, d.Skill.GRAMMAR], -1.0, rng)
    assert picked.skill != d.Skill.GRAMMAR


def test_vocabulary_result_moves_the_starting_point():
    assert d.prior_mean_from_vocabulary(None) == d.DIAGNOSTIC.default_prior_mean
    assert d.prior_mean_from_vocabulary(1000) > d.prior_mean_from_vocabulary(100)
    assert d.prior_mean_from_vocabulary(10**6) <= 1.0


def test_skill_report_flags_strengths_and_weaknesses_against_the_estimate():
    r = d.SkillReport(d.Skill.LISTENING, asked=4, correct=0, expected=2.5)
    assert r.verdict == "weak"
    assert d.SkillReport(d.Skill.READING, asked=1, correct=1, expected=0.2).verdict == "few"


def test_band_at_most():
    assert d.band_at_most(CefrLevel.A2, CefrLevel.B1)
    assert not d.band_at_most(CefrLevel.B2, CefrLevel.B1)
    assert not d.band_at_most(CefrLevel.A1, None)
    assert d.band_at_most(CefrLevel.B2, CefrLevel.C1)
