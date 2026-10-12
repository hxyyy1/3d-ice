# GDDR6 1-Pkg 与 GDDR7 1-Pkg 物理参考模型

本目录包含两套可并入完整芯片/PCB热模型的单封装模型：

- `gddr6_1pkg/model.stk`：16 Gb = 2 GB GDDR6；
- `gddr7_1pkg/model.stk`：24 Gb = 3 GB GDDR7。

物理结构和几何尺寸按公开机械图、拆解及基板规格约束；热导率与非active层体积热容已在约320 K参考温度下重新校准。直接数据不足的层采用有限体积均质化、铜走线覆盖率、Maxwell圆柱夹杂模型、面积热阻反演及体积热容守恒混合。完整推导、证据等级和不确定性见`../thermal_calibration/thermal_conductivity_calibration.tex`。

## 1. 证据等级

| 等级 | 含义 |
|---|---|
| A | 厂商数据表、正式产品目录或机械图直接给出的参数 |
| B | 公开拆解实测、同行评审论文或封装供应商规格 |
| C | 从A/B级数据计算得到的尺寸或跨同代产品推断 |
| D | 尚无公开截面时采用的布局或厚度假设 |

目录中的模型是公开资料可支持的参考几何，不是任一厂商的保密封装图纸。

## 2. 校准后的主要物理参数

| 参数 | GDDR6 1-Pkg | GDDR7 1-Pkg | 等级与说明 |
|---|---:|---:|---|
| 容量 | 16 Gb = 2 GB | 24 Gb = 3 GB | A：[S1][S4] |
| 封装平面尺寸 | 12 × 14 mm | 12 × 14 mm | A：[S1][S4][S5] |
| 模型总高 | 1.10 mm nominal | 1.10 mm | G6 A/C：机械图为1.1±0.1 mm；G7 A |
| 产品目录高度上限/标称项 | 1.20 mm | 1.10 mm | A：[S2][S4][S5] |
| BGA球数 | 180 | 266 | A：[S1][S4][S5] |
| BGA pitch | 0.75 mm | 0.75/0.73 mm | A：[S1][S5] |
| BGA球高 | 0.34±0.05 mm | 0.30 mm | G6 A：[S1]；G7 D |
| BGA球径 | 约0.47 mm | 0.47 mm | G6 A：[S1]；G7 D，沿用G6代理 |
| 物理DRAM die数 | 2 | 2 | G6 B/C：[S2][S3]；G7 B/C：[S6][S7] |
| 单die平面尺寸 | 8.23 × 4.50 mm | 6.50 × 6.40 mm | G6 B：拆解实测；G7 B/C：41.6 mm²等面积矩形 |
| 单die面积 | 37.03 mm² | 41.60 mm² | B：[S3][S6] |
| 两die总面积 | 74.06 mm² | 83.20 mm² | C |
| 硅片总厚度 | 150 μm | 150 μm | D：采用公开FCCSP截面的实测量级[S9] |
| active/source数值层 | 2 μm | 2 μm | D：数值离散层，不是独立实物薄片 |
| 被动硅厚度 | 148 μm | 148 μm | C：150−2 μm |
| bump/PI等效厚度 | 48 μm | 48 μm | D：采用公开FCCSP的30+3+10+5 μm截面[S9] |
| package substrate | 280 μm，4L | 262 μm，6L | G6 B/C；G7 B：[S8] |
| 顶部mold cap残余厚度 | 282 μm | 340 μm | C/D：由总高闭合反算 |

### 2.1 GDDR6 裸片尺寸为什么改变

原模型曾使用两个`8 × 6 mm`裸片，这是按旧位密度做的估算。新的公开拆解针对Samsung `K4ZAF325BC-SC20` 16 Gb GDDR6，在封装内识别出`K4Z80165BC` 8 Gb die，并测得：[S3]

```text
seal 内尺寸：8.18 × 4.44 mm = 36.32 mm²
whole-die尺寸：8.23 × 4.50 mm = 37.03 mm²
```

模型采用whole-die尺寸。Micron 16 Gb GDDR6目录同时把对应封装列为`Number of Components = 2`，[S2] 因此使用两个8 Gb物理die比原先的单大die或两个48 mm²估算更有依据。

不同厂商/工艺节点的die尺寸会变化。本模型的`37.03 mm²/die`具体对应Samsung 1z节点拆解，不代表所有2 GB GDDR6料号。

### 2.2 GDDR7 裸片尺寸如何映射到3 GB

Micron当前目录已直接列出24 Gb器件`MT68A768M32DF`，其容量、12×14×1.1 mm外形和266-ball封装与本模型一致。[S4]

公开ISSCC/JSSC设计给出GDDR7采用两个die组成四通道，并披露1z节点16 Gb设计的die面积为41.6 mm²。[S6] Samsung对24 Gb GDDR7说明其通过提高50%单元密度，在保持封装尺寸不变的情况下将容量从16 Gb提高到24 Gb。[S7] 因此本模型暂时保持两个die，并将每个die表示为等面积的：

```text
6.50 × 6.40 mm = 41.60 mm²
```

这里“24 Gb仍采用两个41.6 mm² die”是C级跨产品推断，不是Micron 24 Gb封装的公开X-ray/截面实测。若后续取得该料号的die photo，应优先替换。

## 3. 垂直结构和层数

两套模型都使用6个3D-ICE数值层。`active/source`从150 μm硅片中切出2 μm用于施加功耗，因此不能把它理解为硅片之外额外增加的一层实物。

### 3.1 GDDR6 nominal stack

```text
282 μm  顶部EMC/mold cap（残余闭合值）
148 μm  passive silicon
  2 μm  active/source数值层
 48 μm  Cu pillar/Ni/solder/PI等效连接层
280 μm  4-layer package substrate
340 μm  BGA standoff
----------------------------------------
1100 μm  nominal package height
```

高度闭合：

```text
282 + 148 + 2 + 48 + 280 + 340 = 1100 μm
```

GDDR6机械图给出的总高是`1.1±0.1 mm`。[S1] 当前模型选nominal 1.10 mm；若要做最坏包络，可把顶部cap由282 μm改成382 μm，从而得到1.20 mm总高。

### 3.2 GDDR7 stack

```text
340 μm  顶部EMC/mold cap（残余闭合值）
148 μm  passive silicon
  2 μm  active/source数值层
 48 μm  Cu pillar/Ni/solder/PI等效连接层
262 μm  6-layer package substrate
300 μm  BGA standoff代理
----------------------------------------
1100 μm  package height
```

高度闭合：

```text
340 + 148 + 2 + 48 + 262 + 300 = 1100 μm
```

GDDR7的12×14×1.1 mm、266 balls和pitch有官方资料，[S4][S5] 但尚未找到与GDDR6同等级的公开球高/球径机械图。因此300 μm ball height及470 μm ball diameter仍是当前最大的纵向几何不确定项。

## 4. 平面布局文件

`dram_silicon.layout`定义被动硅层中两个物理die的平面位置；`bump_underfill.layout`在相同footprint下放置flip-chip连接区。

### 4.1 GDDR6

```text
die 0: (1885, 2250, 8230, 4500) μm
die 1: (1885, 7250, 8230, 4500) μm
```

两个die均为8.23×4.50 mm，长轴沿package的12 mm方向；模型把它们居中放置，在14 mm方向留0.50 mm间隔。裸片尺寸来自实测，**方向、居中方式及0.50 mm间隔仍为D级布局假设**。

### 4.2 GDDR7

```text
die 0: (2750,  400, 6500, 6400) μm
die 1: (2750, 7000, 6500, 6400) μm
```

两个die各为6.50×6.40 mm，面积等于论文披露的41.6 mm²。两die平面并排而非垂直堆叠，是基于12×14 mm包内可布置面积及散热路径做出的D级实现假设；公开论文确认了die数量和面积，但没有公开本模型所需的封装内精确坐标。

## 5. 厚度参数的依据与边界

### 5.1 已有直接或较强依据

- GDDR6总高、球高、球径和pitch来自机械图[S1]；
- GDDR6 die的XY尺寸来自具体器件拆解[S3]；
- GDDR7总高、封装尺寸、容量和ball count来自Micron正式产品目录[S4]；
- GDDR6/GDDR7 substrate层数和厚度来自GDDR FCCSP substrate供应商：GDDR6 4L为246–308 μm，GDDR7 6L为262 μm。[S8]

### 5.2 仍是类比值的厚度

公开FCCSP截面论文给出150 μm die；其Cu pillar 30 μm、Ni 3 μm、reflow solder 10 μm和PI 5 μm合计48 μm。[S9] 这些值用于替代原模型自行假设的200 μm die和50 μm bump层，使厚度量级更接近实测FCCSP结构。

但该论文样品不是GDDR6/7。故模型中的150 μm与48 μm是**封装类型校准值**，不是目标GDDR料号的直接测量。顶部mold cap由总高扣除其他层得到，其准确度受这些类比厚度和GDDR7球高假设共同限制。

## 6. 功耗接口与热参数状态

`dram_active.flp`仍把每个package简化为一个`ACTIVE_EQ`模块：

- GDDR6 trace只需一列`P_GDDR6_pkg(t)`；
- GDDR7 trace只需一列`P_GDDR7_pkg(t)`；
- `.flp`中没有预设`power values`；
- 无需把总功耗拆分到两个物理die或bank。

单模块覆盖12×14 mm计算平面，是为了接收一个package总功耗；它不表示功耗在EMC中真实产生。热参数已与当前两颗die的面积和位置重新闭合。模型中的SI等效值如下；`.stk`写入值为表中数值除以$10^6$：

| 材料/等效层 | GDDR6 $k_x,k_y,k_z$ [W/(m·K)] | GDDR7 $k_x,k_y,k_z$ [W/(m·K)] | 依据 |
|---|---:|---:|---|
| Silicon | 130, 130, 130 | 130, 130, 130 | 约320 K工作点；温度修正见校准文档 |
| EMC | 0.88, 0.88, 0.88 | 0.88, 0.88, 0.88 | 公开stacked-package基线[S11]；未找到GDDR7高导热EMC证据，因此删除旧2.46代理值 |
| Active/source层 | 2.3265, 2.1687, 57.8081 | 1.8922, 6.0459, 64.8251 | 当前两die坐标上的二维有限体积均质化；$k_z$面积并联 |
| Cu-pillar/UF | 0.8790, 0.8790, 4.5639 | 同左 | 25/32 μm bump线宽/间距[S8]、FCCSP截面[S9]与microbump实测接触热阻[S10] |
| Package substrate | 30.7031, 30.7031, 0.4102 | 49.0137, 49.0137, 0.4685 | 4L/6L、25/30 μm trace覆盖率[S8]；层内并联、层间串联[S12] |
| BGA standoff | 0.0275, 0.0275, 1.0257 | 0.0275, 0.0275, 0.9410 | 球/空气体材料上界再串联焊盘收缩热阻；避免旧简单面积并联高估约一个数量级[S12] |

非active层体积热容按$C_{v,eq}=\sum_i f_i\rho_i c_{p,i}$守恒混合，单位为MJ/(m³·K)：

| 材料/等效层 | GDDR6 $C_v$ | GDDR7 $C_v$ | 状态 |
|---|---:|---:|---|
| Silicon | 1.710 | 1.710 | 320 K NIST Si热容 |
| EMC | 1.520 | 1.520 | 公开PBGA mold基线 |
| Active/source层 | 1.616 | 1.61387 | 本轮按要求不修改 |
| Cu-pillar/UF | 1.76025 | 1.76025 | Cu/Ni/SAC柱与EMC/PI体积分数 |
| Package substrate | 1.74416 | 1.83109 | patterned-Cu真实覆盖体积分数 |
| BGA standoff | 0.31877 | 0.47054 | SAC305/air体积混合 |

校准修正了原substrate热容仍按100%铜层计算、FC层未计入Cu/Ni柱，以及SAC热容仍用旧代理值的问题。active层热容保持原值，未纳入本轮校准。

`ACTIVE_LAYER_EQ`的面内分量由与3D-ICE相同网格上的稳态单元问题$\nabla\!\cdot(k\nabla T)=0$求得，而不是只取穿过die中心线的一条串联路径。可复现实现在`../thermal_calibration/calibrate_conductivity.py`。

## 7. 与完整封装集成

模型已经包含BGA standoff，但不包含：

- PCB焊盘、铜走线和显卡板；
- GPU或其他芯片；
- 顶层TIM、散热器或冷板；
- 顶部/底部散热边界。

集成时把该GDDR package作为整体放置，并为每个package提供一列外部`P_pkg(t)`。BGA的$k_z$已包含一个名义封装侧收缩热阻，但真实PCB铜区、焊盘和过孔仍应在系统模型中显式加入；获得实测$\theta_{JB}$或结构函数后，应优先反演替换这一D级接触项。

## 8. 仍待获得的数据

按对温度结果的潜在影响排序：

1. GDDR7 266-ball正式机械图中的ball height和ball diameter；
2. 目标GDDR6/7料号的封装截面：die thickness、mold cap、underfill和实际bump高度；
3. GDDR7 24 Gb成品的die photo/X-ray，确认die面积、方向、间距及是否确为平面双die；
4. GDDR6双die的封装内精确方向和间距；
5. 目标供应商的substrate精确厚度，而不是供应商公开范围/典型值。
6. 目标料号的EMC、underfill和BGA界面面积热阻实测值。

## 9. 物理参数来源

### [S1] Micron 16 Gb GDDR6 SGRAM Data Sheet — Package Dimensions

用于：180-ball FBGA机械图，`1.1±0.1 mm`总高、`0.34±0.05 mm`球高、约0.47 mm球径、0.75 mm pitch。

https://www.mouser.com/datasheet/2/671/gddr6_sgram_16gb_brief-3179155.pdf

### [S2] Micron GDDR6 Part Catalog

用于：16 Gb、x32、180-ball、12×14×1.2 mm目录外形及`Number of Components = 2`。

https://www.micron.com/products/memory/graphics-memory/gddr6/part-catalog

### [S3] TechInsights — Samsung K4ZAF325BC-SC20 GDDR6 Floorplan Analysis

用于：包内`K4Z80165BC` 8 Gb die；seal内8.18×4.44 mm，whole die 8.23×4.50 mm。

https://www.techinsights.com/blog/samsung-k4zaf325bc-sc20-gddr6-dram-memory-floorplan-analysis

### [S4] Micron GDDR7 Part Catalog

用于：24 Gb `MT68A768M32DF`、x32、266-ball、12×14×1.1 mm正式产品项。

https://www.micron.com/products/memory/graphics-memory/gddr7/part-catalog

### [S5] Micron GDDR7 Memory Product Brief

用于：GDDR6/GDDR7封装尺寸对比、180/266 balls、0.75/0.73 mm pitch及四通道信息。

https://assets.micron.com/adobe/assets/urn:aaid:aem:087330f6-6d71-4575-b622-cb10f20cdaf0/renditions/original/as/gddr7-product-brief.pdf

### [S6] Cho et al., ISSCC 2024 / IEEE JSSC 2025

用于：GDDR7由两个die组成四通道，以及1z节点设计的41.6 mm² die面积。

https://doi.org/10.1109/ISSCC49657.2024.10454354

扩展论文：https://doi.org/10.1109/JSSC.2024.3472463

### [S7] Samsung — Industry's First 24 Gb GDDR7

用于：24 Gb通过提升50% cell density并保持package size不变。

https://news.samsung.com/global/samsung-develops-industrys-first-24gb-gddr7-dram-for-next-generation-ai-computing

### [S8] SIMMTECH GDDR6/GDDR7 FCCSP Substrate

用于：flip-chip CSP结构、GDDR6 4L 246–308 μm、GDDR7 6L 262 μm和约57 μm bump pitch。

https://eng.simmtech.com/product/package05.aspx

### [S9] The Effect of BEOL Design Factors on the Thermal Reliability of FCCSP

用于：SEM/模型中的150 μm die、30 μm Cu pillar、3 μm Ni、10 μm solder和5 μm PI层。

https://doi.org/10.3390/mi16020121

### [S10] Colgan et al.，microbump单位面积热阻实测

用于：25 μm直径、50 μm pitch、16.1 μm高度microbump/underfill层的实测面积热阻8.0 K·mm²/W及underfill导热率0.55 W/(m·K)，从而识别体材料并联模型漏掉的接触热阻。

https://doi.org/10.1109/STHERM.2012.6188818

### [S11] Kim and Yoo，stacked package DAF/EMC公开参数

用于：常规EMC 0.88 W/(m·K)基线；该来源是公开专利数据，作为工程材料锚点而非GDDR厂商实测。

https://patents.justia.com/patent/20260047392

### [S12] Johnson et al.，BGA等效导热方法

用于：BT laminate 0.34 W/(m·K)、铜覆盖率下的正交各向异性基板等效，以及简单球/空气面积并联会忽略焊盘收缩热阻并高估$k_z$的结论。

https://doi.org/10.1109/ITHERM.1998.689523

## 10. 数值兼容性验证

验证只检查文件结构和外部功耗接口，不代表物理温度已经校准。验证副本临时加入顶部边界，交付模型本身仍不含散热边界。

2026-08-23使用校准后的材料张量与临时顶部边界完成单slot求解。两套模型均使用48×56平面网格、6个数值层：

```text
Cells       = 16,128
Connections = 90,144
power trace = 1列/package
GDDR6 factorization = 0.42 s
GDDR7 factorization = 0.37 s
```

当前`.stk/.flp/.layout`可由`3D-ICE-Server --power-trace`完成单slot transient解析和求解。该测试验证语法与热参数闭合性；产品级温升精度仍取决于PCB、边界条件、功耗和D级界面参数。
