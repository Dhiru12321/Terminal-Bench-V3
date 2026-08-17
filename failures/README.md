# Failure Postmortems

This directory stores structured postmortems for rejected tasks. Records are
repo-internal calibration artifacts; do not package them with task submissions.

Use:

```bash
python3 scripts/log_failure.py --template --out /tmp/failure-template.json
python3 scripts/log_failure.py --from-json /tmp/failure-template.json
python3 scripts/failure_meta_review.py
```

Schema: `failures/catalog.schema.json`.

Policy and process: `docs/FAILURE_CATALOG.md`.
