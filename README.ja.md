# NEC uPD7725

NECのデジタルシグナルプロセッサuPD7725とuPD96050をPythonで実装したもので、1クロックサイクルにつき1命令を実行します。印刷されたすべての事実はNECの1987年のデータシートと1989年のデータブックに、各命令後のプロセッサ状態全体は記録済みのコーパスに照らして検証しています。

[English](README.md) | 日本語 | [简体中文](README.zh-Hans.md) | [繁體中文（香港）](README.zh-HK.md)

[![CI](https://github.com/gufranco/nec-upd7725-96050-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/nec-upd7725-96050-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/nec-upd7725-96050-python)](https://github.com/gufranco/nec-upd7725-96050-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**2**種類のチップ、フィールドごとに網羅した**1,120**通りのエンコーディング、比較した**22,240**命令、不一致**0**件、**1,111**件のテスト、ステートメントとブランチの**100%**カバレッジ、依存パッケージなし

```python
from upd7725 import Cpu

cpu = Cpu("upd7725")
cpu.reset()
cpu.stores.load_program(bytes([0xC0, 0x0A, 0x81]))

cost = cpu.step()

print(f"{cpu.registers.word('a'):04X}", cost, cpu.registers.pc, cpu.cycles, cpu.steps)
```

```
002A 1 1 5 1
```

この3バイトは24ビットのプログラムワード1つ、`C00A81`です。上位2ビットがロード形式を選び、続く16ビットが値`002A`を運び、下位4ビットが転送先としてアキュムレータAを指定します。このステップのコストは1サイクルです。`reset()`がNECの示すRESETパルス幅の最小値である4サイクルを消費するため、サイクルカウンタは5になります。

## インストール

| 要件   | バージョン |
| :----- | :--------- |
| Python | 3.12以降   |
| git    | 任意       |

```bash
git clone https://github.com/gufranco/nec-upd7725-96050-python.git
cd nec-upd7725-96050-python
python3 upd7725/doctor.py
```

このパッケージは標準ライブラリ以外を一切インポートしません。`python3 -m pip install git+https://github.com/gufranco/nec-upd7725-96050-python.git`でインストールすると、ドクターが`upd7725-doctor`コマンドとして入ります。

ドクターはマシンとチェックアウトを確認し、両方のチップを構築してリセットし、最後に1行を出力します。すべてのチェックに合格すると終了コード0、それ以外では1で終了します。バグ報告には出力全体を貼り付けてください。

```
  4 checks, nothing to report
```

リリースは[セマンティックバージョニング](https://semver.org/)に従い、semantic-releaseがコミット履歴から作成します。すべてのリリースにはタグが付き、[リリースページ](https://github.com/gufranco/nec-upd7725-96050-python/releases)に掲載されます。

## インターフェース

`upd7725.Cpu(model, memory=None, *, fill=0, sources=None, seed=UNSET_SEED)`は、電源が入った状態でリセット前のチップを1つ構築します。

| 引数      | 意味                                                                                                                                                          |
| :-------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `model`   | 必須です。[モデル](#models)の表にあるモデル名または別名です。省略すると`UnknownModelError`が発生します                                                        |
| `memory`  | 使用する`Stores`です。省略するとチップ自身のサイズで1つ構築します                                                                                             |
| `fill`    | 各ストアの未書き込みワードを読んだときの値で、ストアの幅でマスクされます。省略時は`0`です                                                                     |
| `sources` | `"program"`、`"table"`、`"scratch"`からアドレスを引数に取る関数へのマッピングです。ソースを持つストアは、未書き込みワードを`fill`の代わりにソースから読みます |
| `seed`    | 電源投入時のレジスタのスクランブルです。同じシードで構築した2つのチップは同じ値を保持します                                                                   |

### 呼び出し

| 呼び出し                       | 動作                                                                                                                                                              | 戻り値                                  |
| :----------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------- | :-------------------------------------- |
| `reset()`                      | RESETピンの動作です。プログラムカウンタを0に、`steps`を0にし、4サイクルを消費します                                                                               | チップ                                  |
| `step()`                       | 1命令を実行します                                                                                                                                                 | 消費したサイクル数で、どの命令でも1です |
| `run_for(cycles)`              | 少なくとも`cycles`が経過するまで命令単位で実行します                                                                                                              | 消費したサイクル数                      |
| `run_until(check, limit=None)` | `check(cpu)`が偽の間ステップ実行します。`limit`命令を実行すると`RunLimit`を送出します                                                                             | チップ                                  |
| `held()`                       | チップがプログラムの進行を止めているかどうかです。このチップにはホルト状態がありません                                                                            | `False`                                 |
| `irq()`                        | 割り込み線をアサートします。立ち上がりエッジで、ステータスワードのEIビットが立っていれば、プログラムカウンタをプッシュし、100Hへジャンプし、1サイクルを消費します | 割り込みが受理されたときは`True`        |
| `lower_irq()`                  | 割り込み線をネゲートし、次の`irq()`を新しいエッジにします                                                                                                         | `None`                                  |
| `power_on(seed=UNSET_SEED)`    | 構築時と同じく、`seed`からレジスタを再びスクランブルします                                                                                                        | `None`                                  |
| `spend()`                      | 1サイクルを数え、`on_cycle`を呼び出します。チップが消費するすべてのサイクルはここを通ります                                                                       | `None`                                  |

### 状態

| 属性                 | 意味                                                                                                                          |
| :------------------- | :---------------------------------------------------------------------------------------------------------------------------- |
| `model`              | チップの構築元である`Model`レコードです                                                                                       |
| `registers`          | レジスタファイルで、後述します                                                                                                |
| `flags_a`, `flags_b` | 各アキュムレータの6つのフラグ、`s1`、`s0`、`c`、`z`、`ov1`、`ov0`です。`int()`は`ov0`をビット0、`s1`をビット5としてまとめます |
| `stores`             | 3つのストアで、後述します                                                                                                     |
| `cycles`             | チップの構築以降のサイクル数です。リセットでも加算されます                                                                    |
| `steps`              | 直前のリセット以降の命令数です                                                                                                |
| `irq_line`           | レベルとしての割り込み線です                                                                                                  |
| `on_cycle`           | `None`、またはサイクルごとに引数なしで呼ばれる関数です                                                                        |
| `pins`               | シリアルポートとDMA要求で、[シリアルポートとDMA要求](#the-serial-port-and-the-dma-request)で説明します                        |

`registers.pc`、`rp`、`dp`、`sp`は書き込まれた値をチップ固有の幅でマスクします。`k`、`l`、`m`、`n`、`a`、`b`は16ビットを保持し、符号付きで読み出されます。`registers.word(name)`はそのいずれも符号なし16ビットワードとして読みます。`tr`、`trb`、`dr`、`si`、`so`は普通の整数です。`registers.stack`はチップのスタックと同じ長さのリストで、`registers.sr`はステータスワードです。ビット`p0`、`p1`、`ei`、`sic`、`soc`、`drc`、`dma`、`usf0`、`usf1`、`rqm`、`drs`はデータシートのFigure 3が示す位置にあり、`int(registers.sr)`はそれらを1ワードとして読み、`registers.sr.assign(word)`は1ワードからそれらを設定します。`registers.sr.siack`と`registers.sr.soack`は、SIACKとSOACKによる条件ジャンプが読むシリアル入力と出力の肯定応答です。どちらもワードには含まれません。シリアル入力にワード全体が届くと`siack`が立ち、SIからの転送がそれをクリアします。SOへの転送は`soack`を立て、ワードがシフトレジスタへ移るとそれがクリアされます。

```python
from upd7725 import Cpu, disassemble

program = [0xDFFFC1, 0xC00043, 0x150030]
cpu = Cpu("upd7725", fill=0)
cpu.reset()
cpu.stores.load_program(b"".join(word.to_bytes(3, "big") for word in program))
cpu.run_for(3)

registers = cpu.registers
print([found.text for found in disassemble(program)])
print(registers.a, hex(registers.word("a")), cpu.flags_a, int(cpu.flags_a))
print(registers.sr, hex(int(registers.sr)))
```

```
['ld $7FFF,a', 'ld $0001,tr', 'add a idb tr->none']
-32768 0x8000 <Flags ov0 ov1 s0 s1> 51
<Status none> 0x0
```

7FFFに1を足すと符号ビットへオーバーフローします。アキュムレータAは符号付きで-32768、ワードとして8000と読め、加算は両方のオーバーフローフラグと両方の符号フラグを立てます。

### 実行、割り込み、サイクルフック

```python
from upd7725 import Cpu, RunLimit

cpu = Cpu("upd7725", fill=0)
cpu.reset()
cpu.stores.load_program(bytes.fromhex("C02007"))
seen = []
cpu.on_cycle = lambda: seen.append(cpu.cycles)

cpu.run_until(lambda part: part.registers.pc == 16)
print(cpu.registers.pc, cpu.steps, cpu.cycles, len(seen), cpu.held())

registers = cpu.registers
print(cpu.irq(), hex(registers.pc), registers.stack[registers.sp - 1], cpu.cycles)
print(cpu.irq(), cpu.irq_line)
cpu.lower_irq()
print(cpu.irq(), registers.stack[registers.sp - 1])

try:
    cpu.run_until(lambda part: False, limit=100)
except RunLimit as error:
    print(error)
```

```
16 16 20 16 False
True 0x100 16 21
False True
True 256
gave up after 100 instructions at 164
```

最初のワード`ld $0080,sr`はEIビットを立て、その後のゼロのワードは何もしません。フックはリセット後に設定したため、16の命令サイクルは見ていますが、4つのリセットサイクルは見ていません。最初の`irq()`は立ち上がりエッジなので受理されます。2回目は線がすでにハイなので受理されません。`lower_irq()`の後の次の呼び出しは再び受理されますが、今度は100Hからなので、プッシュするのは100Hです。`RunLimit`は命令数とプログラムカウンタを16進数で示します。

### ストア

`cpu.stores`は`program`、`table`、`scratch`を保持する`Stores`です。それぞれが、そのアドレスを指定するレジスタとちょうど同じ長さの`Store`です。

| 名前                                                                      | 内容                                                                                                   |
| :------------------------------------------------------------------------ | :----------------------------------------------------------------------------------------------------- |
| `Stores(program_words, table_words, scratch_words, fill=0, sources=None)` | 指定したサイズの3つのストアです                                                                        |
| `stores.program`, `stores.table`, `stores.scratch`                        | 24ビットのプログラムワード、16ビットのテーブルワード、16ビットのスクラッチワードです                   |
| `stores.load_program(image)`                                              | アドレス0からイメージを書き込みます。3バイトで1ワード、上位バイトが先です                              |
| `stores.load_table(image)`                                                | テーブルに対して同じことを、2バイトで1ワードとして行います                                             |
| `stores.read_byte(at)`, `stores.write_byte(at, value)`                    | スクラッチの1バイトです。偶数アドレスはワード`at // 2`の下位バイト、奇数アドレスは上位バイトです       |
| `Store(words, bits, fill=0, source=None)`                                 | ストア1つです。`store[at]`はワードを読み書きし、`at`は長さを法として扱われ、値は`bits`でマスクされます |
| `store.changed()`                                                         | 書き込まれたワードのうち、以前に読んでいた値と異なるものすべてを、アドレスごとに返します               |
| `store.words`, `store.bits`, `store.mask`, `store.source`                 | 長さ、幅、その幅のマスク、ソース関数または`None`です                                                   |

```python
from upd7725 import Cpu, NotWholeWords, TooLarge

cpu = Cpu("upd7725", fill=0)
stores = cpu.stores
print(len(stores.program), len(stores.table), len(stores.scratch))
print(stores.program.bits, stores.table.bits, hex(stores.scratch.mask))

stores.load_table(bytes.fromhex("12348000"))
print(hex(stores.table[0]), hex(stores.table[1]), hex(stores.table[1024]))

stores.write_byte(1, 0xAB)
print(hex(stores.scratch[0]), hex(stores.read_byte(1)), stores.scratch.changed())

for image in (bytes(4), bytes(3 * 2049)):
    try:
        stores.load_program(image)
    except (NotWholeWords, TooLarge) as error:
        print(type(error).__name__, error)

counted = Cpu("upd7725", fill=0x1234, sources={"table": lambda at: at * 2})
print(hex(counted.stores.scratch[5]), counted.stores.table[5])
```

```
2048 1024 256
24 16 0xffff
0x1234 0x8000 0x1234
0xab00 0xab {0: 43776}
NotWholeWords 4 bytes is not a whole number of 3 byte words
TooLarge 2049 words will not fit in a store of 2048
0x1234 10
```

テーブルが1024ワードのuPD7725では、テーブルアドレス1024は0に折り返します。失敗するロードは、何かを書き込む前に例外を送出します。

### ホスト側

ホストからは2つのアドレスが見えます。0である`upd7725.DATA`と、1である`upd7725.STATUS`です。`upd7725.Host(cpu)`がそれらを操作します。

| 呼び出し                                                              | 動作                                                                                                                                                         |
| :-------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `asking`                                                              | RQMビットが立っている間、つまりチップがホストを待っている間はTrueです                                                                                        |
| `settle(limit=200000)`                                                | チップが要求するまでステップ実行します。実行した命令数を返し、`limit`に達すると`NeverReady`を送出します                                                      |
| `read(address)`                                                       | `STATUS`はステータスワードの上位8ビットを読みます。`DATA`はデータレジスタの1バイトを読み、転送が完了するとRQMをクリアします。それ以外のアドレスは0を読みます |
| `write(address, value)`                                               | `DATA`はデータレジスタに1バイトを書き込みます。ステータスワードは読み出し専用のため、それ以外のアドレスへの書き込みは何もしません                            |
| `send_bytes(values, limit=200000)`, `take_bytes(count, limit=200000)` | 各バイトの前にsettleしてから、書き込みまたは読み出しを行います                                                                                               |
| `send(word, limit=200000)`, `take(limit=200000)`                      | 16ビットワードを2バイトとして、下位バイトから扱います                                                                                                        |

DRCビットがクリアのとき、データレジスタは16ビットを1バイトずつ転送し、DRSは転送済みの半分を示します。DRCが立っているときは8ビットを転送します。

```python
from upd7725 import STATUS, Cpu, Host, NeverReady

cpu = Cpu("upd7725", fill=0)
cpu.reset()
cpu.stores.load_program(bytes.fromhex("C48D06"))
host = Host(cpu)

print(hex(host.read(STATUS)), host.settle(), hex(host.read(STATUS)))
print(hex(host.take()), host.asking)

cpu.reset()
host.send(0xBEEF)
print(hex(cpu.registers.dr), host.asking, cpu.steps)

try:
    host.settle(limit=50)
except NeverReady as error:
    print(error)
```

```
0x0 1 0x80
0x1234 False
0xbeef False 1
the part did not ask for attention within 50 instructions
```

プログラムは1ワード、`ld $1234,dr`です。データレジスタへの書き込みはRQMを立てます。RQMは`STATUS`のバイトのビット7です。ホストは1234を2回の読み出しで受け取り、2回目でRQMがクリアされます。リセット後、同じワードが再び要求し、ホストは代わりにBEEFを送ります。その後に要求するものはないため、最後の`settle`は諦めます。

<a id="the-serial-port-and-the-dma-request"></a>

### シリアルポートとDMA要求

`cpu.pins`は、ホストバスの外にある線を保持する`Pins`です。入力はホストがサイクルの合間に設定するレベルで、チップは各サイクルの最後にそれらを1回サンプリングします。エッジとは、前回のサンプリングで見たレベルからの変化です。

| 属性                       | 意味                                                                                                                           |
| :------------------------- | :----------------------------------------------------------------------------------------------------------------------------- |
| `sck`                      | シリアルクロック入力です。立ち上がりエッジで1ビットをシフトインし、立ち下がりエッジで1ビットをシフトアウトします               |
| `si`, `sien`               | シリアルデータ入力とそのイネーブルです。`sien`がローの間だけビットがシフトインします                                           |
| `soen`                     | シリアル出力イネーブルです。ローの間だけビットがシフトアウトします                                                             |
| `so`                       | シリアルデータ出力です。`0`か`1`、またはハイインピーダンスのとき`None`です                                                     |
| `sorq`                     | シリアル出力要求です。ワードがロードされた後の立ち上がりクロックで立ち上がり、最後のビットの後の立ち上がりクロックで下がります |
| `drq`                      | DMA要求です。DMAモードではRQMを立てる転送がこれを立て、転送を完了させるホストのアクセスがこれを下げます                        |
| `shifting_in`, `bits_in`   | 入力シフトレジスタと、進行中のワードについてそれが保持しているビット数です                                                     |
| `shifting_out`, `bits_out` | 出力シフトレジスタと、まだ送るべきビット数です                                                                                 |
| `msb_first`                | SOへの直前の転送が、最上位ビットから送るSOMを指定したか、最下位ビットから送るSOLを指定したかです                               |

ステータスワードのSICとSOCは、クリアのとき各ワードを16ビットに、セットのとき8ビットにします。届いたワード全体はビットが来た順に、最初のビットを最上位として`registers.si`に入り、SIACKを立てます。SIMからの転送はそのまま読み、SILからの転送はビットを反転して読み、どちらもSIACKをクリアします。SOへの転送はSOACKを立て、`soen`がローの状態での最初の立ち下がりクロックがワードをシフトレジスタに取り込み、SOACKをクリアします。

```python
from upd7725 import Cpu, Host

cpu = Cpu("upd7725", fill=0)
cpu.reset()
cpu.stores.load_program(bytes.fromhex("E970C9"))
pins = cpu.pins
pins.bits_out = 0
cpu.step()
print(cpu.registers.sr.soack, pins.sorq, pins.so)

pins.soen = False
sent = []
for _ in range(16):
    pins.sck = True
    cpu.step()
    pins.sck = False
    cpu.step()
    sent.append(pins.so)
print(cpu.registers.sr.soack, pins.sorq, "".join(map(str, sent)))

pins.sck = True
cpu.step()
print(pins.sorq)

cpu.reset()
cpu.stores.load_program(bytes.fromhex("C20007C48D06"))
cpu.run_for(2)
host = Host(cpu)
print(pins.drq, hex(host.take()), pins.drq)
```

```
True False None
False True 1010010111000011
False
True 0x1234 False
```

`E970C9`は`ld $A5C3,som`です。この転送はSOACKを立て、まだ何もワードを求めていません。イネーブルがローの状態で、16回の立ち下がりクロックがA5C3を最上位ビットから送ります。最初の立ち下がりがワードを取り込んでSOACKをクリアし、SORQは最後のビットの後の立ち上がりクロックまでハイのままです。シフトレジスタはシードが決める値を持って立ち上がるため、最初に`bits_out`を0にしています。誰もクリアしていないチップは、書き込まれたワードの前に、それまで保持していたものを送ります。2つ目のプログラムはDMAビットを立ててデータレジスタをロードし、これがDRQを立て、ホストが受け取る2バイト目がそれを下げます。

### モジュールの内容

| 名前                                                           | 内容                                                                                                                                                                                                                                                                                         |
| :------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `upd7725.MODELS`                                               | 2つの`Model`レコードで、正式名をキーとします                                                                                                                                                                                                                                                 |
| `upd7725.Model`                                                | `name`、`aliases`、`summary`、`counter_bits`、`table_bits`、`pointer_bits`、`stack_levels`と、派生値の`program_words`、`table_words`、`scratch_words`、`stack_pointer_bits`です。`build(*arguments, **options)`はこのモデルからチップを構築し、`Cpu`がモデルの後に受け取る引数を受け取ります |
| `upd7725.UNSET_SEED`                                           | シードを指定しないときに使われるシード、`0x5A5A5A5A`です                                                                                                                                                                                                                                     |
| `upd7725.scramble(size, seed=UNSET_SEED)`                      | `seed`から導出した`size`個の32ビット値で、電源投入時の状態の元になります                                                                                                                                                                                                                     |
| `upd7725.Cpu7725`                                              | `Cpu`がどちらのパーツにも返す、型チェック用のクラスです。パーツはモデルを選ぶ`Cpu`で作ります                                                                                                                                                                                                 |
| `upd7725.Store`, `upd7725.Stores`                              | 上で説明したストアのクラスです                                                                                                                                                                                                                                                               |
| `upd7725.Clock`                                                | 1サイクルずつのステップ実行で、[1サイクルずつ動かす](#driving-it-one-cycle-at-a-time)で説明します                                                                                                                                                                                            |
| `upd7725.decode`, `upd7725.disassemble`, `upd7725.Instruction` | プログラムワードの読み取りで、[実行せずに読む](#reading-without-running)で説明します                                                                                                                                                                                                         |
| `upd7725.Flags`                                                | フラグの集合です。`Flags.of(word)`は6ビットを展開し、`copy()`は複製を作ります                                                                                                                                                                                                                |
| `upd7725.Pins`                                                 | シリアルポートとDMA要求で、[シリアルポートとDMA要求](#the-serial-port-and-the-dma-request)で説明します                                                                                                                                                                                       |
| `upd7725.__version__`                                          | インストールされているバージョンです                                                                                                                                                                                                                                                         |

### エラー

| エラー              | 発生する条件                                                                                                                                                                                |
| :------------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `UnknownModelError` | `Cpu`にモデルが渡されなかったとき、どのモデルにも該当しない名前が渡されたとき、またはこのパッケージがモデル化を拒否するチップが渡されたときです。メッセージには受け付ける名前が列挙されます |
| `RunLimit`          | `run_until`が`limit`に達したときです                                                                                                                                                        |
| `ClockClosed`       | クロックを閉じた後に`Clock.tick()`が呼ばれたときです                                                                                                                                        |
| `NotWholeWords`     | `load_program`または`load_table`が、ワード数が整数にならないイメージを受け取ったときです                                                                                                    |
| `TooLarge`          | `load_program`または`load_table`が、ストアより長いイメージを受け取ったときです                                                                                                              |
| `NeverReady`        | チップが要求しないまま`Host.settle`が`limit`に達したときです                                                                                                                                |

6つとも`upd7725`からインポートできます。

### コマンドラインツール

| コマンド                               | 引数                                                                           | 終了コード                                                                                                         |
| :------------------------------------- | :----------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------- |
| `python3 upd7725/doctor.py`            | なし                                                                           | すべてのチェックに合格すれば0、それ以外は1                                                                         |
| `python3 -m conformance.instructions`  | `--corpus PATH`、`--cases N`、`--record`、`--retake`                           | 不一致がなければ0、1件でもあれば1、引数が不正なら2                                                                 |
| `python3 -m conformance.differential`  | `--from N`、`--cases N`（既定値5,000）、`--seconds S`                          | 2つの実装が一致すれば0、一致しなければ1、引数が不正なら2                                                           |
| `python3 -m conformance.speed`         | `--instructions N`（既定値200,000）、`--repeats N`（既定値7）                  | 下限以上なら0、下回れば1、引数が不正なら2                                                                          |
| `python3 -m conformance.documents`     | `--check`、`--only SUBSTRING`                                                  | すべてのドキュメントがダイジェストと一致すれば0、それ以外は1                                                       |
| `python3 -m conformance.quotes`        | なし                                                                           | すべての引用が見つかるか、ドキュメントが1つもなければ0、それ以外は1                                                |
| `python3 -m conformance.links`         | なし                                                                           | このファイル内のリンクが404または410を返せば1、それ以外は0                                                         |
| `python3 -m conformance.stack IMAGE`   | 大きい方のチップ用のイメージ1つ以上、プログラム16384ワードとテーブル2048ワード | すべてのイメージが8段のスタックに収まれば0、収まらないか上限を示せないものがあれば1、イメージがないか長さが違えば2 |
| `python3 -m conformance.package WHEEL` | 監査するwheel                                                                  | すべてのモジュールが含まれ、テストが1つも含まれなければ0、それ以外は1、wheelを指定しなければ2                      |

`--record`単独ではコーパスの上書きを拒否します。`--record --retake`は上書きを行い、修正されたハードウェアの事実を反映するときにだけ使います。

## 実時間の速度で動かす

チップは水晶が示す速度で動きます。`step()`は命令のコストを報告するので、ホストはチップを実時間のクロックに合わせられます。

```python
import time

from upd7725 import Cpu

HERTZ = 8_192_000
SLICE = 0.02

cpu = Cpu("upd7725")
cpu.reset()
per_slice = round(HERTZ * SLICE)
owed = 0

for _ in range(5):
    began = time.perf_counter()
    owed += per_slice
    owed -= cpu.run_for(owed)
    time.sleep(max(0.0, SLICE - (time.perf_counter() - began)))
```

8,192,000Hzは、データシートが122nsの命令サイクルを示すときのクロックです。このチップでは1命令が1サイクルなので、`run_for()`は予算ちょうどで止まり、`owed`は0のままです。それでもこのループは差分を持ち越すため、命令に数サイクルかかるチップ向けのループと同じ形になります。

`python3 -m conformance.speed`はモデルを計測し、その速度をシリコンの毎秒8,192,000命令に対する割合として出力します。毎秒250,000命令を下回ると失敗します。

<a id="driving-it-one-cycle-at-a-time"></a>

## 1サイクルずつ動かす

`Clock(cpu)`は任意の2つのサイクルの間でチップを止めます。ボードが読み出しに返す値を変えるのはこの位置です。

```python
from upd7725 import Clock, ClockClosed, Cpu

cpu = Cpu("upd7725", fill=0)
cpu.reset()

with Clock(cpu) as clock:
    clock.tick()
    print(clock.run_for(6), cpu.registers.pc, cpu.cycles)

try:
    clock.tick()
except ClockClosed as error:
    print(clock.closed, error)
```

```
7 7 11
True this clock has been closed
```

| 呼び出し                  | 動作                                                                                   |
| :------------------------ | :------------------------------------------------------------------------------------- |
| `tick()`                  | 次のサイクルの終わりまで実行して止まります。このクロックが実行したサイクル数を返します |
| `run_for(cycles)`         | `cycles`回ティックします。このクロックが実行したサイクル数を返します                   |
| `close()`                 | チップを止め、見つけたときの`on_cycle`を元に戻します。`with`ブロックを抜けると閉じます |
| `cycles`, `closed`, `cpu` | 実行したサイクル数、閉じているかどうか、チップです                                     |

クロックを反復処理するとティックします。ティック中にチップが送出した例外は`tick()`から送出され、クロックは閉じます。

NECは、このチップが1命令を外部クロック1サイクルで実行すると述べているため、サイクルの境界と命令の境界は同じ位置です。`Clock`はこのチップにファミリーの他のモデルと同じインターフェースを与えますが、それより細かい分解能はなく、`step()`のほうが高速です。Pythonはコールスタックを中断できないため、クロックはチップをスレッド上で実行し、各サイクルでブロックします。ブロックするのはそのスレッドだけです。クロックが一時停止している間に呼んだ`irq()`は、2回の`step()`の間と同じくすぐに動作し、そのサイクルは`cpu.cycles`に数えられますがティックには数えられません。

<a id="models"></a>

## モデル

命令セットは1つ、サイズは2通りです。どのストアも、そのアドレスを指定するレジスタとちょうど同じ長さです。

| 構築方法          | プログラムストア |  テーブル | スクラッチ | スタック | プログラムカウンタ |
| :---------------- | ---------------: | --------: | ---------: | -------: | -----------------: |
| `Cpu("upd7725")`  |  2048 x 24ビット | 1024 x 16 |   256 x 16 |        4 |           11ビット |
| `Cpu("upd96050")` | 16384 x 24ビット | 2048 x 16 |  2048 x 16 |        8 |           14ビット |

NECのデータシートとデータブックはuPD7725を扱っています。uPD96050についてのNECの文書は見つからなかったため、その4つの数値は二次資料に基づいています。レコードはそれに`verified: false`を付けており、[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md)に何があれば決着するかを記しています。

各チップは、NECが販売したときの型番で指定できます。大文字小文字、ハイフン、アンダースコアは区別しないため、`Cpu("uPD-77C25")`はuPD7725を構築します。

| 構築方法          | 別名                                      |
| :---------------- | :---------------------------------------- |
| `Cpu("upd7725")`  | `7725`, `upd77c25`, `77c25`, `necupd7725` |
| `Cpu("upd96050")` | `96050`, `upd96050gf`, `necupd96050`      |

```python
import upd7725

for name, model in upd7725.MODELS.items():
    sizes = (model.program_words, model.table_words, model.scratch_words, model.stack_levels)
    print(name, model.aliases, *sizes)

print(upd7725.Cpu("uPD-77C25").model.name, upd7725.Cpu("96050").model.name)

for asked in (None, "upd7720", "upd77p25", "upd7726"):
    try:
        upd7725.Cpu(asked)
    except upd7725.UnknownModelError as error:
        print(error)
```

```
upd7725 ('7725', 'upd77c25', '77c25', 'necupd7725') 2048 1024 256 4
upd96050 ('96050', 'upd96050gf', 'necupd96050') 16384 2048 2048 8
upd7725 upd96050
no model was named, and this package will not choose one for you. Name one of: upd7725, upd96050
upd7720 is not modelled here: the uPD7720 is the earlier part of the same family, and the reference this package is measured against does not implement it; a model of it here would have nothing behind it
upd77p25 is not modelled here: the uPD77P25 is the same processor with its program in erasable storage rather than masked, which changes how it is made rather than what it does; ask for upd7725 and load the program yourself
upd7726 is not a processor this package covers; it has upd7725, upd96050
```

ここで実装していない型番は、最も近いものに解決されることなく拒否されます。

<a id="reading-without-running"></a>

## 実行せずに読む

`decode(word, address=0)`はプログラムワードを1つ読み、`disassemble(words, address=0)`はワードごとに1つの`Instruction`を、`address`から番号を振って生成します。`Instruction`は`address`、`raw`、`text`を持ちます。

```python
from upd7725 import decode, disassemble

for found in disassemble([0xC00A81, 0x910040, 0x400000], 0x100):
    print(f"{found.address:04X}  {found.text}")

print(decode(0x8F0000), decode(0x158C51, 0x20).text)
```

```
0100  ld $002A,a
0101  jnza $0010
0102  rt
<Instruction 0000 jp ?078 $0000> add b idb rp->a dphm6
```

プログラムストアはワード単位でアドレス指定されるため、バイトではなくワードを受け取ります。24ビットのワードはすべて、`op`、`rt`、`jp`、`ld`の4つの形式のいずれかにデコードされます。条件フィールドがどの条件も指定しないジャンプは、そのフィールドを16進数で付けた`jp ?`として出力されるため、例外は発生しません。

## 何もクリーンな状態では始まらない

構築されたチップは、`pc`、`rp`、`dp`、`sp`、`k`、`l`、`m`、`n`、`a`、`b`、`tr`、`dr`とすべてのスタックスロットに、シードから導出した値を保持しています。これらをクリアする引数はありません。フラグ、ステータスワード、`si`、`so`、`trb`は0から始まり、すべてのストアは書き込まれるまで`fill`を読みます。

```python
from upd7725 import Cpu

powered = Cpu("upd7725")
print(hex(powered.registers.pc), hex(powered.registers.word("a")), powered.cycles)
print(hex(Cpu("upd7725", seed=7).registers.pc))
print(Cpu("upd7725", seed=7).registers.pc == Cpu("upd7725", seed=7).registers.pc)

powered.reset()
print(hex(powered.registers.pc), hex(powered.registers.word("a")), powered.cycles)
print(powered.flags_a, powered.registers.sr, hex(powered.stores.program[0]))
```

```
0x4eb 0xa2fb 0
0x438
True
0x0 0xa2fb 4
<Flags none> <Status none> 0x0
```

リセット前のプログラムカウンタは4EBを指しているため、誰もリセットしていないチップをステップ実行すると、シードが選んだアドレスから実行されます。データシートによればRESETはプログラムカウンタを0にし、`reset()`が変えるのはそれだけです。アキュムレータAはリセット後もA2FBを保持しています。

## 正しいか

コーパスは両方のチップで**1,120**通りのエンコーディングをフィールドごとに網羅し、シードから導出した20,000件のケースを加えています。各ケースはプロセッサ状態全体を設定し、1命令を実行し、その後の状態全体を記録します。モデルはそのすべてを再現します。**22,240命令、不一致なし**です。

```bash
python3 -m conformance.instructions
python3 -m conformance.differential --from 70000000 --cases 4000
python3 conformance/alu_flags.test.py
```

```
  22,240 instructions, 0 disagreed
  4,000 cases, the model and the reference agreed on every one
```

1つ目のコマンドはゲートで、リポジトリ外のものを何も必要としません。2つ目は、別の構造で書かれた第2の実装である[`conformance/reference.py`](conformance/reference.py)を、コーパスの終わりより先のケースでモデルと並べてステップ実行します。3つ目は16種類すべてのALU演算を、1989年のデータブックのTable 6と照合します。この表は各フラグについて、影響を受けるか、リセットされるか、保持されるか、不定かを示しています。モデルはすべてのセルと一致します。

[`conformance/hardware.json`](conformance/hardware.json)には、文書から取ったすべての事実が、出典の文とページとともに収められています。データシートとコーパスが食い違う場合はデータシートを優先し、コーパスを取り直します。これは3回起きており、[`conformance/pinned.json`](conformance/pinned.json)にそれぞれが記録されています。1つはスタックの深さで、出回っているどの実装も16としていますが、NECは4と記載しています。2つ目は、算術演算がデータ転送の転送先として自分自身のアキュムレータを指定する581件のケースで、NECはこの場合その演算がNOPになると述べています。3つ目はシリアルレジスタを通してワードを転送する1,895件のケースで、NECはSILが入力をビット反転して読むこと、SOへの転送がSOACKを立てること、SIからの転送がSIACKをクリアすることを記載しています。

コーパスはエミュレータから記録したものなので、NECが記載していない事柄についてのみ判断の根拠になります。[`conformance/divergences.json`](conformance/divergences.json)には2つの情報源が食い違う箇所がすべて収められています。[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md)には未解決の6つの問いと、それぞれを解決する計測が記されています。

## 開発に参加する

| 必要なもの                                               | 場所                                                                         |
| :------------------------------------------------------- | :--------------------------------------------------------------------------- |
| すべてのゲートと実行順序                                 | [CONTRIBUTING.md](CONTRIBUTING.md)                                           |
| コーディングエージェント向けの同じ内容                   | [AGENTS.md](AGENTS.md)                                                       |
| このリポジトリがファミリーの他のリポジトリと共有する基準 | [FAMILY.md](FAMILY.md)                                                       |
| バグ報告                                                 | [GitHub Issues](https://github.com/gufranco/nec-upd7725-96050-python/issues) |
| セキュリティ報告                                         | [SECURITY.md](SECURITY.md)                                                   |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx mypy@1.14.1
pnpm install --frozen-lockfile && pnpm run format:check
python3 -m coverage erase
for f in $(find upd7725 conformance -name '*.test.py' | sort); do python3 -m coverage run -a "$f"; done
python3 -m coverage report
```

各モジュールには`<module>.test.py`という名前のテストファイルが隣にあり、それぞれ単独で実行できます。カバレッジはステートメントとブランチの100%を必須とするゲートで、型は`mypy`のstrictで検査します。

## 参考文献

- NEC Electronics, _uPD77C25/uPD77P25 Digital Signal Processor Data Sheet_, Advance Product Information, August 1987。36ページ、1,299,452バイト、SHA-256 `d043be18d5cd21d90960ffb7e068e3b9a81647c8534a142f29eb11015733d042`。取得元：https://www.cryptomuseum.com/df/telefunken/e2000/files/uPD77C25.pdf
- NEC Electronics, _Digital Signal Processor and Speech Processor Products Data Book_, document 50052, 1989。388ページ、14,316,524バイト、SHA-256 `2f0190523de99938cc1da1c138f2c5b7f71573eb11bcb3b0dcdd1da1267e85ce`。取得元：https://bitsavers.trailing-edge.com/components/nec/_dataBooks/1989_DSP_and_Speech_Products_Data_Book.pdf
- ares、[`conformance/pinned.json`](conformance/pinned.json)が指定するコミット時点のもの。文書に記載のない命令レベルの動作を調べるために参照しました。コードは一切取り込んでいません。取得元：https://github.com/ares-emulator/ares

どちらの文書も再配布できず、このリポジトリには含まれていません。[`conformance/documents.json`](conformance/documents.json)にそれぞれのダイジェスト、サイズ、アドレスが記載されています。`python3 -m conformance.documents`は両方をgitが無視する`docs/`にダウンロードし、ダイジェストが一致しないファイルは拒否します。その後、`python3 -m conformance.quotes`がそれらの中から引用されたすべての文を探します。

どちらも印刷された本のスキャンなので、各ページを画像と、ファイルに含まれるテキストレイヤーの2通りで読みました。1987年版のテキストレイヤーは`the`を`lhe`と、ページ上で`8-bit`となっている箇所を`a-bit data pointer`と出力します。引用の横に記録されたページは、両方の読み取りが一致したページか、そのページを直接読んで確認したページです。データブックは2-33のようにセクションごとにページ番号を振っているため、そこから読み取った事実はセクションを明記しています。

## 引用

[CITATION.cff](CITATION.cff)は、パッケージのバージョンを刻むスクリプトによってリリースごとに更新されます。

## ライセンス

MIT。[LICENSE](LICENSE)を参照してください。
