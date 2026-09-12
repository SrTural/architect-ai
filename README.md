# 🏛️ ArchitectAI

**Local-first AI-powered legacy code refactoring engine.**

Transforms insecure, outdated Python code into modern, secure architecture — 100% on-premise, zero data exfiltration.

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-Qwen%202.5-000000?logo=ollama&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-22c55e)
![Status](https://img.shields.io/badge/Status-v0.1%20Alpha-orange)

---

## The Problem

Legacy systems in **banking, healthcare, government, and defense** cannot be sent to cloud-based SAST tools (Snyk, Checkmarx, GitHub Copilot) because:

- **GDPR / HIPAA compliance** — source code cannot leave the organization
- **Air-gapped networks** — no internet access by design
- **National security** — code is classified

---

## The Solution

ArchitectAI does **not** just find vulnerabilities. It **transforms the entire architecture**.

| Traditional SAST | ArchitectAI |
|:---|:---|
| "SQL injection on line 42" | Rewrites the file with SQLAlchemy ORM |
| "eval() is dangerous" | Removes eval() and replaces it with ast.literal_eval() |
| "Hardcoded password found" | Migrates secrets to environment variables |
| **1 bug fixed** | **10 bugs prevented** |

---

## Why ArchitectAI?

| Feature | Cloud SAST | ArchitectAI |
|:---|:---:|:---:|
| Data location | Vendor servers | **Your server** |
| GDPR compliant | Partial | **Full** |
| Air-gapped | No | **Yes** |
| Monthly cost | $50-500 / dev | **$0** |
| Data exfiltration | Possible | **Impossible** |
| Architectural refactoring | No | **Yes** |
| Self-correction loop | No | **Yes** |

---

## How It Works

1. **Parse** — Legacy code is converted to an Abstract Syntax Tree
2. **Analyze** — Local LLM detects anti-patterns (raw SQL, eval, hardcoded secrets)
3. **Refactor** — The entire file is rewritten using modern, secure architecture
4. **Validate** — Output is syntax-checked; on failure, the LLM retries

---

## Quick Start

```bash
git clone https://github.com/SrTural/architect-ai.git
cd architect-ai
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.main
