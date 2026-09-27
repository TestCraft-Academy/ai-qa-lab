# AI QA Demonstration Library

> **Insidious AI Failure Modes: Reproduce, Audit, and Defend.**  
> A practical, open-source demonstration catalog showing QA professionals and SDETs exactly how LLM systems fail in production, why naive testing breaks down, and what technical safeguards are required.

This repository accompanies the video tutorials and articles on AI Testing & Evaluation. Every script is standalone, zero-friction, and runs directly in your terminal.

---

## Repository Map

```text
ai-qa-lab/
├── 01-api-failure-surface/            # The 7 core failure modes across providers
│   ├── 01_token_cost_and_densities.py # 6-model cross-provider tokenization benchmark
│   ├── gemini/                        # Google Gemini implementation (google-genai)
│   ├── OpenAI/                        # OpenAI implementation (openai)
│   └── Anthropic/                     # Anthropic Claude implementation (anthropic)
├── 02-nondeterminism-and-sampling/    # [Roadmap] Pass@k, variance distributions across 30 runs
├── 03-rag-failure-modes/              # [Roadmap] Retrieval misses, chunking errors, context poisoning
├── 04-eval-metrics-and-judges/        # [Roadmap] String vs. semantic metrics, LLM-as-judge calibration
├── 05-production-observability/       # [Roadmap] Tracing, cost & latency tracking, drift detection
└── 06-security-and-red-teaming/       # [Roadmap] OWASP LLM Top 10, direct/indirect injection
```

---

## The Standard Demonstration Anatomy

Each demonstration script follows a disciplined QA defect pattern:

1. **`[TEST SCENARIO]`**: Defines the system boundary and failure mechanism.
2. **Defect Repro**: Executes an API request that triggers the failure or vulnerability.
3. **`[QA DEFECT AUDIT]`**: Analyzes the exact output, silent failure, or unhandled exception.
4. **`[SDET Takeaways]`**: Concrete testing practices, assertions, and architectural mitigations.

---

## Quickstart

### 1. Prerequisites
- Python 3.10+
- API keys for the providers you wish to test:
  - Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/)
  - OpenAI API Key from [OpenAI Platform](https://platform.openai.com/)
  - Anthropic API Key from [Anthropic Console](https://console.anthropic.com/)

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/TestCraft-Academy/ai-qa-lab.git
cd ai-qa-lab

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure your API keys
cp .env.example .env
# Edit .env and paste your GEMINI_API_KEY, OPENAI_API_KEY, and/or ANTHROPIC_API_KEY
```

### 3. Run a Demonstration
```bash
# Gemini Examples:
python 01-api-failure-surface/gemini/02_context_limits_and_truncation.py
python 01-api-failure-surface/gemini/04_guardrail_bypass_side_channels.py

# OpenAI Examples:
python 01-api-failure-surface/OpenAI/01_token_cost_and_densities.py
python 01-api-failure-surface/OpenAI/06_schema_vs_semantic_validity.py

# Anthropic Examples:
python 01-api-failure-surface/Anthropic/02_context_limits_and_truncation.py
python 01-api-failure-surface/Anthropic/07_tool_calling_vulnerabilities.py
```

---

## Looking for Hands-On Exercises & Workshops?

This repository contains **demonstrations** designed for inspection and video walkthroughs.

If you are looking for **interactive lab exercises, broken systems under test (SUTs), automated Pytest suites, and challenges with solution keys**, visit TestCraft Academy:
👉 **[TestCraft Academy](https://www.testcraftacademy.com/)**
