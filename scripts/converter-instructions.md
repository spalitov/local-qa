# Scenario CSV -> JSON Converter

Standalone utility that converts a scenario CSV into the JSON structure expected by `scenarios.json`:

```json
{ "scenarios": [ ... ] }
```

## Run

```bash
node scripts/convert_input.js --in <input.csv> --out <output.json>
```

If `--out` is omitted, JSON is printed to stdout.

Output scenarios keep full `conversation`, but omit:
- `companyName`

Kept fields include:
- `escalation_preferences`
- `blocklisted_words`
- `rightPanel.promotions` (only `promotions` inside `rightPanel`, when present)

## Expected source columns

Required:
- `SEND_ID`

Common optional columns supported:
- `MESSAGE_TONE`
- `CONVERSATION_JSON`
- `ESCALATION_TOPICS`
- `BLOCKLISTED_WORDS`
- `COMPANY_PROMOTIONS`
