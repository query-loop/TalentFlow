# TalentFlow Logs Documentation

This directory contains comprehensive logs for all pipeline executions, accuracy metrics, and performance analytics.

## Log File Structure

### 1. Pipeline Execution Logs
**Filename**: `{pipeline_id}_pipeline.json`

Complete log of the entire pipeline execution including:
- `pipeline_id`: Unique pipeline identifier
- `timestamp`: When the pipeline completed
- `total_duration_seconds`: Total execution time
- `steps_completed` / `steps_failed`: Step execution summary
- `step_metrics`: Detailed metrics for each step:
  - `duration_seconds`: Individual step execution time
  - `completed_at`: Timestamp when step completed
  - `status`: "success" or "failed"
  - `error`: Error message (if failed)
- `artifacts_summary`: High-level summary of generated artifacts
  - `ats_score`: Final ATS aggregate score (0-1)
  - `accuracy_metrics`: 
    - `precision`: Keyword match precision (0-1)
    - `recall`: Keyword match recall (0-1)
    - `f1_score`: F1 score combining precision and recall
  - `bias_score`: Potential bias detection score (0-1)
- `log_entries`: Sequential log messages from pipeline execution

### 2. JD (Job Description) Extraction Logs
**Filename**: `{pipeline_id}_jd_extraction.json`

Logs from JD extraction/retry operations:
- `operation`: Type of operation (e.g., "jd_extraction_retry")
- `url`: Source URL of the JD
- `success`: Whether extraction was successful
- `extraction_method`: Method used ("enhanced", "manual", "worker")
- `quality_score`: Quality of extracted JD (0-1)
- `description_length`: Character count of extracted description
- `key_requirements_count`: Number of identified requirements
- `coverage_percent`: Coverage percentage of requirements (0-100)

### 3. Manual JD Processing Logs
**Filename**: `{pipeline_id}_manual_jd.json`

Logs for manually provided job descriptions:
- `operation`: "manual_jd_processing"
- `text_length`: Length of manually provided JD text
- `key_requirements_count`: Number of extracted requirements
- `coverage_percent`: Requirement coverage (0-100)

### 4. Resume Parsing Logs
**Filename**: `{candidate_id}_parsing.json`

Logs from resume parsing and ingest operations:
- `candidate_id`: Unique candidate identifier
- `operation`: "resume_parsing"
- `parsing_success`: Whether parsing succeeded
- `parsed_skills_count`: Number of skills extracted
- `parsed_experience_count`: Number of experience entries
- `parsed_education_count`: Number of education entries
- `raw_text_length`: Original resume text length in characters
- `chunks_indexed`: Number of text chunks indexed in Chroma
- `ingest_task_id`: Celery task ID for asynchronous ingestion

## Accuracy Metrics Explained

### Precision, Recall, and F1-Score
These metrics measure how well the ATS scoring matches job requirements:

- **Precision**: Of the keywords flagged as matched, how many were actually in the resume?
  - Formula: `true_positives / (true_positives + false_positives)`
  - Range: 0-1 (higher is better)

- **Recall**: Of all required keywords, how many were found in the resume?
  - Formula: `true_positives / (true_positives + false_negatives)`
  - Range: 0-1 (higher is better)

- **F1-Score**: Harmonic mean of precision and recall
  - Formula: `2 * (precision * recall) / (precision + recall)`
  - Range: 0-1 (higher is better, balanced metric)

### Bias Score
Indicates potential gender, age, or ethnicity biases in the scoring:
- **0.0**: No bias detected
- **0.5**: Moderate bias indicators found
- **1.0**: High bias indicators throughout

Recommendations appear with each score:
- "Appears fair": Low bias score, safe to use
- "Review for fairness": Moderate bias score, manual review recommended

## Example Log Entry

```json
{
  "pipeline_id": "pl2_1775541960973_67a513",
  "timestamp": 1775541996.4350507,
  "total_duration_seconds": 0.01,
  "steps_completed": 9,
  "steps_failed": 0,
  "step_metrics": {
    "ats": {
      "duration_seconds": 0.001,
      "completed_at": 1775541996.4293664,
      "status": "success"
    }
  },
  "artifacts_summary": {
    "ats_score": 0.5,
    "accuracy_metrics": {
      "precision": 0.8,
      "recall": 0.6,
      "f1_score": 0.686
    },
    "bias_score": 0.0
  }
}
```

## Log Usage

### Performance Analysis
Use `step_metrics` to identify bottlenecks:
- If `ats` step takes > 1 second, embedding model may be slow
- If `profile` step takes > 2 seconds, resume parsing is slow

### Quality Assurance
Monitor `accuracy_metrics`:
- Low precision: Resume skills not extracted properly
- Low recall: Job requirements not properly identified
- Low F1: Both have issues

### Fairness Monitoring
Track `bias_score` trends:
- Average bias score increasing: Add fairness filters
- High bias scores: Manually review affected candidates

## Automatic Log Generation

Logs are automatically generated for:
1. **Every pipeline run** (`{pipeline_id}_pipeline.json`)
2. **Every resume upload** (`{candidate_id}_parsing.json`)
3. **Every JD extraction** (`{pipeline_id}_jd_extraction.json`)
4. **Manual JD input** (`{pipeline_id}_manual_jd.json`)

No manual intervention needed - logs are created immediately after each operation completes.

## Log Retention

Consider implementing log rotation:
- **Daily rotation**: Rename logs with date suffix
- **Weekly cleanup**: Archive old logs (> 30 days)
- **Monthly storage**: Long-term archive for compliance

## Analysis Tools

Example analysis script:
```python
import json
import glob
from statistics import mean

# Load all pipeline logs
logs = []
for filepath in glob.glob("/workspaces/TalentFlow/logs/*_pipeline.json"):
    with open(filepath) as f:
        logs.append(json.load(f))

# Calculate average ATS score
avg_score = mean(log["artifacts_summary"]["ats_score"] for log in logs)
print(f"Average ATS Score: {avg_score:.3f}")

# Calculate average F1-score
avg_f1 = mean(log["artifacts_summary"]["accuracy_metrics"]["f1_score"] for log in logs)
print(f"Average F1-Score: {avg_f1:.3f}")

# Check for biases
high_bias = [log for log in logs if log["artifacts_summary"]["bias_score"] > 0.5]
print(f"Pipelines with high bias: {len(high_bias)}")
```
