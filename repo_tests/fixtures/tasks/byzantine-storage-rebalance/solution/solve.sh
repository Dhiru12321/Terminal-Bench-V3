#!/usr/bin/env bash
set -euo pipefail

cd /app
export PATH="/usr/local/go/bin:${PATH}"

python3 <<'PY'
from pathlib import Path

journal = Path("internal/transport/journal.go")
jt = journal.read_text()
old_j = """	for _, d := range batch {
		apply(d)
	}
	for _, d := range batch {
		apply(d)
	}
}"""
new_j = """	for _, d := range batch {
		apply(d)
	}
}"""
if old_j not in jt:
    raise SystemExit("journal.go: expected duplicate replay block not found")
journal.write_text(jt.replace(old_j, new_j))

fp = Path("internal/codec/fingerprint.go")
ft = fp.read_text()
old_f = """	lim := n
	if n%wideStride == 0 {
		lim = n - wideStride
		if lim < 0 {
			lim = 0
		}
	}
	for i := 0; i < lim; i += wideStride {"""
new_f = """	lim := n
	for i := 0; i < lim; i += wideStride {"""
if old_f not in ft:
    raise SystemExit("fingerprint.go: expected stride limiter block not found")
fp.write_text(ft.replace(old_f, new_f))

mg = Path("internal/catalog/merge.go")
mt = mg.read_text()
old_m = """		case api.LayoutV2:
			sum += s.AvailBytes - s.FreeBytes"""
new_m = """		case api.LayoutV2:
			sum += s.FreeBytes"""
if old_m not in mt:
    raise SystemExit("merge.go: expected v2 merge line not found")
mg.write_text(mt.replace(old_m, new_m))
PY

go build -o /app/storesim ./cmd/storesim
mkdir -p /app/output
/app/storesim -replays /app/fixtures/replays -out /app/output/report.json
