### Pack/Create and Unpack/Extract

```bash
# Pack/Create with verification and compression

python frupack.py -o test-z.img -f fl1.json -i ipmi.json -v -g

# w/o compression

python frupack.py -o test-n.img -f fl1.json -i ipmi.json -v

# Unpack/Extract with verification

python funpack.py -i test-z.img -o test_z

python funpack.py -i test-n.img -o test_n
```

### JSON Input Validation

Input JSON files are automatically validated against their corresponding JSON schemas before processing. If validation fails, the tool reports the error and stops before building any image.

**Schema mapping:**

| Input file prefix | Schema file                      |
|--------------------|----------------------------------|
| `fl*` (e.g. fl1.json, fl2.json) | `schemas/fru-tool-input-v0_1_0.json` |
| `ipmi*` (e.g. ipmi.json, ipmi2.json) | `schemas/fru-tool-ipmi-v0_1_0.json` |

Validation happens automatically when running `frupack.py`. No extra flags are needed.

**Standalone validation:**

The `validate_json_with_schema(json_file, schema_file)` function in `utility.py` can also be used directly:

```python
from utility import validate_json_with_schema

valid, message = validate_json_with_schema("samples/ipmi.json", "schemas/fru-tool-ipmi-v0_1_0.json")
print(message)
```

The function returns a tuple of `(bool, str)` — `True` with a success message on pass, or `False` with a descriptive error on failure.

**Dependency:** Requires the `jsonschema` package (`pip install jsonschema`).
