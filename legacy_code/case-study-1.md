# Case Study 1: Remediation-Demo (Flask → FastAPI)

## 📊 Metadata
- **Source:** github.com/vulnerable-apps/Remediation-Demo
- **Original size:** 1,888 simvol, 4 funksiya
- **Refactor time:** 16 saniyə
- **Attempts:** 1
- **Date:** 2026-09-12

## 🔴 Before (Legacy Flask)

### Vulnerabilities Found:
1. **SQL Injection** (CRITICAL)
   `query = f"SELECT * FROM users WHERE name = '{name}'"`

2. **Credential Leak** (CRITICAL)
   `/.env` endpoint exposes: `DB_PASSWORD=crapi`, `MONGO_DB_PASSWORD=crapi`

3. **Raw sqlite3** — No ORM
4. **Debug mode in production** — `app.run(debug=True)`

## 🟢 After (ArchitectAI Output)

### Fixed:
- ✅ **SQL Injection** → SQLAlchemy ORM parameterized query
- ✅ **Framework** → Flask → FastAPI (modern)
- ✅ **Validation** → Pydantic UserResponse model
- ✅ **Dependency injection** → `Depends(get_db)`
- ✅ **Config** → `os.getenv()` instead of hardcoded

### Remaining Issues (Human Review Required):
- ❌ **`/.env` endpoint still leaks credentials** — must be removed
- ⚠️ `@app.on_event("startup")` deprecated
- ⚠️ `init_db()` inserts duplicates on every startup
- ⚠️ Type hint `SessionLocal` should be `Session`

## 📈 Result

| Metric | Value |
|:---|:---:|
| Vulnerabilities fixed | 1/2 (SQL injection) |
| Architecture modernized | ✅ Yes |
| Syntax valid | ✅ Yes |
| Attempts | 1 |
| Time | 16 seconds |
| Success rate | 70-80% |

## 🎯 Conclusion

ArchitectAI successfully transformed a Flask-based legacy API into a 
modern FastAPI + SQLAlchemy architecture. SQL injection was eliminated 
at the architectural level.

Human review identified 1 remaining critical issue (`/.env` endpoint) 
and 3 minor improvements — demonstrating the **"AI + Human"** workflow.

**Key Insight:** AI excels at architectural refactoring (ORM, framework, 
validation) but requires human oversight for business-logic and 
security-policy decisions.