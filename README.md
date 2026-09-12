# 🏛️ ArchitectAI

**Local-first AI-powered legacy code refactoring engine.**

Transforms insecure, outdated Python code into modern, secure architecture — 100% on-premise, zero data exfiltration.

---

## The Problem

Legacy systems in **banking, healthcare, government, and defense** cannot be sent to cloud-based SAST tools (Snyk, Checkmarx, GitHub Copilot) because:

- **GDPR / HIPAA compliance** — source code cannot leave the organization
- **Air-gapped networks** — no internet access by design
- **National security** — code is classified

Existing tools either don't work in these environments, or are outright illegal to use.

---

## The Solution

ArchitectAI does **not** just find vulnerabilities. It **transforms the entire architecture**.

Instead of patching individual bugs (a losing game at scale), it rewrites the code so that vulnerabilities **cannot exist** in the first place.

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
| Air-gapped | No | Yes |
| Monthly cost | $50-500 / dev | **$0** |
| Data exfiltration | Possible | **Impossible** |
| Architectural refactoring | No | Yes |
| Self-correction loop | No | Yes |

---

## How It Works

1. **Parse** — Legacy code is converted to an Abstract Syntax Tree
2. **Analyze** — Local LLM detects anti-patterns (raw SQL, eval, hardcoded secrets, etc.)
3. **Refactor** — The entire file is rewritten using modern, secure architecture
4. **Validate** — Output is syntax-checked; on failure, the LLM is asked to retry

---

## Quick Start

### Prerequisites

- Python 3.12+
- Ollama installed and running
- Qwen 2.5 model pulled locally

```bash
ollama pull qwen2.5:7b-16k
