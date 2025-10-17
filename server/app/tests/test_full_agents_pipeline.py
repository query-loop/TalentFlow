import tempfile
import os
from app.agents.parser_agent import extract_profile_from_text
from app.agents.skill_normalizer import normalize_skills
from app.agents.embedder import embed_texts
from app.agents.retriever import retrieve
from app.agents.resume_generator import generate_resume
from app.agents.bullet_optimizer import optimize_experience_bullets
from app.agents.ats_formatter import format_txt, format_docx
from app.agents.scorer import score_profile
from app.agents.feedback_loop import FeedbackLoop, FeedbackStore, Ranker
from app import ingest
from app.chroma_client import ChromaClient


def test_full_pipeline_happy_path():
    # Simulate user uploads resume text and a JD
    resume_text = """
John Doe
john@example.com
Experienced backend engineer. Built microservices and scaling systems. Led a migration that reduced costs by 20%.
Skills: Python, AWS, Docker
"""
    jd_text = "Seeking backend engineer with Python and AWS experience to reduce costs and improve scalability."

    # Parser
    profile = extract_profile_from_text(resume_text)

    # Normalize skills
    normalized = normalize_skills(profile.get("skills", []), model_name=None)
    profile["normalized_skills"] = normalized

    # Ingest resume into chroma fake
    c = ChromaClient(collection_name="full_pipeline_test").get_collection()
    count = ingest.ingest_candidate("cand1", resume_text, metadata={"source": "upload"}, collection=c)
    assert count > 0

    # Retrieve context
    hits = retrieve("backend engineer AWS", top_k=2, collection=c, embed_model=None)
    assert "documents" in hits

    # Generate resume (template fallback)
    out = generate_resume(profile, query=None, top_k=2, embed_model=None, llm=None, collection=c)
    assert "John Doe" in out or profile.get("name") in out

    # Optimize bullets
    bullets = optimize_experience_bullets([out], llm=None)
    assert isinstance(bullets, list) and len(bullets) >= 1

    # Format
    txt, docx = format_txt(profile, bullets), format_docx(profile, bullets)
    assert isinstance(txt, str)
    assert isinstance(docx, (bytes, bytearray))

    # Score against JD
    job = {"text": jd_text, "keywords": ["Python", "AWS", "scalability"]}
    score = score_profile(profile, job, embed_model=None)
    assert "aggregate" in score

    # Feedback loop: positive feedback
    fb = FeedbackLoop(store=FeedbackStore(client=None), ranker=Ranker(), embed_model=None)
    key = fb.record_feedback(profile, job, label=1)
    assert key is not None


def test_empty_resume_handling():
    profile = extract_profile_from_text("")
    assert profile["raw_text"] == ""
    # generating resume should not crash
    out = generate_resume(profile, collection=ChromaClient().get_collection())
    assert isinstance(out, str)


def test_jd_with_no_keywords():
    resume_text = "Alice\nSkills: Python, Data Analysis\nExperience: did data stuff"
    profile = extract_profile_from_text(resume_text)
    job = {"text": "General role", "keywords": []}
    sc = score_profile(profile, job)
    assert "aggregate" in sc


def test_large_resume_chunking_and_retrieval():
    long_text = "Word " * 5000 + " Python AWS"
    c = ChromaClient(collection_name="large_test").get_collection()
    count = ingest.ingest_candidate("big1", long_text, collection=c)
    assert count > 0
    hits = retrieve("Python", collection=c)
    assert "documents" in hits


def test_ambiguous_skills_normalization():
    profile = extract_profile_from_text("Bob\nSkills: ML, Machine Learning, ml")
    norm = normalize_skills(profile.get("skills", []), model_name=None)
    assert isinstance(norm, list)


def test_negative_feedback_updates_ranker():
    profile = {"raw_text": "C dev with Java", "skills": ["C", "Java"], "name": "CDev"}
    job = {"text": "Looking for Python dev", "keywords": ["Python"]}
    fb = FeedbackLoop(store=FeedbackStore(client=None), ranker=Ranker(), embed_model=None)
    before = fb.score_with_ranker(profile, job)["probability"]
    fb.record_feedback(profile, job, label=0)
    after = fb.score_with_ranker(profile, job)["probability"]
    # after negative feedback, probability should not increase
    assert after <= before or abs(after - before) < 1e-6


def test_ingest_from_file_reference():
    # write temp resume and ingest via file:// reference
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tf:
        tf.write("Zoe\nSkills: SQL\nExperience: optimized DB queries")
        path = tf.name
    try:
        c = ChromaClient(collection_name="ref_test").get_collection()
        cnt = ingest.ingest_from_reference("ref_cand", f"file://{path}", collection=c)
        assert cnt > 0
    finally:
        os.unlink(path)
