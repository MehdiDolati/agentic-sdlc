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
