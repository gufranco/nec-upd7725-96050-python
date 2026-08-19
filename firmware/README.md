# Firmware goes here

Nothing in this directory is committed, and nothing in it ships. The rest of the
repository is a processor, and a processor is complete without any firmware at
all: every instruction it has is settled against the reference by generating the
instruction words rather than by quoting anyone's program.

A firmware image is only needed to run a particular cartridge's part, and that
image belongs to whoever wrote it. So a copy you already own goes here, on your
own disk, and the tests that use it are opt-in and skipped when it is absent.

## What belongs here

| Part | Processor | Bytes | Names it is usually saved under |
|:-----|:----------|------:|:--------------------------------|
| DSP-1 | uPD7725 | 8,192 | `dsp1.rom`, `dsp1.bin` |
| DSP-1B | uPD7725 | 8,192 | `dsp1b.rom`, `dsp1b.bin` |
| DSP-2 | uPD7725 | 8,192 | `dsp2.rom`, `dsp2.bin` |
| DSP-3 | uPD7725 | 8,192 | `dsp3.rom`, `dsp3.bin` |
| DSP-4 | uPD7725 | 8,192 | `dsp4.rom`, `dsp4.bin` |
| ST010 | uPD96050 | 53,248 | `st010.rom`, `st0010.bin` |
| ST011 | uPD96050 | 53,248 | `st011.rom`, `st0011.bin` |

The program comes first and the data second, the program three bytes to a word
and the data two. Some tools save a shorter file holding only the part each
cartridge actually reaches; that layout is recognised too and named when it is
found, rather than rejected.

## How to use it

```bash
export UPD7725_FIRMWARE_DIR=~/nec-upd7725-python/firmware
python3 conformance/against_firmware.py
```

Every file is identified by digest before it is run. A file that does not match
is diagnosed rather than refused: the report says whether it is the wrong part,
the wrong revision, a shorter layout, an archive rather than the file inside it,
or a known bad dump.
