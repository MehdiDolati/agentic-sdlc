# Product Requirements (PRD)

Vision:
- {{ vision }}

Primary Users:
{% for u in users %}
- {{ u }}
{% endfor %}

Key Scenarios:
{% for s in scenarios %}
- {{ s }}
{% endfor %}

Success Metrics:
{% for m in metrics %}
- {{ m }}
{% endfor %}

## Stack Summary (Selected)
Language: Python
Backend Framework: FastAPI
Database: SQLite

## Acceptance Gates
- Coverage gate: minimum 80%
- Linting passes
- All routes return expected codes
