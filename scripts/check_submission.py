from pathlib import Path
import json
root=Path(__file__).resolve().parents[1]
required=['README.md','requirements.txt','pyproject.toml','docs/capture_protocol.md','docs/compliance_matrix.md','src/spatialscan/cli.py','src/spatialscan/models.py']
missing=[x for x in required if not (root/x).exists()]
print('missing:',missing or 'none')
print('raw benchmark captures:',len(list((root/'benchmarks/raw').glob('*'))) if (root/'benchmarks/raw').exists() else 0)
print('manifest:',json.load(open(root/'benchmarks/manifest.json'))['version'])
raise SystemExit(1 if missing else 0)
