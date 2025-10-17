from app.agents.parser_agent import extract_profile_from_text


def test_extract_profile_simple():
    text = """
John Doe
john.doe@example.com
+1 555-123-4567

Skills: Python, SQL, AWS

Professional Summary
Experienced software engineer with 5 years of experience.
"""

    parsed = extract_profile_from_text(text)
    assert parsed["name"] == "John Doe"
    assert parsed["email"] == "john.doe@example.com"
    assert "+1" in parsed["phone"] or "555" in parsed["phone"]
    assert "Python" in parsed["skills"]
    assert parsed["raw_text"] == text
