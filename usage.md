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
