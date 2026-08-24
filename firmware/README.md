# Firmware goes here

Nothing in this directory is committed, and nothing in it ships. The rest of the
repository is a processor, and a processor is complete without any firmware at
all: every instruction it has is settled against the reference by generating the
instruction words rather than by quoting anyone's program.

A firmware image is only needed to run a particular cartridge's part, and that
image belongs to whoever wrote it. So a copy you already own goes here, on your
own disk, and the tests that use it are opt-in and skipped when it is absent.

## What belongs here

Each image is identified by its digest before it is run, not by its name. Any file
ending `.bin` or `.rom` is read and matched against this table, so a copy called
`dsp1.rom`, `dsp1.bin` or anything else works as long as its content is right.

| Part | Revision | Bytes | CRC32 | MD5 |
|:-----|:---------|------:|:------|:----|
| `dsp1` | DSP-1 | 8,192 | `27124599` | `4865ac61cd758b0f9383fe3d4d3b8694` |
| `dsp1b` | DSP-1B | 8,192 | `588279b4` | `c8bfb983703a96e1c3d4683105112bc0` |
| `dsp2` | DSP-2 | 8,192 | `f0221c90` | `e500ec7f6005e78cb935eea5289c8cc4` |
| `dsp3` | DSP-3 | 8,192 | `e3b54e6a` | `c037185c8bbef6313226200dbe5fd07f` |
| `dsp4` | DSP-4 | 8,192 | `ca09e176` | `fe85065a7023551b0d84941a094435ba` |
| `st010` | ST010 | 53,248 | `8d136190` | `a1728c31df22b93e4bdae73718ba27a2` |
| `st011` | ST011 | 53,248 | `750c6012` | `2c56baddba22c6649c95c4c3b13adce3` |

| Part | SHA-1 | SHA-256 |
|:-----|:------|:--------|
| `dsp1` | `4870e3b1636938c85347e20c56a81284fdfaf46e` | `5f2e5ed06b362be023b978b5978813ecb9a07c76592454b45c2a1ed17a0de349` |
| `dsp1b` | `1e0112ba3b130c770dab342f6cfe47ac53b278f0` | `4d42db0f36faef263d6b93f508e8c1c4ae8fc2605fd35e3390ecc02905cd420c` |
| `dsp2` | `9179f61b8823b4e9a4130e1fb732424a2f6daa1a` | `5efbdf96ed0652790855225964f3e90e6a4d466cfa64df25b110933c6cf94ea1` |
| `dsp3` | `0386ffaa041a5798c4568c5f5dc17fe66bb09d24` | `2e635f72e4d4681148bc35429421c9b946e4f407590e74e31b93b8987b63ba90` |
| `dsp4` | `9a5392879cee4bac7907159f281d9e5681dfa66a` | `63ede17322541c191ed1fdf683872554a0a57306496afc43c59de7c01a6e764a` |
| `st010` | `75a3e5b5564ea251060dd35bff3dc468d4429e77` | `55c697e864562445621cdf8a7bf6e84ae91361e393d382a3704e9aa55559041e` |
| `st011` | `b2fdfa3edf08f76dbd30a0a4d3d0ef1e3d3f6905` | `651b82a1e26c4fa8dd549e91e7f923012ed2ca54c1d9fd858655ab30679c2f0e` |

**SHA-256 decides.** The other three are published so a copy can be cross-checked
against a database that keys on one of them, and none of them decides anything on
its own: a CRC32 is a 32-bit error code, and MD5 and SHA-1 are both collision
broken. All four are checked: a file that matches on SHA-256 and disagrees on any
of the others is refused, because a manifest that contradicts itself is worth
saying out loud rather than passing over.

The program comes first in the file and the data second, the program three bytes
to a word and the data two.

## How to use it

```bash
export UPD7725_FIRMWARE_DIR=~/nec-upd7725-96050-python/firmware
python3 conformance/against_firmware.py
```

Every file is identified by digest before it is run. A file that does not match
is diagnosed rather than refused: the report says whether it is the wrong part,
the wrong revision, a shorter layout, an archive rather than the file inside it,
or a known bad dump.
