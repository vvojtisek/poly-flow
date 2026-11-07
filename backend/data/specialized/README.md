# Specialist interest vocabulary — starter drafts

70 concepts, adapted across DE/EN/FR/IT (280 topic entries), cover figure skating,
dance, gymnastics, ice hockey, field sports (football/rugby), nature, mathematics,
chemistry, biology, physics, history, woodworking, criminology and contemporary
colloquial speech. Sports are available to every profile; there is no gender gate.

`topics.json` groups the adaptations by the same interest slugs used in profile
settings. Each entry includes a Czech domain-specific gloss, language lemma, POS,
rank reference, content flags and `review_status: unreviewed`. A word can have a
specialist sense different from its general dictionary meaning. The manifest
preserves that sense without overwriting the existing lexicon gloss.

The four CSV files use the existing LexiconRow schema and contain only genuinely
new lemmas (221 in total); other topic entries reuse keys/ranks from the base or
C1 candidate files. New specialist ranks start at 8001 per language and mean
**teaching order only**, not general frequency or CEFR. Specialist vocabulary can
be useful at any proficiency level. These files are outside the default seed glob.

Source: Codex-drafted on 2026-11-07, unreviewed; CC0-1.0
(https://creativecommons.org/publicdomain/zero/1.0/). Human and subject-matter
review is required, particularly skating terminology and forensic/legal
jurisdiction differences. Slang is a modest, neutral starter selection of current
colloquial usages, not a measured 2026 street corpus; regional and age-group usage
varies. English uses British terminology (`mate`); French `pote`/`kiffer`, German
`Kumpel`/`feiern` and Italian `spacca` are register-marked in the Czech glosses.

Criminology is conservatively withheld from child profiles in this starter pack
through `violence` content flags. It contains vocabulary, not instructions for
committing crimes. The CSV only introduces newly added entries; references to
existing words do not change those words' global safety flags. Any future topic
serving code must also enforce each manifest entry's flags, rather than relying
only on the global word flags. This PR does not expose a new learner API or
silently enable unreviewed topic teaching. Interest selection continues to supply
topics to the existing daily story generator.

Review C1 and specialist sources together before import (some terms reference
C1 candidates), then use `python -m app.cli seed-lexicon data/specialized/*.csv
--dry-run` from `backend/`. Reviewed imports use the same command without
`--dry-run`. Check for occupied extension ranks first. Existing learner progress
is preserved by the established upsert path. Topic-based lesson selection and
one-click collection creation remain future work; no collections are created for
users by importing these files.
