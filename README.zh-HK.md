# NEC uPD7725

以 Python 實現的 NEC uPD7725 與 uPD96050 數碼訊號處理器，每個時鐘週期執行一條指令。每一項印刷事實都以 NEC 1987 年的數據表與 1989 年的數據手冊為準，每條指令執行後的完整處理器狀態則以一套錄製的語料庫為準。

[English](README.md) | [日本語](README.ja.md) | [简体中文](README.zh-Hans.md) | 繁體中文（香港）

[![CI](https://github.com/gufranco/nec-upd7725-96050-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/nec-upd7725-96050-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/nec-upd7725-96050-python)](https://github.com/gufranco/nec-upd7725-96050-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**2** 款晶片，逐欄位走訪 **1,120** 種編碼，比對 **22,240** 條指令，**0** 處分歧，**1,045** 項測試，**100%** 語句與分支覆蓋率，無任何依賴

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

這三個位元組是一個 24 位元程式字 `C00A81`。最高兩個位元選擇載入形式，接下來十六個位元攜帶數值 `002A`，最低四個位元指定累加器 A 為目的地。這一步花費一個週期。週期計數器讀數為 5，因為 `reset()` 花費了四個週期，即 NEC 給出的 RESET 脈衝最小寬度。

## 安裝

| 需求 | 版本 |
|:--|:--|
| Python | 3.12 或更新 |
| git | 任何版本 |

```bash
git clone https://github.com/gufranco/nec-upd7725-96050-python.git
cd nec-upd7725-96050-python
python3 upd7725/doctor.py
```

此套件除標準庫外不匯入任何模組。`python3 -m pip install git+https://github.com/gufranco/nec-upd7725-96050-python.git` 會安裝它，並將診斷腳本安裝為命令 `upd7725-doctor`。

診斷腳本檢查機器與檢出的程式碼，建立並重設兩款晶片，最後輸出一行。所有檢查通過時以 0 結束，否則以 1 結束。提交任何錯誤報告時，請貼上其完整輸出。

```
  4 checks, nothing to report
```

版本發佈遵循[語義化版本](https://semver.org/)，由 semantic-release 根據提交歷史產生。每個版本都會加上標籤，並列於[發佈頁面](https://github.com/gufranco/nec-upd7725-96050-python/releases)。

## 介面

`upd7725.Cpu(model, memory=None, *, fill=0, sources=None, seed=UNSET_SEED)` 建立一款晶片，已上電但未重設。

| 參數 | 含義 |
|:--|:--|
| `model` | 必填。取自[型號](#models)下表的型號名稱或別名。省略時會引發 `UnknownModelError` |
| `memory` | 要使用的 `Stores`。省略時，晶片按自身大小建立一個 |
| `fill` | 各儲存區中未寫入的字讀出的值，按儲存區寬度遮罩。省略時為 `0` |
| `sources` | 由 `"program"`、`"table"` 或 `"scratch"` 對應到以位址為參數之函式的映射。有來源的儲存區從來源讀取未寫入的字，而非使用 `fill` |
| `seed` | 暫存器的上電擾亂。以同一種子建立的兩款晶片持有相同數值 |

### 呼叫

| 呼叫 | 效果 | 回傳 |
|:--|:--|:--|
| `reset()` | RESET 腳位的作用：將程式計數器設為 0，將 `steps` 設為 0，並花費 4 個週期 | 該晶片 |
| `step()` | 執行一條指令 | 其花費的週期數，每條指令皆為 1 |
| `run_for(cycles)` | 執行完整指令，直至至少經過 `cycles` 個週期 | 花費的週期數 |
| `run_until(check, limit=None)` | 在 `check(cpu)` 為假時持續單步執行。執行 `limit` 條指令後引發 `RunLimit` | 該晶片 |
| `held()` | 晶片是否已停止推進其程式。此晶片沒有停機狀態 | `False` |
| `irq()` | 拉高中斷線。在上升沿且狀態字的 EI 位元已設定時，它會推入程式計數器、跳至 100H 並花費 1 個週期 | 中斷被接受時為 `True` |
| `lower_irq()` | 拉低中斷線，使下一次 `irq()` 成為新的邊沿 | `None` |
| `power_on(seed=UNSET_SEED)` | 與建構時一樣，以 `seed` 重新擾亂暫存器 | `None` |
| `spend()` | 計算一個週期並呼叫 `on_cycle`。晶片花費的每個週期都經過它 | `None` |

### 狀態

| 屬性 | 含義 |
|:--|:--|
| `model` | 建立該晶片所用的 `Model` 記錄 |
| `registers` | 暫存器檔，見下文 |
| `flags_a`, `flags_b` | 每個累加器的六個旗標：`s1`、`s0`、`c`、`z`、`ov1`、`ov0`。`int()` 將它們打包，`ov0` 在位元 0，`s1` 在位元 5 |
| `stores` | 三個儲存區，見下文 |
| `cycles` | 自晶片建立以來的週期數。重設會增加它 |
| `steps` | 自上次重設以來的指令數 |
| `irq_line` | 以電平表示的中斷線 |
| `on_cycle` | `None`，或在每個週期後以無參數呼叫的函式 |

`registers.pc`、`rp`、`dp` 與 `sp` 會將寫入的值遮罩至晶片自身的寬度。`k`、`l`、`m`、`n`、`a` 與 `b` 持有 16 位元，讀回時為有號數。`registers.word(name)` 將其中任何一個讀作無號 16 位元字。`tr`、`trb`、`dr`、`si` 與 `so` 是普通整數。`registers.stack` 是長度與晶片堆疊相同的清單，`registers.sr` 是狀態字：位元 `p0`、`p1`、`ei`、`sic`、`soc`、`drc`、`dma`、`usf0`、`usf1`、`rqm` 與 `drs` 位於數據表 Figure 3 所示的位置，`int(registers.sr)` 將它們讀作一個字，`registers.sr.assign(word)` 則從一個字設定它們。`registers.sr.siack` 與 `registers.sr.soack` 是串列輸入與輸出的應答，SIACK 與 SOACK 條件跳轉會讀取它們。本套件不會設定它們，因此使用這些跳轉的主機須自行設定；兩者皆不屬於狀態字。

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

7FFF 加 1 會溢位至符號位元。累加器 A 以有號數讀作 -32768，以字讀作 8000，而該加法設定了兩個溢位旗標與兩個符號旗標。

### 執行、中斷與週期鈎子

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

第一個字 `ld $0080,sr` 設定 EI 位元，其後的零字不做任何事。鈎子在重設之後才設定，因此它看到 16 個指令週期，而看不到 4 個重設週期。第一次 `irq()` 是上升沿，因此被接受。第二次發現中斷線已是高電平，因此不被接受。`lower_irq()` 之後，下一次又被接受，此時程式位於 100H，所以推入的是 100H。`RunLimit` 會指出計數及以十六進制表示的程式計數器。

### 儲存區

`cpu.stores` 是一個 `Stores`，持有 `program`、`table` 與 `scratch`。每一個都是 `Store`，長度恰好與為其定址的暫存器相符。

| 名稱 | 內容 |
|:--|:--|
| `Stores(program_words, table_words, scratch_words, fill=0, sources=None)` | 按指定大小建立的三個儲存區 |
| `stores.program`, `stores.table`, `stores.scratch` | 24 位元程式字、16 位元表格字、16 位元臨時字 |
| `stores.load_program(image)` | 從位址 0 開始寫入映像檔，每三個位元組一個字，高位元組在前 |
| `stores.load_table(image)` | 表格的相同操作，每兩個位元組一個字 |
| `stores.read_byte(at)`, `stores.write_byte(at, value)` | 臨時儲存區的一個位元組。偶數位址是字 `at // 2` 的低位元組，奇數位址是高位元組 |
| `Store(words, bits, fill=0, source=None)` | 一個儲存區。`store[at]` 讀寫一個字，`at` 以長度取模，值遮罩至 `bits` |
| `store.changed()` | 所有寫入值與之前讀出值不同的字，按位址列出 |
| `store.words`, `store.bits`, `store.mask`, `store.source` | 長度、寬度、該寬度的遮罩，以及來源函式或 `None` |

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

在 uPD7725 上，表格位址 1024 會回繞至 0，因為其表格長 1024 字。載入失敗時，會在寫入任何內容之前引發錯誤。

### 主機端

主機看到兩個位址：`upd7725.DATA`，即 0；以及 `upd7725.STATUS`，即 1。`upd7725.Host(cpu)` 驅動它們。

| 呼叫 | 效果 |
|:--|:--|
| `asking` | RQM 位元已設定時為 True，即晶片等待主機的時候 |
| `settle(limit=200000)` | 單步執行晶片直至它發出請求。回傳單步執行的指令數，超過 `limit` 後引發 `NeverReady` |
| `read(address)` | `STATUS` 讀取狀態字的高 8 位元。`DATA` 讀取數據暫存器的一個位元組，並在傳輸完成時清除 RQM。任何其他位址讀出 0 |
| `write(address, value)` | `DATA` 寫入數據暫存器的一個位元組。寫入任何其他位址都不起作用，因為狀態字是唯讀的 |
| `send_bytes(values, limit=200000)`, `take_bytes(count, limit=200000)` | 每個位元組之前先等待晶片發出請求，然後寫入或讀取它 |
| `send(word, limit=200000)`, `take(limit=200000)` | 一個 16 位元字，分為兩個位元組，低位元組在前 |

DRC 位元清除時，數據暫存器以每次一個位元組的方式搬移 16 位元，DRS 標示已搬移的那一半。DRC 設定時，它搬移 8 位元。

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

程式只有一個字：`ld $1234,dr`。寫入數據暫存器會設定 RQM，即 `STATUS` 位元組的位元 7。主機分兩次讀取取得 1234，第二次讀取清除 RQM。重設後，同一個字再次發出請求，主機改為送入 BEEF。之後再沒有任何請求，因此最後的 `settle` 放棄。

### 模組內容

| 名稱 | 內容 |
|:--|:--|
| `upd7725.MODELS` | 兩筆 `Model` 記錄，以標準名稱為鍵 |
| `upd7725.Model` | `name`、`aliases`、`summary`、`counter_bits`、`table_bits`、`pointer_bits`、`stack_levels`，以及衍生的 `program_words`、`table_words`、`scratch_words` 與 `stack_pointer_bits`。`build(*arguments, **options)` 以它建立晶片，接受 `Cpu` 在型號之後接受的參數 |
| `upd7725.UNSET_SEED` | 未指定種子時使用的種子，`0x5A5A5A5A` |
| `upd7725.scramble(size, seed=UNSET_SEED)` | 由 `seed` 衍生的 `size` 個 32 位元值，為上電狀態的來源 |
| `upd7725.Store`, `upd7725.Stores` | 上述的儲存區類別 |
| `upd7725.Clock` | 每次步進一個週期，見[逐個週期驅動](#driving-it-one-cycle-at-a-time) |
| `upd7725.decode`, `upd7725.disassemble`, `upd7725.Instruction` | 讀取程式字，見[不執行而讀取](#reading-without-running) |
| `upd7725.Flags` | 旗標集合。`Flags.of(word)` 解開六個位元，`copy()` 複製一個集合 |
| `upd7725.__version__` | 已安裝的版本 |

### 錯誤

| 錯誤 | 引發時機 |
|:--|:--|
| `UnknownModelError` | `Cpu` 未取得型號、取得沒有任何型號使用的名稱，或取得本套件拒絕建模的晶片。訊息會列出可接受的名稱 |
| `RunLimit` | `run_until` 達到其 `limit` |
| `ClockClosed` | 時鐘關閉後仍呼叫 `Clock.tick()` |
| `NotWholeWords` | `load_program` 或 `load_table` 取得的映像檔不是整數個字 |
| `TooLarge` | `load_program` 或 `load_table` 取得的映像檔比儲存區長 |
| `NeverReady` | `Host.settle` 達到其 `limit` 時晶片仍未發出請求 |

六者皆可從 `upd7725` 匯入。

### 命令列工具

| 命令 | 參數 | 結束碼 |
|:--|:--|:--|
| `python3 upd7725/doctor.py` | 無 | 所有檢查通過時為 0，否則為 1 |
| `python3 -m conformance.instructions` | `--corpus PATH`、`--cases N`、`--record`、`--retake` | 無分歧時為 0，有任何分歧時為 1，參數錯誤時為 2 |
| `python3 -m conformance.differential` | `--from N`、`--cases N` 預設為 5,000、`--seconds S` | 兩個實現一致時為 0，不一致時為 1，參數錯誤時為 2 |
| `python3 -m conformance.speed` | `--instructions N` 預設為 200,000，`--repeats N` 預設為 7 | 達到或高於下限時為 0，低於下限時為 1，參數錯誤時為 2 |
| `python3 -m conformance.documents` | `--check`、`--only SUBSTRING` | 每份文件都與其摘要相符時為 0，否則為 1 |
| `python3 -m conformance.quotes` | 無 | 每段引文都找到或沒有任何文件時為 0，否則為 1 |
| `python3 -m conformance.links` | 無 | 本檔案中有連結回應 404 或 410 時為 1，否則為 0 |
| `python3 -m conformance.package WHEEL` | 要審核的 wheel | 每個模組都已打包且沒有打包任何測試時為 0，否則為 1，未指定 wheel 時為 2 |

單獨使用 `--record` 會拒絕覆寫語料庫。`--record --retake` 會覆寫它，且只用於帶入一項已更正的硬件事實。

## 以真實速度執行

晶片按其晶體所定的速度執行。`step()` 報告一條指令的花費，因此主機可以讓晶片跟隨真實時鐘。

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

8,192,000 Hz 是數據表標示 122 ns 指令週期時所用的時鐘。此晶片上一條指令就是一個週期，所以 `run_for()` 恰好用完預算，`owed` 保持為 0。迴圈仍然結轉差額，使它與指令需要多個週期的晶片所用的迴圈寫法相同。

`python3 -m conformance.speed` 測量模型，並以矽晶片每秒 8,192,000 條指令的比例列印其速率。低於每秒 250,000 條指令時失敗。

<a id="driving-it-one-cycle-at-a-time"></a>

## 逐個週期驅動

`Clock(cpu)` 讓晶片在任意兩個週期之間停下，電路板正是在此處改變一次讀取將得到的回應。

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

| 呼叫 | 效果 |
|:--|:--|
| `tick()` | 執行至下一個週期結束並停止。回傳此時鐘已執行的週期數 |
| `run_for(cycles)` | `cycles` 個節拍。回傳此時鐘已執行的週期數 |
| `close()` | 停止晶片，並放回它原先找到的 `on_cycle`。離開 `with` 區塊時會將其關閉 |
| `cycles`, `closed`, `cpu` | 已執行的週期數、是否已關閉，以及該晶片 |

迭代時鐘即令其前進一個節拍。晶片在節拍期間引發的例外會從 `tick()` 拋出，時鐘隨之關閉。

NEC 指明該晶片在一個外部時鐘週期內執行一條指令，因此週期邊界與指令邊界是同一位置。`Clock` 為此晶片提供與家族其他成員相同的介面，但沒有更細的解析度，`step()` 是較快的呼叫。時鐘在一條執行緒上執行晶片，並在每個週期阻塞它，因為 Python 無法暫停呼叫堆疊。

<a id="models"></a>

## 型號

同一指令集，兩種大小。每個儲存區的長度都恰好與為其定址的暫存器相符。

| 建立方式 | 程式儲存區 | 表格 | 臨時 | 堆疊 | 程式計數器 |
|:--|--:|--:|--:|--:|--:|
| `Cpu("upd7725")` | 2048 x 24 位元 | 1024 x 16 | 256 x 16 | 4 | 11 位元 |
| `Cpu("upd96050")` | 16384 x 24 位元 | 2048 x 16 | 2048 x 16 | 8 | 14 位元 |

NEC 的數據表與數據手冊涵蓋 uPD7725。未能找到任何關於 uPD96050 的 NEC 文件，因此其四項數字依據的是二手資料。該記錄將其標為 `verified: false`，[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) 說明了甚麼能確定這些數字。

每款晶片都可用 NEC 銷售時的型號來指定。大小寫、連字號與底線無關緊要，因此 `Cpu("uPD-77C25")` 會建立 uPD7725。

| 建立方式 | 其他可用名稱 |
|:--|:--|
| `Cpu("upd7725")` | `7725`、`upd77c25`、`77c25`、`necupd7725` |
| `Cpu("upd96050")` | `96050`、`upd96050gf`、`necupd96050` |

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

沒有任何實現對應的型號會被拒絕，而不會解析為最接近的型號。

<a id="reading-without-running"></a>

## 不執行而讀取

`decode(word, address=0)` 讀取一個程式字，`disassemble(words, address=0)` 為每個字產生一個 `Instruction`，從 `address` 開始編號。`Instruction` 帶有 `address`、`raw` 與 `text`。

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

它接受字而非位元組，因為程式儲存區以字定址。每個 24 位元字都會解碼為四種形式之一：`op`、`rt`、`jp` 與 `ld`。條件欄位未指定任何條件的跳轉會顯示為 `jp ?`，並以十六進制列出該欄位，因此不會引發錯誤。

## 沒有任何東西以乾淨狀態開始

建立後的晶片在 `pc`、`rp`、`dp`、`sp`、`k`、`l`、`m`、`n`、`a`、`b`、`tr`、`dr` 及每個堆疊槽中持有由種子衍生的值。沒有任何參數可以清除它們。旗標、狀態字、`si`、`so` 與 `trb` 從 0 開始，每個儲存區在寫入前都讀出 `fill`。

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

重設前程式計數器指向 4EB，因此對未經重設的晶片單步執行，會從種子選定的位址開始。數據表指出 RESET 將程式計數器設為 0，而這就是 `reset()` 所改變的全部：之後累加器 A 仍持有 A2FB。

## 它是否正確

語料庫在兩款晶片上逐欄位走訪 **1,120** 種編碼，並加入 20,000 個由種子衍生的案例。每個案例設定完整的處理器狀態，執行一條指令，並記錄其後的完整狀態。模型重現了全部案例：**22,240 條指令，沒有分歧**。

```bash
python3 -m conformance.instructions
python3 -m conformance.differential --from 70000000 --cases 4000
python3 conformance/alu_flags.test.py
```

```
  22,240 instructions, 0 disagreed
  4,000 cases, the model and the reference agreed on every one
```

第一條命令是關卡檢查，除本儲存庫外不需要任何東西。第二條命令單步執行 [`conformance/reference.py`](conformance/reference.py)，這是以不同結構編寫的第二個實現，在語料庫結束之後的案例上與模型對照。第三條命令以 1989 年數據手冊的 Table 6 驅動全部十六種 ALU 運算，該表列明每個旗標是受影響、重設、保持還是不確定。模型與表中每一格都一致。

[`conformance/hardware.json`](conformance/hardware.json) 持有取自文件的每一項事實，連同其出處的句子與頁碼。數據表與語料庫不一致時，以數據表為準，並重新錄製語料庫。這種情況發生過兩次，[`conformance/pinned.json`](conformance/pinned.json) 記錄了這兩次：一次是堆疊深度，業界所有實現都定為十六，而 NEC 印的是四；另一次是 581 個案例，其中算術運算將自己的累加器指定為數據搬移的目的地，NEC 指出這會使該運算變成 NOP。

語料庫是從模擬器錄製的，因此只裁定 NEC 未印出的內容。[`conformance/divergences.json`](conformance/divergences.json) 持有兩個來源出現分歧的每一處。[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) 列出三個仍未解決的問題，以及能解決每個問題的測量。

## 參與開發

| 需要 | 位置 |
|:--|:--|
| 每道關卡檢查及其執行順序 | [CONTRIBUTING.md](CONTRIBUTING.md) |
| 供編程代理使用的相同內容 | [AGENTS.md](AGENTS.md) |
| 本儲存庫與家族其他成員共用的標準 | [FAMILY.md](FAMILY.md) |
| 錯誤報告 | [GitHub Issues](https://github.com/gufranco/nec-upd7725-96050-python/issues) |
| 安全報告 | [SECURITY.md](SECURITY.md) |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx mypy@1.14.1
pnpm install --frozen-lockfile && pnpm run format:check
python3 -m coverage erase
for f in $(find upd7725 conformance -name '*.test.py' | sort); do python3 -m coverage run -a "$f"; done
python3 -m coverage report
```

每個模組旁都有一個名為 `<module>.test.py` 的測試檔案，每個都能獨立執行。覆蓋率是一道硬性關卡，要求 100% 語句與分支覆蓋，型別檢查為嚴格模式的 `mypy`。

## 參考資料

- NEC Electronics，*uPD77C25/uPD77P25 Digital Signal Processor Data Sheet*，Advance Product Information，1987 年 8 月。36 頁，1,299,452 位元組，SHA-256 `d043be18d5cd21d90960ffb7e068e3b9a81647c8534a142f29eb11015733d042`。取自 https://www.cryptomuseum.com/df/telefunken/e2000/files/uPD77C25.pdf
- NEC Electronics，*Digital Signal Processor and Speech Processor Products Data Book*，文件編號 50052，1989 年。388 頁，14,316,524 位元組，SHA-256 `2f0190523de99938cc1da1c138f2c5b7f71573eb11bcb3b0dcdd1da1267e85ce`。取自 https://bitsavers.trailing-edge.com/components/nec/_dataBooks/1989_DSP_and_Speech_Products_Data_Book.pdf
- ares，https://github.com/ares-emulator/ares ，取 [`conformance/pinned.json`](conformance/pinned.json) 指定的提交，用於研究文件未提供的指令層級行為。未取用任何程式碼。

兩份文件均不可再分發，也都不在本儲存庫中。[`conformance/documents.json`](conformance/documents.json) 載有每份文件的摘要、大小與位址。`python3 -m conformance.documents` 會將兩者下載到 git 忽略的 `docs/`，並拒絕摘要不符的檔案。`python3 -m conformance.quotes` 隨後在其中找出每一個被引用的句子。

兩者都是印刷書籍的掃描件，因此每一頁都讀了兩次：一次從影像讀取，一次從檔案附帶的文字層讀取。1987 年的文字層把 `the` 印成 `lhe`，並在頁面寫著 `8-bit` 之處印成 `a-bit data pointer`。引文旁記錄的頁碼，是兩種讀法一致的頁，或經直接閱讀該頁確認的頁。數據手冊按章節編排頁碼，例如 2-33，因此從中讀取的事實會註明章節。

## 引用本專案

[CITATION.cff](CITATION.cff) 會在每次發佈時，由蓋印套件版本的腳本更新。

## 授權

MIT。見 [LICENSE](LICENSE)。
