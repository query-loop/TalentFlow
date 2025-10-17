from app.agents.scorer import score_profile


def test_scorer_basic():
    profile = {
        "raw_text": "Experienced Python developer with AWS and SQL. Contact: a@b.com",
        "skills": ["Python", "AWS", "SQL"],
        "name": "A Dev",
        "email": "a@b.com",
    }
    job = {
        "text": "Looking for a Python engineer with AWS experience and SQL skills.",
        "keywords": ["Python", "AWS", "SQL", "Docker"]
    }

    res = score_profile(profile, job, embed_model=None)
    assert 0.0 <= res["embedding"] <= 1.0
    assert 0.0 <= res["keyword_coverage"] <= 1.0
    assert 0.0 <= res["ats"] <= 1.0
    assert 0.0 <= res["aggregate"] <= 1.0
    # keyword coverage should be fairly high because profile contains 3 of 4 keywords
    assert res["keyword_coverage"] >= 0.7
