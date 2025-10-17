from app.agents.skill_normalizer import normalize_skills


def test_normalize_simple():
    skills = ["python", "aws", "proj management", "unknownskill"]
    normalized = normalize_skills(skills, model_name=None)
    # Expect canonical matches for known skills and None for unknown
    mapping = {n["input"]: n for n in normalized}
    assert mapping["python"]["canonical"] in ("Python",)
    assert mapping["aws"]["canonical"] in ("AWS",)
    # project management fuzzy match
    assert mapping["proj management"]["canonical"] in ("Project Management",)
    assert mapping["unknownskill"]["canonical"] is None
