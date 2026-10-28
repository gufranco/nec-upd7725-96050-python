# NEC uPD7725

用 Python 实现的 NEC uPD7725 与 uPD96050 数字信号处理器，每个时钟周期执行一条指令。每一项印刷事实都以 NEC 1987 年的数据表和 1989 年的数据手册为准，每条指令执行后的完整处理器状态都以一份录制的语料库为准。

[English](README.md) | [日本語](README.ja.md) | 简体中文 | [繁體中文（香港）](README.zh-HK.md)

[![CI](https://github.com/gufranco/nec-upd7725-96050-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/nec-upd7725-96050-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/nec-upd7725-96050-python)](https://github.com/gufranco/nec-upd7725-96050-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**2** 个器件，**1,120** 种编码逐字段遍历，**22,240** 条指令比对，**0** 处不一致，**1,202** 个测试，**100%** 语句与分支覆盖率，无任何依赖

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

这三个字节是一个 24 位程序字 `C00A81`。最高两位选择加载形式，接下来的十六位携带值 `002A`，最低四位指定累加器 A 为目标。这一步耗费一个周期。周期计数器读数为 5，因为 `reset()` 耗费了 NEC 给出的 RESET 最小脉冲宽度，即四个周期。

## 安装

| 要求   | 版本        |
| :----- | :---------- |
| Python | 3.12 或更高 |
| git    | 任意        |

```bash
git clone https://github.com/gufranco/nec-upd7725-96050-python.git
cd nec-upd7725-96050-python
python3 upd7725/doctor.py
```

本包只导入标准库中的内容。`python3 -m pip install git+https://github.com/gufranco/nec-upd7725-96050-python.git` 会安装本包，并将诊断脚本安装为命令 `upd7725-doctor`。

诊断脚本检查本机和检出的代码，构建并复位两个器件，最后输出一行结果。所有检查都通过时退出码为 0，否则为 1。提交缺陷报告时请粘贴其完整输出。

```
  4 checks, nothing to report
```

版本发布遵循[语义化版本](https://semver.org/)，由 semantic-release 根据提交历史生成。每个版本都打了标签，并列在[发布页面](https://github.com/gufranco/nec-upd7725-96050-python/releases)上。

## 接口

`upd7725.Cpu(model, memory=None, *, fill=0, sources=None, seed=UNSET_SEED)` 构建一个已上电、未复位的器件。

| 参数      | 含义                                                                                                                           |
| :-------- | :----------------------------------------------------------------------------------------------------------------------------- |
| `model`   | 必填。取自 [Models](#models) 下表格中的型号名或别名。省略时抛出 `UnknownModelError`                                            |
| `memory`  | 要使用的 `Stores`。省略时，器件按自身尺寸构建一个                                                                              |
| `fill`    | 每个存储区中未写入的字读出的值，按该存储区的宽度掩码。省略时为 `0`                                                             |
| `sources` | 从 `"program"`、`"table"` 或 `"scratch"` 到一个以地址为参数的函数的映射。有来源的存储区从该函数读取未写入的字，而不是读 `fill` |
| `seed`    | 寄存器的上电扰乱值。用同一个种子构建的两个器件持有相同的值                                                                     |

### 调用

| 调用                           | 作用                                                                                        | 返回值                         |
| :----------------------------- | :------------------------------------------------------------------------------------------ | :----------------------------- |
| `reset()`                      | 即 RESET 引脚的作用：把程序计数器设为 0，把 `steps` 设为 0，并耗费 4 个周期                 | 该器件                         |
| `step()`                       | 执行一条指令                                                                                | 它耗费的周期数，每条指令都是 1 |
| `run_for(cycles)`              | 执行完整的指令，直到至少经过 `cycles` 个周期                                                | 耗费的周期数                   |
| `run_until(check, limit=None)` | 在 `check(cpu)` 为假时单步执行。执行 `limit` 条指令后抛出 `RunLimit`                        | 该器件                         |
| `held()`                       | 器件是否已停止推进其程序。本器件没有停机                                                    | `False`                        |
| `irq()`                        | 拉高中断线。在上升沿，若状态字的 EI 位已置位，则压入程序计数器，跳转到 100H 并耗费 1 个周期 | 中断被响应时为 `True`          |
| `lower_irq()`                  | 拉低中断线，使下一次 `irq()` 成为新的边沿                                                   | `None`                         |
| `power_on(seed=UNSET_SEED)`    | 按 `seed` 重新扰乱寄存器，与构建时相同                                                      | `None`                         |
| `spend()`                      | 计入一个周期并调用 `on_cycle`。器件耗费的每个周期都经过它                                   | `None`                         |

### 状态

| 属性                 | 含义                                                                                                          |
| :------------------- | :------------------------------------------------------------------------------------------------------------ |
| `model`              | 构建该器件所用的 `Model` 记录                                                                                 |
| `registers`          | 寄存器组，见下文                                                                                              |
| `flags_a`, `flags_b` | 每个累加器的六个标志：`s1`、`s0`、`c`、`z`、`ov1`、`ov0`。`int()` 将它们打包，`ov0` 在第 0 位，`s1` 在第 5 位 |
| `stores`             | 三个存储区，见下文                                                                                            |
| `cycles`             | 自器件构建以来的周期数。复位会累加到其中                                                                      |
| `steps`              | 自上次复位以来的指令数                                                                                        |
| `irq_line`           | 以电平表示的中断线                                                                                            |
| `on_cycle`           | `None`，或每个周期后以无参数方式调用的函数                                                                    |
| `pins`               | 串行端口与 DMA 请求，见[串行端口与 DMA 请求](#the-serial-port-and-the-dma-request)                            |

`registers.pc`、`rp`、`dp` 和 `sp` 会把写入的值按器件自身的宽度掩码。`k`、`l`、`m`、`n`、`a` 和 `b` 持有 16 位，读回时为有符号数。`registers.word(name)` 把其中任意一个读作无符号 16 位字。`tr`、`trb`、`dr`、`si` 和 `so` 是普通整数。`registers.stack` 是一个与器件堆栈等长的列表，`registers.sr` 是状态字：`p0`、`p1`、`ei`、`sic`、`soc`、`drc`、`dma`、`usf0`、`usf1`、`rqm` 和 `drs` 各位位于数据表 Figure 3 所示的位置，`int(registers.sr)` 把它们读作一个字，`registers.sr.assign(word)` 从一个字设置它们。`registers.sr.siack` 和 `registers.sr.soack` 是串行输入和输出的应答，SIACK 和 SOACK 条件跳转读取它们。两者都不属于状态字。串行输入收到一个完整的字会置位 `siack`，从 SI 传送会清除它。传送到 SO 会置位 `soack`，字移入移位寄存器时会清除它。

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

7FFF 加 1 溢出到符号位。累加器 A 按有符号数读为 -32768，按字读为 8000，这次加法置位了两个溢出标志和两个符号标志。

### 运行、中断与周期钩子

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

第一个字 `ld $0080,sr` 置位 EI 位，其后的零字什么也不做。钩子是在复位之后设置的，所以它看到了 16 个指令周期，而没有看到 4 个复位周期。第一次 `irq()` 是上升沿，中断被响应。第二次发现中断线已经为高，中断不被响应。`lower_irq()` 之后，下一次又被响应，此时位于 100H，所以压入的是 100H。`RunLimit` 用十六进制给出计数和程序计数器。

### 存储区

`cpu.stores` 是一个 `Stores`，持有 `program`、`table` 和 `scratch`。每一个都是 `Store`，长度恰好等于为其寻址的寄存器所能覆盖的范围。

| 名称                                                                      | 内容                                                                  |
| :------------------------------------------------------------------------ | :-------------------------------------------------------------------- |
| `Stores(program_words, table_words, scratch_words, fill=0, sources=None)` | 按给定尺寸构建的三个存储区                                            |
| `stores.program`, `stores.table`, `stores.scratch`                        | 24 位程序字、16 位表字、16 位暂存字                                   |
| `stores.load_program(image)`                                              | 从地址 0 开始写入一个镜像，三个字节构成一个字，高字节在前             |
| `stores.load_table(image)`                                                | 对表做同样的事，两个字节构成一个字                                    |
| `stores.read_byte(at)`, `stores.write_byte(at, value)`                    | 暂存区的一个字节。偶数地址是字 `at // 2` 的低字节，奇数地址是高字节   |
| `Store(words, bits, fill=0, source=None)`                                 | 一个存储区。`store[at]` 读写一个字，`at` 按长度取模，值按 `bits` 掩码 |
| `store.changed()`                                                         | 按地址列出所有写入后与先前读出值不同的字                              |
| `store.words`, `store.bits`, `store.mask`, `store.source`                 | 长度、宽度、该宽度的掩码，以及来源函数或 `None`                       |

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

在 uPD7725 上，表地址 1024 回绕到 0，因为它的表长 1024 个字。加载失败时会在写入任何内容之前抛出异常。

### 主机端

主机看到两个地址：`upd7725.DATA`，值为 0；`upd7725.STATUS`，值为 1。`upd7725.Host(cpu)` 驱动它们。

| 调用                                                                  | 作用                                                                                              |
| :-------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------ |
| `asking`                                                              | RQM 位置位时为 True，即器件等待主机的时候                                                         |
| `settle(limit=200000)`                                                | 单步执行器件，直到它发出请求。返回执行的指令数，超过 `limit` 后抛出 `NeverReady`                  |
| `read(address)`                                                       | `STATUS` 读取状态字的高 8 位。`DATA` 读取数据寄存器的一个字节，传输完成时清除 RQM。其他地址读出 0 |
| `write(address, value)`                                               | `DATA` 写入数据寄存器的一个字节。写入其他地址不起作用，因为状态字是只读的                         |
| `send_bytes(values, limit=200000)`, `take_bytes(count, limit=200000)` | 每个字节之前先等待就绪，然后写入或读出该字节                                                      |
| `send(word, limit=200000)`, `take(limit=200000)`                      | 以两个字节传送一个 16 位字，低字节在前                                                            |

DRC 位清零时，数据寄存器传送 16 位，每次一个字节，DRS 标记已传送的那一半。DRC 置位时传送 8 位。

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

程序只有一个字 `ld $1234,dr`。写入数据寄存器会置位 RQM，即 `STATUS` 处字节的第 7 位。主机分两次读取 1234，第二次读取清除 RQM。复位之后同一个字再次发出请求，主机发送 BEEF 取而代之。其后没有任何指令发出请求，所以最后一次 `settle` 放弃。

<a id="the-serial-port-and-the-dma-request"></a>

### 串行端口与 DMA 请求

`cpu.pins` 是一个 `Pins`，持有主机总线之外的各条线。输入是主机在周期之间设置的电平，器件在每个周期的最后对它们采样一次。边沿是相对上一次采样所见电平的变化。

| 属性                       | 含义                                                                               |
| :------------------------- | :--------------------------------------------------------------------------------- |
| `sck`                      | 串行时钟输入。上升沿移入一位，下降沿移出一位                                       |
| `si`, `sien`               | 串行数据输入及其使能。只有 `sien` 为低时才移入位                                   |
| `soen`                     | 串行输出使能。只有它为低时才移出位                                                 |
| `so`                       | 串行数据输出：`0` 或 `1`，处于高阻态时为 `None`                                    |
| `sorq`                     | 串行输出请求。字装入后的上升时钟沿使它升起，最后一位之后的上升时钟沿使它落下       |
| `drq`                      | DMA 请求。在 DMA 模式下，置位 RQM 的传送会升起它，完成传输的那次主机访问会使它落下 |
| `shifting_in`, `bits_in`   | 输入移位寄存器，以及它持有的当前字的位数                                           |
| `shifting_out`, `bits_out` | 输出移位寄存器，以及它仍需发送的位数                                               |
| `msb_first`                | 最近一次传送到 SO 时指定的是先发最高位的 SOM，还是先发最低位的 SOL                 |

状态字中的 SIC 和 SOC 为零时把每个字设为 16 位，置位时设为 8 位。完整到达的字按位到达的顺序放入 `registers.si`，第一位在最高位，并置位 SIACK。从 SIM 传送按原样读取，从 SIL 传送按位反转读取，两者都会清除 SIACK。传送到 SO 会置位 SOACK，在 `soen` 为低时的第一个下降时钟沿把字取入移位寄存器并清除 SOACK。

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

`E970C9` 是 `ld $A5C3,som`。该传送置位 SOACK，此时还没有任何东西索取这个字。使能为低时，十六个下降时钟沿把 A5C3 从最高位开始发出。其中第一个取入该字并清除 SOACK，SORQ 一直保持高电平，直到最后一位之后的上升时钟沿。先把 `bits_out` 设为 0，是因为移位寄存器上电时持有种子决定的值，所以没有人清零的器件会先发出它之前持有的内容，然后才是写入的字。第二段程序置位 DMA 位并装入数据寄存器，这会升起 DRQ，主机取走的第二个字节使它落下。

### 模块内容

| 名称                                                           | 内容                                                                                                                                                                                                                                                             |
| :------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `upd7725.MODELS`                                               | 两个 `Model` 记录，以规范名称为键                                                                                                                                                                                                                                |
| `upd7725.Model`                                                | `name`、`aliases`、`summary`、`counter_bits`、`table_bits`、`pointer_bits`、`stack_levels`，以及派生的 `program_words`、`table_words`、`scratch_words` 和 `stack_pointer_bits`。`build(*arguments, **options)` 据此构建一个器件，接受 `Cpu` 在型号之后接受的参数 |
| `upd7725.UNSET_SEED`                                           | 未给出种子时使用的种子，`0x5A5A5A5A`                                                                                                                                                                                                                             |
| `upd7725.scramble(size, seed=UNSET_SEED)`                      | 由 `seed` 派生的 `size` 个 32 位值，是上电状态的来源                                                                                                                                                                                                             |
| `upd7725.Cpu7725`                                              | `Cpu` 为任一部件返回的类，用于类型检查。部件用 `Cpu` 构建，由它选择型号                                                                                                                                                                                          |
| `upd7725.Store`, `upd7725.Stores`                              | 上文描述的存储区类                                                                                                                                                                                                                                               |
| `upd7725.Clock`                                                | 每次单步一个周期，见[逐周期驱动](#driving-it-one-cycle-at-a-time)                                                                                                                                                                                                |
| `upd7725.decode`, `upd7725.disassemble`, `upd7725.Instruction` | 读取程序字，见[不运行而读取](#reading-without-running)                                                                                                                                                                                                           |
| `upd7725.Flags`                                                | 标志集合。`Flags.of(word)` 解包六个位，`copy()` 复制一份                                                                                                                                                                                                         |
| `upd7725.Pins`                                                 | 串行端口与 DMA 请求，见[串行端口与 DMA 请求](#the-serial-port-and-the-dma-request)                                                                                                                                                                               |
| `upd7725.__version__`                                          | 已安装的版本                                                                                                                                                                                                                                                     |

### 错误

| 错误                | 抛出时机                                                                                     |
| :------------------ | :------------------------------------------------------------------------------------------- |
| `UnknownModelError` | `Cpu` 没有得到型号、得到的名称不属于任何型号，或得到本包拒绝建模的器件。消息列出可接受的名称 |
| `RunLimit`          | `run_until` 达到其 `limit`                                                                   |
| `ClockClosed`       | 时钟关闭后又调用了 `Clock.tick()`                                                            |
| `NotWholeWords`     | `load_program` 或 `load_table` 得到的镜像不是整数个字                                        |
| `TooLarge`          | `load_program` 或 `load_table` 得到的镜像比存储区长                                          |
| `NeverReady`        | `Host.settle` 达到其 `limit`，而器件始终没有发出请求                                         |

这六个都可以从 `upd7725` 导入。

### 命令行工具

| 命令                                     | 参数                                                                                | 退出码                                                                                                     |
| :--------------------------------------- | :---------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------- |
| `python3 upd7725/doctor.py`              | 无                                                                                  | 所有检查都通过时为 0，否则为 1                                                                             |
| `python3 -m conformance.instructions`    | `--corpus PATH`, `--cases N`, `--record`, `--retake`                                | 没有不一致时为 0，有任何不一致时为 1，参数错误时为 2                                                       |
| `python3 -m conformance.differential`    | `--from N`、`--cases N`（默认 5,000）、`--seconds S`                                | 两个实现一致时为 0，不一致时为 1，参数错误时为 2                                                           |
| `python3 -m conformance.speed`           | `--instructions N`（默认 200,000）、`--repeats N`（默认 7）                         | 达到或高于下限时为 0，低于下限时为 1，参数错误时为 2                                                       |
| `python3 -m conformance.documents`       | `--check`, `--only SUBSTRING`                                                       | 每份文档都与其摘要匹配时为 0，否则为 1                                                                     |
| `python3 -m conformance.quotes`          | 无                                                                                  | 每条引文都找到或没有任何文档时为 0，否则为 1                                                               |
| `python3 -m conformance.links`           | 无                                                                                  | 本文件中有链接返回 404 或 410 时为 1，否则为 0                                                             |
| `python3 -m conformance.stack IMAGE`     | 一个或多个较大器件的映像，16384 个程序字和 2048 个表字                              | 每个映像都不超过 8 级堆栈时为 0，有映像超过或无法确定上限时为 1，未给映像或长度不对时为 2                  |
| `python3 -m conformance.testroms FOLDER` | 存放 `conformance/testroms.json` 所列测试映像的文件夹，加 `--record` 则重写测量语料 | 找到的每个映像都与记录的调查结果一致且不超出堆栈时为 0，否则为 1，未指定文件夹时说明未检查任何内容并返回 0 |
| `python3 -m conformance.package WHEEL`   | 要审查的 wheel                                                                      | 每个模块都已包含且不含任何测试时为 0，否则为 1，未指定 wheel 时为 2                                        |

单独使用 `--record` 会拒绝覆盖语料库。`--record --retake` 会覆盖它，仅用于引入一项更正后的硬件事实。

## 以真实速度运行

器件按其晶振的频率运行。`step()` 报告一条指令的耗费，因此主机可以让器件与真实时钟保持同步。

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

8,192,000 Hz 是数据表给出 122 ns 指令周期时所用的时钟。在本器件上一条指令就是一个周期，所以 `run_for()` 恰好用完其预算，`owed` 保持为 0。循环仍然结转差额，这样它与指令耗费多个周期的器件所用的循环写法相同。

`python3 -m conformance.speed` 测量模型的速度，并以芯片每秒 8,192,000 条指令的比例打印其速率。低于每秒 250,000 条指令时失败。

<a id="driving-it-one-cycle-at-a-time"></a>

## 逐周期驱动

`Clock(cpu)` 可以让器件停在任意两个周期之间，这正是电路板改变一次读取将得到什么结果的位置。

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

| 调用                      | 作用                                                          |
| :------------------------ | :------------------------------------------------------------ |
| `tick()`                  | 运行到下一个周期结束后停下。返回此时钟已运行的周期数          |
| `run_for(cycles)`         | 执行 `cycles` 次 tick。返回此时钟已运行的周期数               |
| `close()`                 | 停止器件，并恢复它原先的 `on_cycle`。离开 `with` 块时会关闭它 |
| `cycles`, `closed`, `cpu` | 已运行的周期数、是否已关闭，以及该器件                        |

迭代一个时钟会使它 tick。器件在 tick 期间抛出的异常会从 `tick()` 抛出，并且时钟随之关闭。

NEC 说明本器件在一个外部时钟周期内执行一条指令，所以周期边界与指令边界是同一个位置。`Clock` 为本器件提供与家族中其他成员相同的接口，但没有更细的粒度，`step()` 是更快的调用。时钟在一个线程上运行器件，并在每个周期阻塞它，因为 Python 无法挂起调用栈。只有该线程会阻塞：在时钟暂停时调用的 `irq()` 会像在两次 `step()` 之间一样立即生效，其周期计入 `cpu.cycles`，但不计为 tick。

<a id="models"></a>

## 型号

同一套指令集，两种尺寸。每个存储区的长度恰好等于为其寻址的寄存器所能覆盖的范围。

| 构建方式          |    程序存储区 |        表 |    暂存区 | 堆栈 | 程序计数器 |
| :---------------- | ------------: | --------: | --------: | ---: | ---------: |
| `Cpu("upd7725")`  |  2048 x 24 位 | 1024 x 16 |  256 x 16 |    4 |      11 位 |
| `Cpu("upd96050")` | 16384 x 24 位 | 2048 x 16 | 2048 x 16 |    8 |      14 位 |

NEC 的数据表和数据手册涵盖 uPD7725。没有找到任何关于 uPD96050 的 NEC 文档，所以它的四项数值依据的是二手资料。其记录标记为 `verified: false`，[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) 说明了什么可以解决这个问题。

每个器件都接受 NEC 销售它时使用的编号。大小写、连字符和下划线无关紧要，所以 `Cpu("uPD-77C25")` 会构建一个 uPD7725。

| 构建方式          | 也接受                                    |
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

本包没有实现的器件编号会被拒绝，而不是解析为最接近的那个。

<a id="reading-without-running"></a>

## 不运行而读取

`decode(word, address=0)` 读取一个程序字，`disassemble(words, address=0)` 为每个字产出一个 `Instruction`，从 `address` 开始编号。`Instruction` 携带 `address`、`raw` 和 `text`。

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

它接受字而不是字节，因为程序存储区按字寻址。每个 24 位字都会解码为四种形式之一：`op`、`rt`、`jp` 和 `ld`。条件字段没有对应任何条件的跳转会打印为 `jp ?`，后跟该字段的十六进制值，因此不会抛出异常。

## 没有什么是干净启动的

构建出的器件在 `pc`、`rp`、`dp`、`sp`、`k`、`l`、`m`、`n`、`a`、`b`、`tr`、`dr` 以及每个堆栈槽中持有由其种子派生的值。没有任何参数可以清除它们。标志、状态字、`si`、`so` 和 `trb` 从 0 开始，每个存储区在写入之前都读出 `fill`。

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

复位之前程序计数器指向 4EB，所以单步执行一个未复位的器件会从种子选定的地址开始运行。数据表说 RESET 把程序计数器设为 0，而这也是 `reset()` 改变的唯一内容：复位之后累加器 A 仍然持有 A2FB。

## 它是否正确

语料库在两个器件上逐字段遍历 **1,120** 种编码，并加入 20,000 个由种子派生的用例。每个用例设置一个完整的处理器状态，执行一条指令，并记录其后的完整状态。模型复现了全部用例：**22,240 条指令，没有不一致**。

```bash
python3 -m conformance.instructions
python3 -m conformance.differential --from 70000000 --cases 4000
python3 conformance/alu_flags.test.py
```

```
  22,240 instructions, 0 disagreed
  4,000 cases, the model and the reference agreed on every one
```

第一条命令是门禁检查，它不需要仓库之外的任何东西。第二条命令在语料库范围之外的用例上，让 [`conformance/reference.py`](conformance/reference.py) 与模型并行单步执行，前者是按另一种结构编写的第二个实现。第三条命令依照 1989 年数据手册的 Table 6 驱动全部十六种 ALU 运算，该表为每个标志说明它是受影响、复位、保持还是不确定。模型与每个单元格都一致。

[`conformance/hardware.json`](conformance/hardware.json) 保存了取自文档的每一项事实，以及其来源语句和页码。当数据表与语料库不一致时，以数据表为准，并重新录制语料库。这种情况发生过三次，[`conformance/pinned.json`](conformance/pinned.json) 记录了每一处：一是堆栈深度，业界每个实现都给出十六，而 NEC 印的是四；二是 581 个用例，其中算术运算把自己的累加器指定为数据传送的目标，NEC 说这会把该运算变为 NOP；三是 1,895 个经由串行寄存器传送字的用例，NEC 印明 SIL 按位反转读取输入、传送到 SO 会置位 SOACK、从 SI 传送会清除 SIACK。

语料库是从模拟器录制的，因此它只决定 NEC 没有印出的内容。[`conformance/divergences.json`](conformance/divergences.json) 保存了两个来源存在分歧的每一处。[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) 列出六个仍未解决的问题，以及能解决每个问题的测量。

## 参与开发

| 需求                             | 位置                                                                         |
| :------------------------------- | :--------------------------------------------------------------------------- |
| 所有门禁检查及其运行顺序         | [CONTRIBUTING.md](CONTRIBUTING.md)                                           |
| 面向编码代理的同类材料           | [AGENTS.md](AGENTS.md)                                                       |
| 本仓库与家族中其他仓库共享的标准 | [FAMILY.md](FAMILY.md)                                                       |
| 缺陷报告                         | [GitHub Issues](https://github.com/gufranco/nec-upd7725-96050-python/issues) |
| 安全报告                         | [SECURITY.md](SECURITY.md)                                                   |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx mypy@1.14.1
pnpm install --frozen-lockfile && pnpm run format:check
python3 -m coverage erase
for f in $(find upd7725 conformance -name '*.test.py' | sort); do python3 -m coverage run -a "$f"; done
python3 -m coverage report
```

每个模块旁边都有一个名为 `<module>.test.py` 的测试文件，每个都可以单独运行。覆盖率是一项硬性门禁检查，要求 100% 语句与分支覆盖，类型检查使用 strict 模式的 `mypy`。

## 参考资料

- NEC Electronics，_uPD77C25/uPD77P25 Digital Signal Processor Data Sheet_，Advance Product Information，1987 年 8 月。36 页，1,299,452 字节，SHA-256 `d043be18d5cd21d90960ffb7e068e3b9a81647c8534a142f29eb11015733d042`。获取自 https://www.cryptomuseum.com/df/telefunken/e2000/files/uPD77C25.pdf
- NEC Electronics，_Digital Signal Processor and Speech Processor Products Data Book_，文档 50052，1989 年。388 页，14,316,524 字节，SHA-256 `2f0190523de99938cc1da1c138f2c5b7f71573eb11bcb3b0dcdd1da1267e85ce`。获取自 https://bitsavers.trailing-edge.com/components/nec/_dataBooks/1989_DSP_and_Speech_Products_Data_Book.pdf
- ares，https://github.com/ares-emulator/ares ，采用 [`conformance/pinned.json`](conformance/pinned.json) 指定的提交，用于研究文档没有给出的指令级行为。未取用任何代码。

两份文档都不可再分发，也都不在本仓库中。[`conformance/documents.json`](conformance/documents.json) 记载了每份文档的摘要、大小和地址。`python3 -m conformance.documents` 把两份文档下载到 git 忽略的 `docs/` 中，并拒绝摘要不匹配的文件。`python3 -m conformance.quotes` 随后在其中查找每一条被引用的语句。

两份都是印刷书籍的扫描件，所以每一页都读了两遍：一遍读图像，一遍读文件携带的文本层。1987 年文档的文本层把 `the` 印成 `lhe`，并在页面写着 `8-bit` 的地方印成 `a-bit data pointer`。引文旁记录的页码，要么是两种读法一致的页面，要么是直接阅读该页确认过的页面。数据手册按章节编排页码，如 2-33，所以从中读取的事实会注明章节。

## 引用本项目

[CITATION.cff](CITATION.cff) 随每次发布由标记包版本的脚本更新。

## 许可证

MIT。见 [LICENSE](LICENSE)。
