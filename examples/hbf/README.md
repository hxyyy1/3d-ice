# HBF 384 GB / 1 TB/s / 16H 参考物理模型

本目录提供一套面向3D-ICE 4.0的High Bandwidth Flash（HBF）子模型：

- `hbf_384gb_16h/model.stk`：384 GB、1 TB/s、16个NAND core die加1个logic/base die。

模型面向后续GPU/NPU、HBM、interposer和完整封装联合仿真。交付模型不包含interposer、顶部TIM、散热器、冷板或任何heat-sink边界，也不包含预设功耗。

HBF截至2026年仍属于新兴技术。公开资料已经可以确认16H NAND core stack、TSV、microbump/MUF、logic/base die和接近HBM4的封装包络，但没有公开384 GB目标器件的完整量产截面、die尺寸、TSV map和每层功耗。因此，本模型是可追溯的公开资料参考结构，不是Sandisk、SK hynix或OCP的工艺deck。

## 1. 证据等级

| 等级 | 含义 |
|---|---|
| A | OCP规范、厂商正式资料或同行评审论文直接给出 |
| B | KAIST TERALAB技术演示、IEEE论文或公开技术报告 |
| C | 由A/B级数据计算或跨同代设计映射得到 |
| D | 缺少公开截面时采用的几何或材料假设 |

当前模型已对公开资料可约束的热导率及非active层体积热容完成校准；active/source热容按本轮要求保持原值。HBF专有TSV、MUF和NAND/CBA配方仍属于C/D级公开资料约束模型，不能视为量产工艺deck。

## 2. 目标规格及与当前HBF标准的关系

| 参数 | 本模型 | 证据与说明 |
|---|---:|---|
| 容量 | 384 GB | 用户目标；H3/MemExplorer参考点[S1][S7] |
| 读带宽 | 1 TB/s | 用户目标；H3/MemExplorer参考点[S1][S7] |
| NAND core die | 16 | B/A：[S2][S3][S4] |
| Logic/base die | 1 | A/B：[S2][S4][S5] |
| 单core die容量 | 24 GB = 192 Gb | C：384/16，非公开标准die density |
| 物理硅die总数 | 17 | C：16 core + 1 base |
| 平面参考尺寸 | 11 × 11 mm | C/D：采用项目HBM4兼容footprint |
| 总高度 | 775 μm | C/D：按“接近HBM4 stack height”闭合[S3][S10] |
| 数值active层厚 | 2 μm/die | D：数值功耗层，不是额外实物die |
| D2D bond厚度 | 10 μm | B/D：TERALAB microbump/MUF类别为10–15 μm，模型取下界[S2] |
| 外部功耗列数 | 17 | 1 base + 16 core active modules |

需要区分两个时间点：

1. H3和MemExplorer采用的早期HBF参考点为`384 GB / 1 TB/s`。[S1][S7]
2. Sandisk随后公开的Gen-1目标是`256 Gb/die × 16 = 512 GB`和`1.6 TB/s`。[S3]
3. 2026年8月发布的首版OCP HBF规范覆盖8H/16H、最高512 GB和多个带宽等级。[S4][S5]

因此，本模型是**保持用户研究目标的pre-standard 384 GB配置**，不是把后来的512 GB Gen-1器件错误标成384 GB产品。

## 3. 采用的HBF物理架构

### 3.1 Core stack与base die

公开HBF结构由以下部分组成：[S2]-[S5]

```text
16 × HBF NAND core die
TSV arrays贯穿stack
die-to-die microbump/MUF连接
1 × logic/base die
base die到xPU/interposer的PHY接口
```

OCP路线中的base die负责host接口、NAND控制、数据调度、ECC、测试、TSV repair和可选scratchpad SRAM，而不是被动硅转接层。[S4][S5]

### 3.2 CBA NAND core die

Sandisk HBF基于CBA（CMOS directly Bonded to Array）NAND。[S3] TERALAB给出两类结构：[S2]

- peripheral circuit位于每个NAND core die；
- peripheral circuit集中在底部base die。

本模型采用第一类：每个core die均含NAND array与CBA peripheral circuit，并把外围电路抽象成该die底部的2 μm active/source数值层。这样可以在未来把读取功耗分布到16层，而不是把所有NAND功耗错误集中在base die。

base die仍单独保留一个2 μm active/source层，用于controller、PHY、ECC和SRAM等逻辑功耗。

## 4. 垂直结构和高度闭合

模型采用HBM4兼容的775 μm参考包络，并使用统一的35 μm core die：

```text
[33 μm passive NAND/Si + 2 μm CBA peripheral active] × 16
[10 μm D2D microbump/MUF等效层] × 16
53 μm base substrate + 2 μm base active
-----------------------------------------------------
775 μm HBF cube
```

高度闭合：

```text
16 × (33 + 2) + 16 × 10 + (53 + 2)
= 560 + 160 + 55
= 775 μm
```

其中：

- `16H`、TSV和base die是公开结构；
- Sandisk只说明stack height接近HBM4，没有公开384 GB HBF截面；
- Sandisk公开结构图标注microbump，TERALAB给出的常规microbump/MUF gap为`10–15 μm`、覆盖4–16Hi；模型采用10 μm下界；
- `35 μm/core die`和`55 μm/base die`是为了满足775 μm包络而构造的D级厚度分配；
- active层从对应物理die厚度中切出2 μm，因此不会额外增加物理高度。

如果后续取得真实cross-section，应优先替换33、10和53 μm，而不需要改变16H拓扑。

## 5. 层数统计

每个物理硅die拆成一个被动层和一个2 μm active/source层，16个相邻core/base界面各使用一个bond层：

| 组成 | 数量 |
|---|---:|
| NAND core passive层 | 16 |
| NAND core active层 | 16 |
| Logic/base passive层 | 1 |
| Logic/base active层 | 1 |
| D2D bond层 | 16 |
| 3D-ICE总层数 | 50 |

计算式：

```text
2 × (16 core + 1 base) + 16 bond = 50 layers
```

这里没有计入HBF-to-interposer接口、silicon/glass interposer、package substrate、PCB或TIM。

## 6. 平面几何与TSV区域

模型使用`11 × 11 mm`、250 μm网格，对应44×44 cells/layer。

`top_silicon.layout`：

- 中央10.5×10.5 mm区域为顶层core die；
- 四周250 μm环带为EMC代理；
- 顶die不设置穿透TSV。

`tsv_silicon.layout`：

- 中央`7 × 9 mm`区域使用`TSV_SI_HBF_EQ`；
- 四周保留250 μm EMC环带。

公开资料只确认存在TSV arrays，没有公开384 GB HBF的TSV直径、pitch、数量或坐标。[S2][S3] `7 × 9 mm`窗口继承自本项目HBM参考模型，是便于联合建模的D级占位，不是HBF标准bump map。1 TB/s带宽只作为体系结构目标，不足以唯一反推出TSV数量。

Sandisk称HBF接近HBM4 footprint，但没有给出正式X/Y机械图。[S3] 因此11×11 mm同样属于C/D级参考值。若系统封装采用10.5×12 mm HBM4 site，应整体修改`dimensions`、两个`.flp`和两个`.layout`。

## 7. 功耗输入

交付`.flp`不含任何`power values`，外部trace是唯一功耗源。Trace每行需要17列，顺序从底部到顶部：

```text
HBF_BASE, HBF_D1, HBF_D2, ..., HBF_D16
```

若上游只有整体功耗`P_HBF(t)`，需要在写入3D-ICE前展开。获得base-die功耗比例`r_base`时：

```text
P_base(t)   = r_base × P_HBF(t)
P_core_i(t) = [1 - r_base] × P_HBF(t) / 16
```

并满足：

```text
P_base + ΣP_core_i = P_HBF
```

如果没有`r_base`，可以临时等分为17份，但这只是D级接口假设。实际HBF的controller/PHY/base逻辑功耗与16个CBA peripheral层不会严格相等。

H3后续研究提到base die scratchpad/staging buffer；[S1][S8] 当前模型没有把SRAM单独划成平面模块，因为上游只提供package总功耗。取得base/PHY/SRAM功耗分解后，可扩展`base_die.flp`而无需改变stack。

## 8. 热导率校准

热参数已按约320 K参考温度校准，3D-ICE写入值仍为SI值除以$10^6$。最终名义张量为：

| 材料/等效层 | $k_x,k_y,k_z$ [W/(m·K)] | $C_v$ [MJ/(m³·K)] | 等级与推导 |
|---|---:|---:|---|
| Silicon | 130,130,130 | 1.710 | B/C；320 K NIST Si热容 |
| EMC | 0.88,0.88,0.88 | 1.520 | B/C；公开PBGA mold基线 |
| NAND core backing | 101.118,101.118,9.677 | 1.811 | C/D；Si与218-layer W/SiO$_2$阵列复合 |
| TSV-NAND | 102.674,102.674,14.615 | 1.832 | D；NAND matrix内加入1.298% Cu TSV |
| TSV-Si base | 131.699,131.699,133.375 | 1.733 | D；Si matrix内加入1.298% Cu TSV |
| CMOS active/source | 16.566,16.566,118.529 | 1.626 | C/D；本轮按要求不修改 |
| 10 μm microbump/MUF | 1.3037,1.3037,0.8167 | 1.558 | C/D；20% SAC与80% MUF体积混合 |

### 8.1 NAND array与Si backing

Sandisk公开其最新CBA BiCS8采用218 layers[S11]；这只作为HBF 256 Gb CBA工艺族的阵列几何代理，不表示当前384 GB研究点的每die容量已经被产品图纸确认。公开V-NAND单元模型给出20 nm word-line与20 nm ILD；材料取$k_W=40$、$k_{SiO_2}=1.4$ W/(m·K)[S12]。因此阵列厚度和正交等效为：

```text
t_array = 218 × (20+20) nm = 8.72 μm
kxy,array = (40 + 1.4)/2 = 20.70 W/(m·K)
kz,array  = 40 / (20/40 + 20/1.4) = 2.705 W/(m·K)
```

在33 μm passive core层中，余下24.28 μm作为Si backing。面内并联、贯穿串联：

```text
kxy,core = (24.28×130 + 8.72×20.70)/33 = 101.118 W/(m·K)
kz,core  = 33/(24.28/130 + 8.72/2.705)  = 9.677 W/(m·K)
```

这项修正避免把3D NAND的W/oxide多层堆栈当成130 W/(m·K) bulk Si。`NAND_CORE_EQ`用于16个core die；base/logic die仍使用Si matrix，并通过新增`base_tsv_silicon.layout`与core-die TSV材料分离。

体积热容使用同一厚度比例：W和SiO$_2$阵列取$(2.58+1.606)/2=2.093$ MJ/(m³·K)，再与24.28 μm Si按厚度混合，得到NAND core的1.811 MJ/(m³·K)。TSV-NAND继续加入1.298% Cu体积分数，得到1.832 MJ/(m³·K)。

### 8.2 TSV与bond

HBF没有公开生产TSV map，中心值继续采用HBM4敏感性面积分数$f_{TSV}=0.0129818$。轴向Cu按并联、面内按Maxwell圆柱模型加入NAND matrix。该输入必须视为D级，建议至少扫描0.5--2.0%。

HBM实测反演的15 μm bond等效$k_z=1.225$ W/(m·K)[S13]，对应面积热阻$R''=15\,\mu$m$/1.225$。假设HBF的界面/BEOL面积热阻不变，10 μm层得到：

```text
kz,HBF-bond = 10 μm / (15 μm / 1.225) = 0.8167 W/(m·K)
```

该值低于简单solder/MUF面积并联得到的数值，因为后者漏掉接触、IMC、空洞和BEOL热阻。完整计算与模型逐项核对可运行`../thermal_calibration/calibrate_conductivity.py --check`；论文级推导见`../thermal_calibration/thermal_conductivity_calibration.tex`。

## 9. 与完整封装集成

集成时建议：

1. 把本模型的material、layer、die和stack声明合并到系统`.stk`；
2. 在`HBF_BASE`下方添加HBF-to-interposer bump/bond层；
3. 添加silicon/glass interposer、GPU/NPU、HBM及package substrate；
4. 再加入顶层TIM、lid/cold plate和真实散热边界；
5. 每个HBF placement提供17列展开后的功耗trace；
6. 在统一热网络中求解。

当前模型本身无热边界，不能用非零功耗求有限稳态温度。

## 10. 已知限制与优先补充数据

1. `384 GB / 1 TB/s`是研究参考点，而当前公开Gen-1/OCP路线已转向512 GB及多个带宽等级。
2. 24 GB/core die由总容量除以16得到，不是公开HBF die density。
3. 11×11 mm footprint缺少HBF正式机械图。
4. 775 μm总高由“接近HBM4”映射，35 μm core和55 μm base是高度闭合假设。
5. 10 μm bond层采用TERALAB microbump/MUF类别下界；量产HBF的专有堆叠技术仍可能不同。
6. TSV窗口、直径、pitch及Cu面积分数未获得公开生产数据。
7. CBA NAND array与peripheral CMOS没有显式拆成两个独立物理wafer层。
8. 当前每个die只有一个整体active模块，不能预测plane、channel、PHY或ECC局部热点。
9. 热导率已按公开CBA/V-NAND/HBM资料校准，但TSV面积分数、NAND实际层数/节距和bond面积热阻仍是C/D级，不能替代目标HBF实测。

对温度精度最有价值的后续数据依次是：目标HBF截面、core/base die厚度、bond gap、TSV map、HBF-to-interposer接口及每层功耗比例。

## 11. 参数来源

### [S1] Ha, Kim, and Kim, 2026 — H3

M. Ha, E. Kim, and H. Kim, “H3: Hybrid Architecture Using High Bandwidth Memory and High Bandwidth Flash for Cost-Efficient LLM Inference,” *IEEE Computer Architecture Letters*, 25(1), 49–52, 2026。

用于：HBF/HBM混合体系结构、384 GB/1 TB/s研究目标、只读数据放置与整体功耗/性能背景。

https://doi.org/10.1109/LCA.2026.3660969

### [S2] Joungho Kim, 2026 — HBF Technology, Workload Analysis and Roadmap

KAIST TERALAB公开演示稿。用于：16-stack NAND、TSV arrays、peripheral-on-every-die与peripheral-on-base两类架构、standard/custom HBF base die，以及microbump/hybrid-bond gap和stack-density范围。关键物理图见第24、25、44–46页。

https://tera.kaist.ac.kr/ （“2026 HBF Workload and Roadmap”）

### [S3] Sandisk HBF Fact Sheet, July 2025

用于：CBA NAND、16 die stack、256 Gb/die、512 GB Gen-1、1.6 TB/s，以及接近HBM4 footprint/power/stack height的说明。

https://documents.sandisk.com/content/dam/asset-library/en_us/assets/public/sandisk/collateral/company/Sandisk-HBF-Fact-Sheet.pdf

### [S4] OCP HBF High-Level Base Die Specification v0.7.0, 2026

用于：HBF base/core-die边界、8H/16H配置、host/base/NAND接口、可靠性、TSV repair、测试和可选scratchpad等标准化方向。原始链接已确认，但本次环境访问PDF返回403；细节由厂商公告和多份规范解读交叉核对，不能标记为本地逐页原文核验。

https://www.opencompute.org/documents/ocp-hbf-architecture-specification-v0-7-0-final-pdf

### [S5] Sandisk and SK hynix OCP HBF Specification Announcement, 2026

用于：OCP规范发布状态、xPU-HBF interface、die-stack packaging/reliability和软件I/O覆盖范围。

https://www.sandisk.com/company/newsroom/press-releases/2026/2026-08-03-Sandisk-and-sk-hynix-advance-global-standardization-of-hbf

### [S6] SK hynix HBF at FMS 2026

用于：OCP首版规范的8H/16H、最高512 GB与带宽等级路线。

https://news.skhynix.com/en/hbf-at-fms-2026/

### [S7] Wu et al., 2026 — MemExplorer

用于：对`384 GB、1 TB/s、约1 μs`HBF研究配置的独立交叉核对，以及HBF在异构NPU内存设计空间中的定位。

https://arxiv.org/abs/2604.16007

### [S8] Son et al., 2026 — Exploring HBF for Modern LLM Inference

用于：core dies经TSV堆叠在logic base die上、per-die/plane并行、base-die staging buffer和HBF写入/耐久性约束。

https://arxiv.org/abs/2608.13868

### [S9] Sakui and Ohba, 2019 — High Bandwidth NAND

用于：以TSV并行访问NAND plane、bumpless TSV与超薄die作为HBF前身路线。该论文不是当前Sandisk/OCP HBF产品规范，因此没有直接把其4 μm极限die厚度写入本模型。

https://doi.org/10.1109/3DIC48104.2019.9058900

### [S10] HBM4 height envelope update

用于：HBM4 package-height参考包络由720 μm放宽到约775 μm。HBF只公开“接近HBM4 stack height”，故本模型对775 μm的采用仍为C/D级映射。

https://www.digitaltoday.co.kr/en/view/84721

### [S11] Sandisk BiCS8 218-layer CBA资料

用于：以218层CBA NAND作为HBF 256 Gb工艺族的公开阵列层数代理；这是工艺映射，不是384 GB研究配置的精确die截面。

https://investor.sandisk.com/static-files/79481580-ada2-4e08-bdeb-4b440d08f4ab

### [S12] Kim, Ryu and Lee，V-NAND均质化模型，2025

Y. Kim, S. Ryu and S. Lee, “Modeling methodology for thermo-structural analysis of V-NAND flash memory structure,” *Scientific Reports*, 15, 7316, 2025。用于：20 nm word-line/20 nm ILD几何，以及Si、SiO$_2$、poly-Si和W热导率。

https://doi.org/10.1038/s41598-025-89936-8

### [S13] Chalise and Cahill，HBM各向异性热导率实测，2023

用于：商用HBM2 polymer/solder层约2 W/(m·K)和整颗HBM $k_z=7\pm0.7$ W/(m·K)，据此反演未显式BEOL/界面面积热阻并迁移到HBF bond层。

https://doi.org/10.48550/arXiv.2303.06785

## 12. 数值兼容性验证

2026-08-23，使用校准后的NAND/base材料映射和当前仓库`3D-ICE-Server --power-trace`，在仅存在于`/tmp`验证副本中的临时顶部边界下完成单slot transient求解。验证功耗来自17列外部trace；交付模型不含该边界和预设功耗。

```text
Physical silicon dies = 17
3D-ICE layers        = 50
Cells                = 96,800
Connections          = 568,128
Power-trace columns  = 17
Factorization        = 17.54 s
```

单slot解析和求解通过。该测试只证明`.stk/.flp/.layout`结构及外部trace接口兼容，不构成HBF温度精度验证。
