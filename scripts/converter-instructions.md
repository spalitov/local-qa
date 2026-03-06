# Scenario CSV -> JSON Converter

Standalone utility that converts a scenario CSV into the JSON structure expected by `scenarios.json`:

```json
{ "scenarios": [ ... ] }
```

## Run

```bash
node tools/scenario-csv-json/convert.js --in <input.csv> --out <output.json>
```

If `--out` is omitted, JSON is printed to stdout.

## Expected source columns

Required:
- `SEND_ID`
- `COMPANY_NAME`

Common optional columns supported:
- `COMPANY_WEBSITE`
- `PERSONA`
- `MESSAGE_TONE`
- `CONVERSATION_JSON`
- `LAST_5_PRODUCTS`
- `ORDERS`
- `COMPANY_NOTES`
- `ESCALATION_TOPICS`
- `BLOCKLISTED_WORDS`
- `HAS_SHOPIFY`
- `COUPONS`
- `COMPANY_PROMOTIONS`