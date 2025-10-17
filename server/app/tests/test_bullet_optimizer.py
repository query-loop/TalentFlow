from app.agents.bullet_optimizer import optimize_experience_bullets


def test_bullet_optimizer_fallback():
    texts = [
        "Led a migration that reduced costs by 25% and improved reliability. Also coordinated a team of 4.",
        "Implemented feature X that processed 1M requests per day." ,
    ]
    bullets = optimize_experience_bullets(texts, llm=None)
    assert isinstance(bullets, list)
    assert any("25%" in b or "reduced costs" in b for b in bullets)
    assert any("1M" in b or "1M requests" in b or "requests" in b for b in bullets)
