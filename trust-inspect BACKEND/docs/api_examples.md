# API examples

Create a project:

```bash
curl -X POST http://127.0.0.1:8000/projects ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"Demo NGO\",\"state\":\"Tamil Nadu\",\"district\":\"Coimbatore\",\"beneficiaries\":50}"
```

Analyze:

```bash
curl -X POST http://127.0.0.1:8000/ai/analyze/1
```

Assign:

```bash
curl -X POST http://127.0.0.1:8000/inspections/assign
```

Verify ledger:

```bash
curl http://127.0.0.1:8000/ledger/verify
```
