# Seed-data instructions

Read the repository and backend `AGENTS.md` files, then read `README.md` in this directory before editing seed data.

- Preserve the documented CSV columns, UTF-8 encoding, comment behavior, idempotent import keys, and rank uniqueness per language.
- Do not invent frequency ranks, IPA, CEFR tags, gender, examples, or Czech glosses and mark them as verified. Record source and license/reuse terms in the dataset documentation.
- Validate all changed CSVs with the CLI's `--dry-run` before relying on an import. Review rank shifts against items already in the database; preserve learner progress.
- Child safety blacklist edits need representative tests for whole-word keywords, regex behavior, diacritics, and false positives. A blacklist is one layer in content review, not a complete safety guarantee.
- Keep small committed sample files suitable for pipeline tests; do not silently replace them with unreviewed full corpora.

