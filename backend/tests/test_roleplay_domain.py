from app.domain.roleplay import Line, options, plain, playable, speakers

LINES = [
    Line("Anna", "Hallo! Ich heiße Anna. Wie heißt du?", "Ahoj! Jmenuju se Anna."),
    Line("Tom", "Hallo, Anna! Ich bin Tom.", "Ahoj, Anno! Já jsem Tom."),
    Line("Anna", "Bist du acht, Tom?", "Je ti osm, Tome?"),
    Line("Tom", "Nein, ich bin neun. Und du?", "Ne, je mi devět. A tobě?"),
]
OTHER = ["Ich habe einen Hund.", "Wo ist die Schule?", "Das Brot ist frisch.", "Danke schön!"]


def test_plain_joins_segments():
    line = {"speaker": "Tom", "cs": "x", "segments": [{"t": "Ich "}, {"t": "bin", "item": "1"}]}
    assert plain(line) == Line("Tom", "Ich bin", "x")


def test_speakers_and_playable():
    assert speakers(LINES) == ["Anna", "Tom"]
    assert playable(LINES)
    assert not playable([Line("Anna", "Hallo", "Ahoj")])
    assert not playable([*LINES, Line(None, "Erzähler", "x")])


def test_options_are_distinct_and_stable():
    a = options(LINES, 1, OTHER, "scene:Tom")
    b = options(LINES, 1, OTHER, "scene:Tom")
    assert a == b
    choices, right = a
    assert len(choices) == 3 and len({c.lower() for c in choices}) == 3
    assert choices[right] == LINES[1].text
    # one distractor comes from the same scene, one from elsewhere
    assert sum(c in {ln.text for ln in LINES} for c in choices) == 2
    assert sum(c in OTHER for c in choices) == 1


def test_options_with_small_pools():
    choices, right = options(LINES[:2], 0, [], "s")
    assert choices[right] == LINES[0].text and len(choices) == 2
