#json read/write tester

import json

with open('results_schema.json') as f:
    data = json.load(f)

with open('results_schema.json', 'w') as f:
    json.dump(data, f, indent=2, sort_keys=True)
