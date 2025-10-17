from app.agents.ats_formatter import format_txt, format_docx


def test_ats_formatter_txt_and_docx():
    profile = {
        "name": "Test Name",
        "summary": "A short summary.",
        "skills": ["Python", "SQL"],
        "education": ["B.S. Something"]
    }
    bullets = ["- Improved performance by 20%", "- Led a team of 3"]

    txt = format_txt(profile, bullets)
    assert "Test Name" in txt
    assert "Improved performance" in txt

    docx_bytes = format_docx(profile, bullets)
    assert isinstance(docx_bytes, (bytes, bytearray))
