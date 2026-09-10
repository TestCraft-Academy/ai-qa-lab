# Module 01: LLM API Failure Surface

This module contains self-contained demonstrations of the **7 core failure surfaces** that occur when interacting with raw LLM APIs. Each script isolates a specific failure mode, demonstrates how to trigger it, audits the defect, and outlines SDET takeaways.

---

## Failure Surface Matrix

| # | Demonstration Script | Failure Mode Demonstrated | Downstream Impact | SDET Defense |
|---|---|---|---|---|
| **01** | `01_token_cost_and_densities.py` | Token-to-word density disparity (Code/JSON vs. Prose). | Token underestimation, sudden 429 rate limits, and billing blowout. | Pre-flight `count_tokens` budgeting assertions on incoming payloads. |
| **02** | `02_context_limits_and_truncation.py` | Silent truncation via `FinishReason.MAX_TOKENS` with HTTP 200. | Incomplete answers; unclosed JSON payloads crash parsers. | Assert `finish_reason == FinishReason.STOP`; budget generous output tokens. |
| **03** | `03_temperature_and_variance.py` | Non-deterministic sampling across temperatures. | Flaky CI assertions; hallucinations at high temperatures. | Enforce `temperature=0.0` for structured tasks; use Pass@k distribution testing. |
| **04** | `04_guardrail_bypass_side_channels.py` | Insecurity of negative system instructions against side-channels. | Data leakage via comparative, ratio, and arithmetic probes. | Filter, mask, or enforce RBAC before text enters the prompt context. |
| **05** | `05_streaming_defects.py` | Network resets, non-text chunks, and partial JSON parsing. | Telemetry loss (0 tokens logged), client app crashes, state poisoning. | Defensive chunk guards (`if chunk.text`), deferred JSON parsing, session audits. |
| **06** | `06_schema_vs_semantic_validity.py` | Type-safe hallucinations; safety refusal behavior. | Schemas pass validation while business logic is violated. | Write semantic invariant assertions; handle refusal states gracefully. |
| **07** | `07_tool_calling_vulnerabilities.py` | Hallucinated tool arguments, boundary breaches, loop crashes. | Unauthorized database access, application crashes, infinite retry loops. | Parameter whitelisting at tool boundary, feedback error loops, circuit breakers. |

---

## Quickstart & Execution

Ensure your virtual environment is active and your API key is set in `.env`:

```bash
# Set up environment in repository root
cp .env.example .env
# Edit .env and paste your GEMINI_API_KEY

# Run any demonstration directly
python 01-api-failure-surface/01_token_cost_and_densities.py
python 01-api-failure-surface/02_context_limits_and_truncation.py
python 01-api-failure-surface/03_temperature_and_variance.py
python 01-api-failure-surface/04_guardrail_bypass_side_channels.py
python 01-api-failure-surface/05_streaming_defects.py
python 01-api-failure-surface/06_schema_vs_semantic_validity.py
python 01-api-failure-surface/07_tool_calling_vulnerabilities.py
```

---

> [!TIP]
> **Looking for hands-on exercises, automated test suites, and challenges?**  
> Check out the companion [ai-qa-workshops](file:///Users/jagobond/repos/_testcraft/ai-qa-workshops) repository for complete Systems Under Test (SUT) and interactive Pytest labs.
