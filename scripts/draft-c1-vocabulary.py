#!/usr/bin/env python3
"""Reproduce quarantined C1 review drafts; never imports into the application.

Build-only dependencies: wordfreq==3.1.1 and simplemma==1.1.2. See data/c1/README.md.
Download the four pinned/checksummed WikDict TEI files into --sources first.
"""

import argparse
import csv
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from simplemma import lemmatize
from wordfreq import zipf_frequency

ROOT = Path(__file__).resolve().parents[1]
NS = {"t": "http://www.tei-c.org/ns/1.0"}
LANGS = {"de": "deu", "en": "eng", "fr": "fra", "it": "ita"}
FIELDS = [
    "language",
    "rank",
    "lemma",
    "pos",
    "translation_cs",
    "ipa",
    "cefr",
    "gender",
    "example",
    "source",
    "license",
    "revision",
    "content_flags",
]
POS = {"n": "NOUN", "v": "VERB", "adj": "ADJ", "adv": "ADV"}
# Confirmed bad source entries and surface forms/US variants; not general C1 vocabulary.
EXCLUDE = {
    "en": {
        "are",
        "st",
        "cannot",
        "percent",
        "pro",
        "center",
        "defense",
        "organization",
        "color",
        "favorite",
        "honor",
        "neighbor",
        "analyze",
        "trump",
        "smith",
    },
    "de": {
        "Berlin",
        "München",
        "Bayern",
        "Hamburg",
        "Wien",
        "Frankfurt",
        "Peter",
        "Köln",
        "Aller",
        "Seine",
    },
    "fr": {"y", "anti", "totale", "grosse", "donné", "macron"},
    "it": {
        "mettersi",
        "salvatore",
        "trovato",
        "vissuto",
        "farsi",
        "occuparsi",
        "unirsi",
        "trovarsi",
        "vinto",
        "portato",
        "giuliano",
        "mo",
        "fu",
        "fa",
    },
}
SENSITIVE = re.compile(
    r"\b(?:vulgar|vulgär|vulgaire|volgare|offensive|pejorative|derogatory|sexual|sexuell|sexuel|sessuale|porn|profanity|slur|penis|vagina|fuck|shit|cunt|nigger|rape|murder|suicide|kill|weapon|gun|bomb|assassin|meurtre|tuer|uccidere|Mord|Waffe|töten|hovno|prdel|píča|čurák|kurva|soulož|znásilnění|vražda|sebevražda|zbraň)\b",
    re.IGNORECASE,
)
PROPER = re.compile(
    r"\b(?:surname|given name|proper noun|Eigenname|Vorname|Familienname|cognome|toponyme|patronyme)\b",
    re.IGNORECASE,
)


def existing(language):
    out = set()
    for path in (ROOT / "backend/data/lexicon").glob(f"{language}.*.csv"):
        with path.open(encoding="utf-8") as handle:
            out.update(
                r["lemma"].casefold()
                for r in csv.DictReader(x for x in handle if not x.startswith("#"))
            )
    return out


def candidates(path, language):
    seen = existing(language)
    out = {}
    for entry in ET.parse(path).findall(".//t:entry", NS):
        lemma = entry.findtext("t:form/t:orth", namespaces=NS) or ""
        pos = POS.get(entry.findtext("t:gramGrp/t:pos", namespaces=NS))
        if (
            not pos
            or not lemma.isalpha()
            or lemma.casefold() in seen
            or lemma in EXCLUDE[language]
        ):
            continue
        if language != "de" and not lemma.islower():
            continue
        if lemmatize(lemma, lang=language).casefold() != lemma.casefold():
            continue
        text = " ".join(entry.itertext())
        if SENSITIVE.search(text) or PROPER.search(text):
            continue
        gender = entry.findtext("t:gramGrp/t:gen", namespaces=NS)
        gender = (
            {"masc": "der", "fem": "die", "neut": "das"}
            if language == "de"
            else {"masc": "m", "fem": "f"}
        ).get(gender, "")
        if pos == "NOUN" and language != "en" and not gender:
            continue
        glosses = [
            q.text.strip()
            for q in entry.findall("t:sense/t:cit[@type='trans']/t:quote", NS)
            if q.text and q.text.strip()
        ]
        if not glosses:
            continue
        gloss = "; ".join(dict.fromkeys(glosses))
        if len(gloss) > 200:
            gloss = glosses[0]
        if len(gloss) > 200:
            continue
        score = zipf_frequency(lemma, language)
        if score <= 0:
            continue
        out.setdefault(
            lemma.casefold(),
            {
                "lemma": lemma,
                "pos": pos,
                "gender": gender if pos == "NOUN" else "",
                "translation_cs": gloss,
                "score": score,
            },
        )
    return sorted(out.values(), key=lambda r: (-r["score"], r["lemma"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, required=True)
    args = parser.parse_args()
    dest = ROOT / "backend/data/c1"
    manifest_path = dest / "sources.json"
    manifest = json.loads(manifest_path.read_text())
    review = {}
    for language, iso in LANGS.items():
        path = args.sources / f"wd-{iso}.tei"
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != manifest[language]["sha256"]:
            raise ValueError(f"{language}: source checksum mismatch")
        rows = candidates(path, language)
        if len(rows) < 3000:
            raise ValueError(
                f"{language}: only {len(rows)} candidates; do not fabricate fillers"
            )
        with (dest / f"{language}.5001-8000.csv").open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            handle.write(
                "# UNREVIEWED candidates; approximate teaching order, not certified CEFR or current corpus ranks.\n"
            )
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            for rank, row in enumerate(rows[:3000], 5001):
                writer.writerow(
                    {
                        "language": language,
                        "rank": rank,
                        "lemma": row["lemma"],
                        "pos": row["pos"],
                        "translation_cs": row["translation_cs"],
                        "gender": row["gender"],
                        "cefr": "C1",
                        "source": "wikdict-wordfreq-unreviewed",
                        "license": "CC-BY-SA-4.0",
                        "revision": "c1-candidates-v1",
                    }
                )
        base = []
        for base_path in (ROOT / "backend/data/lexicon").glob(f"{language}.*.csv"):
            with base_path.open(encoding="utf-8") as base_file:
                base.extend(
                    csv.DictReader(x for x in base_file if not x.startswith("#"))
                )
        counts = Counter(r["translation_cs"] for r in [*base, *rows[:3000]])
        ambiguities = [
            {"lemma": r["lemma"], "translation_cs": r["translation_cs"], "rank": rank}
            for rank, r in enumerate(rows[:3000], 5001)
            if counts[r["translation_cs"]] > 1
        ]
        review[language] = {
            "candidate_count": 3000,
            "ambiguous_gloss_count": len(ambiguities),
            "ambiguous_glosses": ambiguities,
        }
        print(f"{language}: 3000 review candidates; lowest Zipf {rows[2999]['score']}")
    (dest / "review-ambiguities.json").write_text(
        json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
