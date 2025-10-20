# supplier-verifier

Automates verification of a company location address and classifies supplier type based on provided categories.

## Features
- Google Custom Search (CSE) or SerpAPI fallback (configure via env vars)
- Fuzzy company + address matching
- Category inference with keyword heuristics (respects existing category if provided)
- Evidence scoring and export to CSV or JSON

## Installation
Inside project directory:
```
poetry install
```

## Environment Variables
Set one of:
- `GOOGLE_CSE_API_KEY` + `GOOGLE_CSE_ID` (preferred)
- OR `SERPAPI_KEY`

## Usage
Prepare a CSV with headers:
```
company,address,existing_category
Great Lakes Lifting Solutions,209 E Corning Ave, Peotone, IL 60468,
Sautter Crane Rental,2900 Black Lake Pl, Philadelphia, PA 19154,
```
Run:
```
poetry run supplier-verify input.csv --out-csv results.csv --json results.json --print
```

## Output CSV Columns
- company
- address
- verified (Yes/No)
- category (final chosen or blank)
- reason
- evidence_sources (pipe-separated: source:score:MatchedFlag)

## Notes
- Address verification heuristic uses fuzzy token sorting; threshold tuned conservatively.
- Missing or invalid street number will force `verified=False`.
- Adjust keyword mapping in `categories.py` as needed.

## Roadmap
- Add parallel request option
- Pluggable category classifier (ML) interface
- Retry/backoff logic for search APIs
