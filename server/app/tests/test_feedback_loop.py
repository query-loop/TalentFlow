from app.agents.feedback_loop import FeedbackLoop, FeedbackStore, Ranker


def test_feedback_store_memory_and_ranker_update():
    store = FeedbackStore(client=None)
    ranker = Ranker()
    fb = FeedbackLoop(store=store, ranker=ranker, embed_model=None)

    profile = {"raw_text": "Skilled in Python and AWS.", "skills": ["Python", "AWS"], "name": "X"}
    job = {"text": "Looking for Python AWS engineer", "keywords": ["Python", "AWS"]}

    before = fb.score_with_ranker(profile, job)["probability"]
    # positive feedback
    fb.record_feedback(profile, job, label=1)
    after = fb.score_with_ranker(profile, job)["probability"]
    assert after >= before
