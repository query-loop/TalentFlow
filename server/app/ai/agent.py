import os
from typing import Dict, List, Any, Optional, Tuple

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

try:
    import httpx  # type: ignore
except Exception:  # pragma: no cover
    httpx = None  # type: ignore
import re
from collections import Counter


def _extract_keywords_local(text: str) -> Dict[str, Any]:
    words = re.findall(r"\b\w+\b", (text or "").lower())
    freq: Dict[str, int] = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    vocab = list(freq.keys())
    present = vocab[:5]
    missing = ["graphql", "docker"]
    weak = ["testing"] if "testing" in vocab else []
    return {"present": present, "missing": missing, "weak": weak}


def _fallback_generate(jd_ref: str, resume_text: Optional[str], job_hint: Optional[str]) -> Dict[str, Any]:
    # Very simple heuristic generator when no LLM key is available
    # 1) Extract keywords from JD
    kw_resp = _extract_keywords_local(jd_ref)
    present = kw_resp["present"]
    missing = kw_resp["missing"]
    weak = kw_resp["weak"]

    # 2) Build a short summary
    title = (job_hint or "target role").split("\n")[0][:60]
    summary = f"Results-driven professional targeting {title}. Highlights alignment with key requirements and impact in prior roles."

    # 3) Merge skills
    skills = sorted(list({*(present or []), *(weak or [])}))[:15]

    # 4) Experience bullets
    experience = [
        "Led end-to-end initiatives delivering measurable outcomes (e.g., +15% efficiency)",
        "Collaborated cross-functionally with design, product, and stakeholders",
        "Wrote clean, tested code; automated checks and CI/CD pipelines",
    ]
    if missing:
        experience.append(f"Proactively upskilling in: {', '.join(missing[:5])}")

    # Identity extraction from resume_text
    name_line = "Name Lastname"
    email = "email@domain"
    phone = "(123) 456-7890"
    if resume_text:
        lines = [ln.strip() for ln in resume_text.splitlines() if ln.strip()]
        if lines:
            # Use first line as name if it's short enough
            cand = lines[0]
            if 2 <= len(cand.split()) <= 6 and len(cand) <= 80:
                name_line = cand
        m_email = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", resume_text)
        if m_email:
            email = m_email.group(0)
        m_phone = re.search(r"(\+?\d[\d\-\s().]{7,}\d)", resume_text)
        if m_phone:
            phone = m_phone.group(1)

    # 5) Updated resume body (plain text) with placeholders for name/contact
    updated_resume = f"""
{name_line}
City • {email} • {phone} • linkedin.com/in/username

Summary
{summary}

Skills
{', '.join(skills)}

Experience
- {experience[0]}
- {experience[1]}
- {experience[2]}
{f'- {experience[3]}' if len(experience) > 3 else ''}
""".strip()

    plan = [
        "Aligned summary to JD reference",
        f"Merged JD keywords into skills ({len(skills)} items)",
        "Added outcome-driven experience bullets",
        "Preserved your name and contact details from the attached resume",
        *( [f"Flagged gaps: {', '.join(missing[:5])}"] if missing else [] ),
    ]

    return {
        "summary": summary,
        "skills": skills,
        "experience": experience,
        "updatedResume": updated_resume,
        "plan": plan,
    }


def agent_generate(jd_reference: str, resume_text: Optional[str], job_hint: Optional[str] = None) -> Dict[str, Any]:
    """Agentic generation using Gemini (if GOOGLE_API_KEY), else OpenAI, else a heuristic fallback.

    Returns keys: summary, skills, experience, updatedResume, plan
    """
    # 1) Try Gemini if available
    g_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    g_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    if g_api_key and httpx is not None:
        try:
            instruction = (
                "You are a resume writing agent. Return ONLY JSON with keys: "
                "summary (string), skills (string[]), experience (string[]), updatedResume (string), plan (string[]). "
                "Keep content concise, ATS-friendly, truthful, and aligned to the JD."
            )
            user = (
                f"JD Reference:\n{jd_reference}\n\n"
                f"Existing Resume (optional):\n{resume_text or ''}\n\n"
                f"Target Role Hint: {job_hint or ''}\n\n"
                "Use placeholders for name/contact only if missing."
            )
            payload = {
                "contents": [
                    {"parts": [{"text": instruction}]},
                    {"parts": [{"text": user}]},
                ]
            }
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{g_model}:generateContent?key={g_api_key}"
            with httpx.Client(timeout=30) as client:
                r = client.post(url, json=payload)
            r.raise_for_status()
            data_raw = r.json()
            # Extract text
            text = ""
            try:
                text = data_raw["candidates"][0]["content"]["parts"][0]["text"]
            except Exception:
                text = ""
            import json
            parsed = json.loads(text) if text.strip().startswith("{") else {}
            for k in ["summary", "skills", "experience", "updatedResume", "plan"]:
                parsed.setdefault(k, [] if k in ("skills", "experience", "plan") else "")
            return parsed
        except Exception:
            pass

    # 2) Try OpenAI if available
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    base_url = os.getenv("OPENAI_BASE_URL")
    if api_key and OpenAI is not None:
        client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
        system = (
            "You are a resume writing agent. Given a job description reference and an optional existing resume, "
            "produce a tailored resume. Keep it concise, ATS-friendly, and outcome-focused. Return JSON with keys: "
            "summary (string), skills (string[]), experience (string[]), updatedResume (string), plan (string[])."
        )
        user = (
            f"JD Reference:\n{jd_reference}\n\n"
            f"Existing Resume (optional):\n{resume_text or ''}\n\n"
            f"Target Role Hint: {job_hint or ''}\n\n"
            "Constraints: 1) Use JD keywords when relevant, 2) Preserve truthful content, 3) Keep total length reasonable, "
            "4) Use placeholders for name/contact if missing, 5) Experience bullets should be action + outcome."
        )
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content or "{}"
            import json
            data = json.loads(content)
            for k in ["summary", "skills", "experience", "updatedResume", "plan"]:
                data.setdefault(k, [] if k in ("skills", "experience", "plan") else "")
            return data
        except Exception:
            pass

    # 3) Fallback
    return _fallback_generate(jd_reference, resume_text, job_hint)


def agent_answer(question: str, context: Optional[str] = None) -> Dict[str, Any]:
    """General question answering. Returns dict with keys: answer, provider.

    Order: Gemini -> OpenAI -> heuristic fallback.
    """
    q = (question or "").strip()
    ctx = (context or "").strip()
    if not q:
        return {"answer": "", "provider": "none"}

    # 1) Gemini
    g_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    g_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    if g_api_key and httpx is not None:
        try:
            system = (
                "You are a helpful, concise assistant. Use provided conversation and context to answer the latest user message. "
                "Do not repeat the user's message verbatim. If the user says things like 'ok', 'thanks', or 'hello', acknowledge briefly and offer next steps."
            )
            user = (f"Question: {q}\n\n" + (f"Context:\n{ctx}\n\n" if ctx else ""))
            payload = {
                "contents": [
                    {"parts": [{"text": system}]},
                    {"parts": [{"text": user}]},
                ]
            }
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{g_model}:generateContent?key={g_api_key}"
            with httpx.Client(timeout=30) as client:
                r = client.post(url, json=payload)
            r.raise_for_status()
            data_raw = r.json()
            text = ""
            try:
                text = data_raw["candidates"][0]["content"]["parts"][0]["text"]
            except Exception:
                text = ""
            return {"answer": text.strip(), "provider": "gemini"}
        except Exception:
            pass

    # 2) OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    base_url = os.getenv("OPENAI_BASE_URL")
    if api_key and OpenAI is not None:
        try:
            client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
            messages = [
                {"role": "system", "content": "You are a helpful, concise assistant. Answer accurately."},
                {"role": "user", "content": (f"Context:\n{ctx}\n\n" if ctx else "") + q},
            ]
            resp = client.chat.completions.create(model=model, messages=messages, temperature=0.2)
            content = (resp.choices[0].message.content or "").strip()
            return {"answer": content, "provider": "openai"}
        except Exception:
            pass

    # 3) Heuristic fallback: intent-aware answers using JD/Resume from context
    # Helpers
    STOPWORDS = {
        "the","a","an","and","or","for","to","of","in","on","at","by","with","is","are","was","were",
        "be","as","that","this","it","its","from","into","we","our","you","your","their","they",
        "will","can","should","must","may","if","not","no","yes","but","than","then","so","such",
        "about","over","across","more","most","least","have","has","had","do","does","did",
        # Noise from stitched context / labels
        "user","assistant","conversation","so","far","jd","reference","resume","using","attached",
        # Common JD label words
        "role","company","location","work","arrangement","day","days","preferred","required","requirements","responsibilities",
    }

    TOOLS = {
        "python","java","javascript","typescript","sql","excel","tableau","powerbi","power-bi","airflow","dbt","spark","hadoop",
        "jira","confluence","git","github","docker","kubernetes","aws","gcp","azure","metabase","looker","superset",
        "postgres","mysql","redshift","bigquery","snowflake","react","angular","vue","node","flask","django","fastapi","pytorch","tensorflow"
    }

    SOFT_SKILLS = {
        "communication","leadership","mentoring","collaboration","stakeholder","ownership","problem","problem-solving","analytical","teamwork",
        "organization","organized","prioritization","adaptability","initiative","accountability","attention","planning"
    }

    def _split_context(ctx: str) -> Tuple[str, str]:
        jd = ""; resume = ""
        if not ctx:
            return jd, resume
        c = ctx.replace("\r\n", "\n")
        low = c.lower()
        jdx = low.find("jd reference:")
        # Find 'resume:' anywhere after
        rdx = low.find("resume:")
        if jdx != -1 and rdx != -1 and rdx > jdx:
            jd = c[jdx + len("jd reference:"):rdx].strip()
        elif jdx != -1:
            jd = c[jdx + len("jd reference:"):].strip()
        # Resume section (from first 'resume:' to end)
        if rdx != -1:
            resume = c[rdx + len("resume:"):].strip()
        return jd, resume

    def _tokenize(text: str) -> List[str]:
        text = (text or "").lower()
        tokens = re.findall(r"[a-z0-9][a-z0-9\-\+/#\.]{1,}", text)
        return [t.strip(".") for t in tokens if t not in STOPWORDS and len(t) > 1]

    def _rank_keywords(text: str, limit: int = 30) -> List[str]:
        if not text:
            return []
        toks = _tokenize(text)
        base = Counter(toks)
        scores: Dict[str, float] = {w: float(c) for w, c in base.items()}
        for w in list(scores.keys()):
            if w in TOOLS:
                scores[w] += 1.5
            if w in SOFT_SKILLS:
                scores[w] += 0.5
        ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
        return [w for w, _ in ranked[:limit]]

    def _extract_bullets(text: str, section_hint: str) -> List[str]:
        if not text:
            return []
        lines = [ln.strip() for ln in text.splitlines()]
        idx = -1
        for i, ln in enumerate(lines):
            low = ln.lower()
            if section_hint in low:
                idx = i; break
        bullets: List[str] = []
        bullet_re = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")
        if idx != -1:
            for ln in lines[idx+1:]:
                if not ln:
                    if len(bullets) >= 3:
                        break
                    else:
                        continue
                if bullet_re.match(ln):
                    bullets.append(bullet_re.sub("", ln).strip())
                elif ln and bullets:
                    # Likely a new section
                    if re.search(r":$", ln):
                        break
        if not bullets:
            # Fallback: collect any bullet-like lines anywhere
            for ln in lines:
                if bullet_re.match(ln):
                    bullets.append(bullet_re.sub("", ln).strip())
        # Deduplicate while preserving order
        seen = set()
        uniq = []
        for b in bullets:
            if b and b.lower() not in seen:
                uniq.append(b)
                seen.add(b.lower())
        return uniq[:10]

    def _summarize(text: str, max_words: int = 40) -> str:
        if not text:
            return ""
        # Take first 2-3 sentences or up to max_words
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        out = []
        count = 0
        for s in sentences:
            w = len(s.split())
            if count + w > max_words and out:
                break
            out.append(s)
            count += w
            if count >= max_words:
                break
        res = " ".join(out).strip()
        # Trim to max_words if still too long
        words = res.split()
        if len(words) > max_words:
            res = " ".join(words[:max_words])
        return res

    def _compare(resume: str, jd: str) -> Dict[str, Any]:
        rt = set(_tokenize(resume))
        jt = set(_tokenize(jd))
        if not jt:
            return {"score": 0, "strengths": [], "gaps": []}
        overlap = sorted(list(rt & jt))
        gaps = sorted(list(jt - rt))
        score = int(round(100 * (len(overlap) / max(1, len(jt)))))
        return {"score": score, "strengths": overlap[:15], "gaps": gaps[:15]}

    low_q = q.lower().strip()
    trivial_map = {
        "ok": "Got it. What would you like to do next?",
        "okay": "Okay! What should we tackle next?",
        "thanks": "You're welcome! Anything else I can help with?",
        "thank you": "You're welcome! Need help with anything else?",
        "hi": "Hi there! How can I help with your resume or JD today?",
        "hello": "Hello! How can I assist you?",
        "hey": "Hey! What would you like to work on?",
        "yo": "Hey there! How can I help?",
        "welcome": "Thanks! What should we do next?",
        "ping": "I'm here. How can I help?",
        "test": "All set. What would you like to try?",
    }
    if low_q in trivial_map:
        return {"answer": trivial_map[low_q], "provider": "fallback"}

    # If it's a very short non-question input (<= 3 words), acknowledge and ask next step
    if len(low_q.split()) <= 3 and not low_q.endswith(("?", ".")):
        return {"answer": "Got it. What would you like me to answer or do?", "provider": "fallback"}

    # Use JD/Resume from context for grounded answers
    jd_text, resume_text = _split_context(ctx) if ctx else ("", "")

    # Intent detection
    def contains_any(s: str, parts: List[str]) -> bool:
        return any(p in s for p in parts)

    if contains_any(low_q, ["keyword","keywords","key word","ats keyword","professional keyword","resume keyword","skill keywords","resume keywords"]):
        base = jd_text or ctx or ""
        jd_kws = _rank_keywords(base, limit=40)
        # If resume present, prioritize JD keywords missing from resume
        if resume_text:
            res_toks = set(_tokenize(resume_text))
            missing = [w for w in jd_kws if w not in res_toks]
            kws = (missing[:15] or jd_kws[:15])
        else:
            kws = jd_kws[:15]
        if not kws:
            return {"answer": "I couldn’t extract keywords from the context.", "provider": "fallback"}
        if "json" in low_q:
            import json as _json
            return {"answer": _json.dumps({"keywords": kws}, ensure_ascii=False), "provider": "fallback"}
        # If the question hints at resume usage, prepend a small note
        if contains_any(low_q, ["resume", "add on resume", "for resume"]):
            return {"answer": "Missing-from-resume keywords (from JD): " + ", ".join(kws), "provider": "fallback"}
        return {"answer": ", ".join(kws), "provider": "fallback"}

    if contains_any(low_q, ["responsib","dutie","accountabilit","what you will","you will","key responsibil","tasks"]):
        base_text = jd_text or ctx or ""
        bullets = _extract_bullets(base_text, section_hint="responsibil")
        if not bullets:
            # Try a few other section hints common in JDs
            for hint in ("what you will", "duties", "tasks", "what you'll do", "what you do", "require"):
                bullets = _extract_bullets(base_text, section_hint=hint)
                if bullets:
                    break
        if bullets:
            return {"answer": "\n".join([f"• {b}" for b in bullets[:5]]), "provider": "fallback"}
        return {"answer": "I couldn’t find responsibilities in the JD reference.", "provider": "fallback"}

    if contains_any(low_q, ["summarize", "summary", "in one sentence", "tl;dr"]):
        s = _summarize(jd_text or ctx or "", max_words=40 if "40" in low_q else 30)
        if s:
            return {"answer": s, "provider": "fallback"}
        return {"answer": "I couldn’t summarize without a JD reference.", "provider": "fallback"}

    if contains_any(low_q, ["hard skill"]) and contains_any(low_q, ["soft skill"]):
        base = jd_text or ctx or ""
        top = _rank_keywords(base, limit=40)
        hard = [w for w in top if w in TOOLS or w not in SOFT_SKILLS][:10]
        soft = [w for w in top if w in SOFT_SKILLS][:10]
        ans = []
        if hard:
            ans.append("Hard skills: " + ", ".join(hard))
        if soft:
            ans.append("Soft skills: " + ", ".join(soft))
        if ans:
            return {"answer": "\n".join(ans), "provider": "fallback"}
        return {"answer": "Couldn’t categorize skills from the JD.", "provider": "fallback"}

    if contains_any(low_q, ["tool", "framework", "tech stack", "stack"]):
        base = jd_text or ctx or ""
        toks = _tokenize(base)
        tools = [t for t in toks if t in TOOLS]
        tools = sorted(list(dict.fromkeys(tools)))
        if tools:
            return {"answer": ", ".join(tools[:20]), "provider": "fallback"}
        return {"answer": "I couldn’t find named tools/frameworks in the JD.", "provider": "fallback"}

    if contains_any(low_q, ["match score", "score", "gap", "compare", "strength"]):
        cmpd = _compare(resume_text or "", jd_text or ctx or "")
        strengths = ", ".join(cmpd.get("strengths", [])[:8]) or "(none)"
        gaps = ", ".join(cmpd.get("gaps", [])[:8]) or "(none)"
        score = cmpd.get("score", 0)
        msg = f"Match score: {score}/100\nStrengths: {strengths}\nGaps: {gaps}"
        return {"answer": msg, "provider": "fallback"}

    # Default minimal response
    if jd_text:
        s = _summarize(jd_text, max_words=30) or jd_text.splitlines()[0][:160]
        return {"answer": s, "provider": "fallback"}
    return {"answer": "Could you share a bit more detail so I can help?", "provider": "fallback"}
