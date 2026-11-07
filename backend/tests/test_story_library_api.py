"""The checked-in reading library is available through the authenticated reader API."""

from tests.helpers import csrf, setup_parent


async def test_story_library_is_indexed_filtered_and_server_graded(db, client):
    me = await setup_parent(client)
    response = await client.get("/api/v1/story-library?language=de", headers=csrf(me))
    assert response.status_code == 200
    stories = response.json()
    assert len(stories) == 90
    assert {
        level: sum(story["level"] == level for story in stories)
        for level in ("A1", "A2", "B1", "B2")
    } == {
        "A1": 15,
        "A2": 20,
        "B1": 25,
        "B2": 30,
    }

    selected = next(story for story in stories if story["level"] == "A1")
    detail = await client.get(
        f"/api/v1/story-library/{selected['slug']}?language=de", headers=csrf(me)
    )
    assert detail.status_code == 200
    story = detail.json()
    assert story["review_status"] == "unreviewed"
    assert len(story["lines"]) >= 6 and len(story["questions"]) >= 2
    assert all("answer_index" not in question for question in story["questions"])

    results = []
    for choice in range(len(story["questions"][0]["options"])):
        graded = await client.post(
            f"/api/v1/story-library/{selected['slug']}/answer?language=de",
            headers=csrf(me),
            json={"question": 0, "choice": choice},
        )
        assert graded.status_code == 200
        results.append(graded.json())
    assert sum(result["correct"] for result in results) == 1
    assert all(result["answer"] == results[0]["answer"] for result in results)
    typed_results = []
    for option in story["questions"][0]["options"]:
        typed = await client.post(
            f"/api/v1/story-library/{selected['slug']}/answer?language=de",
            headers=csrf(me),
            json={"question": 0, "text": option},
        )
        assert typed.status_code == 200
        typed_results.append(typed.json())
    assert sum(result["correct"] for result in typed_results) == 1

    filtered = await client.get("/api/v1/story-library?language=de&level=A2", headers=csrf(me))
    assert filtered.status_code == 200 and len(filtered.json()) == 20
