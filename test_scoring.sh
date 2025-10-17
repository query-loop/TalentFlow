#!/bin/bash

# Test Resume Scoring API

echo "🧪 Testing Resume Scoring API"
echo "==============================="
echo ""

# Test 1: Health Check
echo "1️⃣ Health Check:"
curl -s http://localhost:9002/api/scoring/health | jq '.'
echo ""
echo ""

# Test 2: Sample Scoring Request
echo "2️⃣ Sample Scoring Request:"

SAMPLE_JD="Senior Backend Engineer

Requirements:
• 5+ years of experience in backend development
• Strong proficiency in Python
• Experience with FastAPI or Django
• Knowledge of Docker and Kubernetes
• AWS experience required
• Strong problem-solving skills"

SAMPLE_RESUME="John Doe
Senior Software Engineer

6 years of experience building scalable web applications.
Expert in Python, FastAPI, and Django frameworks.
Proficient with Docker, Kubernetes, and AWS cloud services.
Strong analytical and problem-solving abilities."

curl -s -X POST http://localhost:9002/api/scoring/score \
  -H "Content-Type: application/json" \
  -d "{
    \"jd_text\": \"$SAMPLE_JD\",
    \"resume_text\": \"$SAMPLE_RESUME\",
    \"jd_title\": \"Senior Backend Engineer\"
  }" | jq '{
    overall_score: .overall_score,
    skills_score: .skills_score,
    keywords_score: .keywords_score,
    experience_score: .experience_score,
    matched_skills: .matched_skills,
    missing_skills: .missing_skills[0:3],
    recommendations: .recommendations[0:2]
  }'

echo ""
echo ""
echo "✅ Test Complete!"
echo ""
echo "📝 Next Steps:"
echo "1. Open http://localhost:5174/app/pipelines-v2"
echo "2. Click 'New pipeline'"
echo "3. Click 'Use Sample Data for Testing'"
echo "4. Click 'Create Pipeline'"
echo "5. View the automatic scoring results!"
