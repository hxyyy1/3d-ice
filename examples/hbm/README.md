# HBM3E 8H 与 HBM4 12H 参考热模型

本目录提供两套面向 3D-ICE 4.0 的 HBM 热子模型：

- `hbm3e_8h/model.stk`：24 GB HBM3E，由 8 个 DRAM core die 和 1 个 buffer/base die 组成；
- `hbm4_12h/model.stk`：36 GB HBM4，由 12 个 DRAM core die 和 1 个 logic/base die 组成。

这两套模型用于体系结构级和封装级热分析，所有关键参数均给出来源或推导方法。它们不是 Micron、SK hynix 或 Samsung 的工艺模型。公开资料能够确认容量、堆叠层数、I/O、带宽以及部分封装尺寸，但通常不公开完整截面、真实 TSV 坐标、BEOL、键合材料配方和产品功耗图。因此，本文将参数严格区分为公开值、论文值、推导值和待校准假设。

## 1. 证据等级

| 等级 | 含义 | 使用原则 |
|---|---|---|
| A | 厂商或标准组织公开规格 | 可作为产品级目标值 |
| B | 同行评审论文或 IEEE 技术资料 | 可作为参考结构或实验工况 |
| C | 根据 A/B 参数和本文公式推导 | 可复现，但依赖所采用的等效规则 |
| D | 因无公开数据而引入的建模假设 | 必须通过截面或热阻测量进一步校准 |

文中 `[S1]` 至 `[S9]` 对应第 12 节的具体来源。

## 2. 建模范围与边界

模型当前仅包含 HBM cube 本体：

- DRAM core dies；
- buffer/logic base die；
- TSV-Si 等效衬底；
- die-to-die microbump + NCF/MUF 等效键合层；
- 被动硅层中的边缘 EMC；
- 每个 active 层的单模块功耗源。

模型当前不包含：

- 顶层 TIM、lid、散热器或冷板；
- HBM 到 interposer 的底部 microbump 层；
- silicon interposer、计算 die、封装基板和 PCB；
- 任何顶部或底部 heat-sink 边界。

因此，交付的 `.stk` 是准备嵌入完整芯片封装的 HBM 子模型。非零功耗且所有外表面绝热时不存在有限稳态温度；当前3D-ICE实现也不能稳定构建完全无散热边界的独立子模型。必须先加入完整封装的真实导热路径和至少一个物理热边界，再运行外部trace。

## 3. 产品级目标参数

| 参数 | HBM3E 8H | HBM4 12H | 等级与来源 |
|---|---:|---:|---|
| 容量 | 24 GB | 36 GB | A：[S1][S2]、[S3][S4] |
| DRAM core die 数量 | 8 | 12 | A：[S1][S2]、[S3][S4] |
| Base/buffer die | 1 | 1 | A/B：[S3][S6] |
| I/O 宽度 | 1024 bit | 2048 bit | A：[S2]、[S3][S5] |
| Channel 数量 | 16 | 32 | A：[S2][S5] |
| 公开速率 | >9.2 Gb/s | JEDEC 基线 8 Gb/s；厂商产品 >10 或 >11 Gb/s | A：[S1][S2]、[S3][S5] |
| 公开带宽 | >1.2 TB/s | >2 TB/s（SK hynix）；>2.8 TB/s（Micron） | A：[S2]、[S3][S4] |
| 平面尺寸 | 11 mm × 11 mm | 11 mm × 11 mm | HBM3E 为 A：[S1]；HBM4 为 B/D：[S6] |
| 模型内部高度 | 720 μm | 720 μm | HBM3E 为 A/C：[S1][S6]；HBM4 为 B：[S6] |
| 当前基准总功耗 | 18 W | 26 W | B：由 [S6] 的每层 2 W 工况求和；不是产品 TDP |

HBM3E 8H 的产品目标主要采用 Micron 公开的 24 GB、8H、11 mm × 11 mm × 0.72 mm 规格 [S1][S2]。HBM4 12H 的容量、I/O、速率和带宽采用 Micron 与 SK hynix 公开资料 [S3]-[S5]；内部层厚采用论文参考结构 [S6]，不能视为具体厂商量产截面。

两套模型都是厂商中立的参考模型：HBM3E 将 Micron 产品外形与通用论文截面组合；HBM4 将 Micron/SK hynix 的公开性能目标、SK hynix 的 Advanced MR-MUF 路线和通用论文截面组合。它们不对应任何一家厂商的完整单一产品。

## 4. 物理结构与 3D-ICE 层拆分

`8H` 和 `12H` 只表示 DRAM core die 数量，不包含底部 base die。每个物理硅 die 在 3D-ICE 中拆成：

```text
被动衬底/顶层 cap
2 μm active/source 层
```

相邻物理 die 之间再插入一个 15 μm 等效键合层：

```text
上层 die 的被动 Si/TSV-Si
上层 die 的 active/source
15 μm NCF/MUF + microbump 等效层
下层 die 的被动 TSV-Si
下层 die 的 active/source
```

键合层是两个 die 之间共享的界面，不属于任何单独 DRAM die 的硅厚度。

### 4.1 HBM3E 8H 截面

```text
342 μm 顶层被动 Si + 2 μm 顶层 DRAM active
15 μm NCF/microbump 等效键合层
[30 μm TSV-Si 衬底 + 2 μm DRAM active + 15 μm 键合层] × 7
30 μm TSV-Si base 衬底 + 2 μm buffer active
----------------------------------------------------------
720 μm HBM cube
```

论文 [S6] 给出的参考结构为：普通薄 die 总厚度 32 μm、顶 die 总厚度 156 μm、die 间隙 15 μm。若把该尺寸直接用于 8H，则：

```text
156 + 7 × 32 + 8 × 15 + 32 = 532 μm
```

而 Micron 公开 HBM3E 外形高度为 720 μm [S1]。为保持普通 die 的 32 μm 和 15 μm 键合节距，同时闭合 720 μm 高度，本模型把缺少的 188 μm 合并到顶层被动硅：

```text
顶 die 总厚度 = 156 + 188 = 344 μm
顶层被动 Si = 344 - 2 = 342 μm
```

342 μm 是 C/D 级的高度闭合假设，不是厂商公开的顶 die 厚度。获得真实截面后应首先替换该值。

### 4.2 HBM4 12H 截面

```text
154 μm 顶层被动 Si + 2 μm 顶层 DRAM active
15 μm Advanced-MR-MUF/microbump 等效键合层
[30 μm TSV-Si 衬底 + 2 μm DRAM active + 15 μm 键合层] × 11
30 μm TSV-Si base 衬底 + 2 μm logic active
----------------------------------------------------------
720 μm 内部参考堆叠
```

该结构直接复现 [S6] 的 12Hi 参考几何：

```text
156 + 11 × 32 + 12 × 15 + 32 = 720 μm
```

SK hynix 公开确认其 12-layer HBM4 使用 Advanced MR-MUF [S4][S5]，但没有公开材料热导率和热容。因此模型保留 15 μm 论文键合厚度，并以 microbump + EMC/MUF 代理材料进行均质化，属于 C/D 级模型。

## 5. 层数统计

| 模型 | 物理硅 die | 3D-ICE 硅层 | 键合层 | 3D-ICE 总层数 |
|---|---:|---:|---:|---:|
| HBM3E 8H | 8 DRAM + 1 base = 9 | 18 | 8 | 26 |
| HBM4 12H | 12 DRAM + 1 base = 13 | 26 | 12 | 38 |

计算方法：

```text
总层数 = 2 × 物理 die 数 + die 间键合层数
HBM3E = 2 × 9 + 8 = 26
HBM4  = 2 × 13 + 12 = 38
```

TIM、lid、HBM-to-interposer 接口、interposer 和封装基板均未计入上述层数。

## 6. `.layout` 与 `.flp` 的职责

| 文件 | 建模对象 | 是否输入功耗 |
|---|---|---|
| `top_silicon.layout` | 顶层被动硅与边缘 EMC；顶 die 不设穿透 TSV | 否 |
| `tsv_silicon.layout` | 30 μm 被动衬底中的 Si、TSV-Si 等效窗口与边缘 EMC | 否 |
| `dram_core.flp` | 一个覆盖完整 active 层的 `DRAM_ACTIVE_EQ` 功耗模块 | 是 |
| `base_die.flp` | 一个覆盖完整 base active 层的 `BASE_ACTIVE_EQ` 功耗模块 | 是 |

`.layout` 是同一 z 层中的 x-y 材料地图，不增加新的 z 层，也不接收功耗。`tsv_silicon.layout` 中：

- 未覆盖区域继承默认 `SILICON`；
- 外侧 250 μm 环带替换为 `EMC`；
- 中央 7.0 mm × 9.0 mm 窗口替换为 `TSV_SI_*_EQ`；
- 7.0 mm × 9.0 mm 是对 HBM3 约 7.084 mm × 8.828 mm bump-map 区域的网格对齐近似。

`.flp` 是 active/source 层的功耗和离散化描述。当前每个 active 层只有一个模块，不再要求 bank 或 TSV corridor 级功耗。

## 7. 材料参数及具体来源

3D-ICE 文件使用：

- 热导率单位：W/(μm·K)，由 SI 单位 W/(m·K) 除以 `10^6`；
- 体积热容单位：J/(μm³·K)，由 SI 单位 J/(m³·K) 除以 `10^18`。

下表以常用 SI 单位列出最终写入模型的等效值：

| 材料/等效模型 | kx, ky, kz [W/(m·K)] | Cv [MJ/(m³·K)] | 等级 | 具体来源或推导 |
|---|---:|---:|---|---|
| Silicon | 130, 130, 130 | 1.710 | B/C | 约320 K NIST热容；见7.1节 |
| EMC | 0.88, 0.88, 0.88 | 1.520 | B/C | 公开PBGA mold的$\rho c_p$基线 |
| Active-layer Si/EMC 等效 | 16.566, 16.566, 118.529 | 1.626 | C | 11 mm几何上的有限体积均质化，见7.4节 |
| HBM3E NCF+bump/BEOL 等效 | 0.2991, 0.2991, 1.2250 | 1.438 | B/C | 20% SAC、80% NCF体积混合 |
| HBM4 MR-MUF+bump/BEOL 等效 | 1.3037, 1.3037, 1.2250 | 1.558 | C/D | 20% SAC、80% MUF/EMC体积混合 |
| HBM3E TSV-Si 等效 | 130.847, 130.847, 131.688 | 1.721 | C/D | Cu/Si圆柱夹杂；5 μm直径、55 μm pitch |
| HBM4 TSV-Si 等效 | 131.699, 131.699, 133.375 | 1.733 | C/D | HBM3E Cu面积分数的2倍，作敏感性中心值 |

体积热容对稳态结果无影响，但会影响瞬态时间常数。本轮已按约320 K公开$\rho c_p$数据和当前TSV/bump体积分数闭合；active层按用户要求保持不变。NCF/MUF仍是跨封装类比的C/D级材料，取得目标配方DSC或瞬态结构函数后应优先替换。

### 7.1 基础材料参数

3D-ICE当前采用常数材料参数。单晶Si在300--400 K内明显随温度下降；NIST汇编给出可用工程式$k_{Si}(T)=28600/(T-100)$ W/(m·K)[S12]。本模型取约320 K的130 W/(m·K)，300 K和373 K敏感性端点分别约143和105 W/(m·K)。其余均质化计算使用：

| 基础材料 | k [W/(m·K)] | Cv [MJ/(m³·K)] | 来源 |
|---|---:|---:|---|
| Si | 130 | 1.710 | 320 K NIST solid-Si heat capacity |
| Cu | 390 | 3.45 | 约320 K工程值；Cv：项目 GDS 等效脚本基线 |
| NCF | 0.2 | 1.37 | k：[S6]；Cv：公开3D-integration材料表类比 |
| EMC/MUF 代理 | 0.88 | 1.52 | k：[S13]；Cv：公开PBGA mold基线 |
| SAC solder | 58 | 1.71 | SAC305厂商密度与比热数据 |

### 7.2 Microbump/underfill 键合层等效

Chalise和Cahill对商用HBM2的3$\omega$测量得到：memory层面内$140\pm13$ W/(m·K)、polymer/solder bump层贯穿方向约2 W/(m·K)，整颗HBM约$(k_{xy},k_z)=(100\pm10,7\pm0.7)$ W/(m·K)[S10]。其X-ray还显示bump金属约占该层20%，故本模型采用$f_b=0.20$，而不再把不同来源的20 μm直径和50 μm pitch机械拼接成精确量产几何。

```text
f_b = 0.20
```

面内孤立圆柱用Maxwell解：

```text
kxy = k_m × [k_b + k_m + f_b(k_b-k_m)]
             / [k_b + k_m - f_b(k_b-k_m)]
```

HBM3E取$k_m=0.2$ W/(m·K)的NCF，HBM4取$k_m=0.88$ W/(m·K)的MUF代理，$k_b=58$ W/(m·K)。$k_z$不再采用体材料面积并联。先以HBM3E 720 μm堆栈为控制体，扣除Si、TSV-Si和active层名义热阻$R''_{other}=4.90$ μm·m·K/W，再令堆栈满足[S10]的$k_{z,stack}=7$ W/(m·K)：

```text
kz,bond = (8×15) / [720/7 - 4.90] = 1.225 W/(m·K)
```

该层因此是“NCF/MUF+bump+未显式BEOL/界面”的封装级等效体，不是纯焊料体材料。Colgan等的microbump实测也显示简单体材料模型会显著低估面积热阻[S7]。若取得目标器件的实测$R''_{bond}$，直接使用：

```text
kz,calibrated = t_bond / R''_bond
```

### 7.3 TSV-Si 等效

HBM3E 采用代表性的 5 μm Cu TSV 直径 [S8] 和 55 μm pitch [S9]。这两个数来自不同公开参考，用于建立可复现的代表性组合，不代表某一 HBM3E 量产产品的精确几何：

```text
f_TSV = π × 2.5² / 55² = 0.00649089
```

贯穿方向的连续Cu柱按面积并联；面内方向按圆柱Maxwell解而不是Reuss下界：

```text
kz  = f_TSV k_Cu + (1-f_TSV) k_Si
kxy = k_Si [k_Cu+k_Si+f_TSV(k_Cu-k_Si)]
             / [k_Cu+k_Si-f_TSV(k_Cu-k_Si)]
```

由此得到表中的HBM3E值。HBM4把Cu面积分数加倍：

```text
f_TSV,HBM4 = 2 × f_TSV,HBM3E = 0.0129818
```

加倍的依据是 HBM4 I/O 从 1024 bit 增至 2048 bit，但真实 TSV 数量、pitch 和分布并未公开，因此这是 D 级灵敏度假设，不是 HBM4 工艺参数。

### 7.4 单模块 active 层等效

每个 2 μm active/source 层已简化成一个 `11 mm × 11 mm` 模块。简化前的参考几何为：

- `10.5 mm × 10.5 mm` Si 核心；
- 每侧宽 250 μm 的 EMC 环带；
- 总面积 `121 mm²`。

面积分数为：

```text
f_Si  = 10.5² / 11² = 0.911157
f_EMC = 1 - f_Si    = 0.088843
```

垂直热导率采用面积并联平均：

```text
kz = f_Si × k_Si + f_EMC × k_EMC
   = 118.529 W/(m·K)
```

`ACTIVE_LAYER_EQ`的1.6255 MJ/(m³·K)为本轮明确冻结的旧值，不再由已经更新到320 K的Si/EMC基础热容反推；该项需要在active层建模方案确定后单独校准。

面内方向在44×44计算网格上求解$\nabla\!\cdot(k\nabla T)=0$，两侧单位温差、其余边界绝热，由总热流反演；不再只取穿过中心的串联路径。两个方向因几何对称均为：

```text
kxy = 16.566 W/(m·K)
```

该等效保持active层的总热容量与竖直面积导热贡献，但会消除bank、PHY和TSV/I/O局部热点。完整计算可由`../thermal_calibration/calibrate_conductivity.py --check`复现。

## 8. 功耗模型与整体 HBM 功耗输入

论文 [S6] 的热仿真工况对每个 DRAM core die 设置 2 W，其中 bank 区域合计 1.5 W、TSV 区域 0.5 W；logic die 设置 2 W。本模型在单模块化后保留每个 die 的总功耗，不再保留其内部空间分配：

- 每个 `DRAM_ACTIVE_EQ`：2.0 W；
- `BASE_ACTIVE_EQ`：2.0 W；
- HBM3E 总功耗：`8 × 2 + 2 = 18 W`；
- HBM4 总功耗：`12 × 2 + 2 = 26 W`。

上述 18 W 和 26 W 是 B 级论文比较工况，不是 Micron、SK hynix 或 Samsung 的产品 TDP。

若上游只能提供一个整体功耗 `P_HBM`，默认采用等 active-die 分配：

```text
HBM3E 8H：P_each = P_HBM / 9
HBM4 12H：P_each = P_HBM / 13
```

生成的 3D-ICE 功耗向量分别只有 9 和 13 个值，顺序从底部 base die 到顶部 DRAM die。该映射严格满足：

```text
Σ P_active_module = P_HBM
```

等 die 分配继承了 [S6] 中每个 die 均为 2 W 的基准，但对于真实工作负载仍属于 D 级假设。如果后续获得 base/PHY 功耗占比 `r_base`，建议改为：

```text
P_base = r_base × P_HBM
P_DRAM,i = (1 - r_base) × P_HBM / N_DRAM
```

当前 `.flp` 不含任何 `power values`，外部 trace 是唯一功耗源。上述每层 2 W 仅保留为论文基准和验证向量，不会在模型加载后先执行。外部只有一个 `P_HBM` 时，功耗转换器必须先按 9/13 个 active module 展开，再写入 trace。

## 9. 与完整芯片封装集成

当前解析器不支持在一个 `.stk` 中直接 `include/import` 另一个 `.stk`。集成 HBM、计算 die 和 interposer 时，需要：

1. 把 HBM 材料、layer、die 和 stack 声明合并到最终系统 `.stk`；
2. 保留或重新引用本目录的 `.flp` 和 `.layout`；
3. 在 HBM 底部添加 HBM-to-interposer microbump/underfill 层；
4. 添加 silicon interposer、计算 die、封装基板和必要的 RDL/键合结构；
5. 根据真实封装添加顶部 TIM、lid、cold plate 或其他散热路径；
6. 在完整封装的最外层设置热边界；
7. 在同一个热网络中联合求解。

完成集成后可运行：

```bash
make
bin/3D-ICE-Server path/to/integrated_package.stk \
  --power-trace path/to/power.ptrace \
  --output-dir results
```

交付 `.stk` 默认使用 `transient step 0.01, slot 0.01`，仅作为外部 trace 接口的初始时间设置；应按真实功耗采样周期修改。Trace 每行必须包含全部 active module，顺序从底部到顶部。

## 10. 输出

两个 `.stk` 已预置：

- 各 active 层的 `Tflp` 平均温度；
- base active 模块的最大温度；
- 顶部 DRAM 和 base active 的 `Tmap`；
- 整个 HBM 的 `T3d` VTK 输出。

合并到完整封装时，需要根据最终 die ID 和输出目录调整这些语句。

## 11. 已知限制与优先校准项

1. 厂商没有公开完整 die 厚度、TSV 坐标、BEOL、bond 配方和功耗图；本模型不能用于产品 sign-off。
2. 3D-ICE 在当前网格下使用等效材料窗口，不解析每一根 5-20 μm TSV 或 microbump。
3. BEOL 被折叠进 2 μm active/source 层，没有单独建模。
4. 被动衬底中的边缘 EMC 仍通过 `.layout` 显式表示；2 μm active 层中的 Si/EMC 已均质化。
5. HBM3E 的 342 μm 顶层被动 Si 是高度闭合假设，应优先用真实截面替换。
6. HBM4 的双倍 TSV Cu 面积分数与 MR-MUF 热物性需要实测校准。
7. 单模块 active floorplan 保持总功耗、垂直导热面积贡献和热容量，但不能预测 bank 或 TSV/I/O 局部热点。
8. 18 W/26 W 仅为论文基准；真实仿真必须使用系统或器件级功耗轨迹。
9. 体积热容中的 D 级参数不影响稳态温度，但会影响瞬态响应。
10. 当前模型无TIM和热边界，不能在当前3D-ICE实现中独立运行；必须先并入带真实热边界的完整封装。

## 12. 参数来源

### [S1] Micron HBM3E Product Brief，Rev. C，2023

用于：24/36 GB、8H/12H、11 mm × 11 mm × 0.72 mm、>9.2 Gb/s、>1.2 TB/s。

https://assets.micron.com/adobe/assets/urn:aaid:aem:b710d8f2-7f66-44c1-a234-456e2b986347/renditions/original/as/hbm3e-product-brief.pdf

### [S2] Micron HBM3E 产品页

用于：24 GB 8H、1024 I/O、16 channels、>1.2 TB/s，以及 8H/12H 产品信息。

https://www.micron.com/products/memory/hbm/hbm3e

### [S3] Micron HBM4 产品页

用于：36 GB 12H、2048 I/O、>11 Gb/s、>2.8 TB/s；同时说明 HBM 制造包含 TSV dies、较厚且无穿透 TSV 的顶 die 和 logic die。

https://www.micron.com/products/memory/hbm/hbm4

### [S4] SK hynix，12-layer HBM4 样品公告，2025

用于：36 GB、>2 TB/s 和 Advanced MR-MUF 技术路线。

https://news.skhynix.com/en/sk-hynix-ships-world-first-12-layer-hbm4-samples-to-customers/

### [S5] SK hynix，HBM4 完成开发与量产准备公告，2025

用于：2048 I/O、JEDEC 8 Gb/s 基线、>10 Gb/s 产品速率，以及 Advanced MR-MUF 说明。

https://news.skhynix.com/en/sk-hynix-completes-world-first-hbm4-development-and-readies-mass-production/

### [S6] Song 与 Yoon，JSTS，2025

J. H. Song and S. W. Yoon, “Comparative Study of Thermal Dissipation in Increasing DRAM Layers of HBM Using 3D FEA Simulations,” *Journal of Semiconductor Technology and Science*, 25(2), 142-147, 2025。DOI：10.5573/JSTS.2025.25.2.142。

用于：11 mm × 11 mm 参考尺寸、32 μm 普通 die、156 μm 顶 die、15 μm die 间隙、Si/Cu/NCF/solder/EMC 热导率，以及每个 DRAM 2 W、logic die 2 W 的论文热负载。

https://doi.org/10.5573/JSTS.2025.25.2.142

### [S7] IBM microbump 热阻测量，2013

用于：25 μm microbump、16 μm 键合后高度、50/71/100 μm pitch、0.55 W/(m·K) underfill，以及“实测界面热阻高于简单体混合模型”的校准依据。

https://www.electronics-cooling.com/2013/03/measured-thermal-resistance-of-microbumps-in-3d-chip-stacks/

### [S8] IEEE Electron Devices Society，HBM 演进资料，2025

用于：代表性的 20 μm microbump、50 μm pitch、5 μm TSV 直径，以及 HBM3E/HBM4 I/O 对比。

https://www.ieee.org/ns/periodicals/EDS/EDS-OCTOBER-2025-HTML/InnerFiles/LandPage.html

### [S9] Ohba 等，Electronics，2022

T. Ohba et al., “Review of Bumpless Build Cube (BBCube) Using Wafer-on-Wafer (WOW) and Chip-on-Wafer (COW) for Tera-Scale Three-Dimensional Integration (3DI),” *Electronics*, 11(2), 236, 2022。DOI：10.3390/electronics11020236。

用于：与 HBM 相当的 conventional 3DI 结构中 55 μm TSV pitch，以及 microbump/TSV 等效建模的参考尺度。该论文表格给出的 conventional TSV 直径为 8 μm；本模型采用的 5 μm 直径另取自 [S8]，因此 5 μm/55 μm 组合明确归类为代表性假设。

https://doi.org/10.3390/electronics11020236

### [S10] Chalise and Cahill，HBM各向异性热导率实测，2023

用于：商用HBM2 memory层$k_{xy}=140\pm13$ W/(m·K)、polymer/solder层$k_z\approx2$ W/(m·K)、整颗器件$(k_{xy},k_z)=(100\pm10,7\pm0.7)$ W/(m·K)，以及约20% bump面积占比。

https://doi.org/10.48550/arXiv.2303.06785

### [S11] Colgan et al.，microbump面积热阻实测，2012

用于：50 μm pitch、约25 μm直径、16.1 μm高度、带underfill的单位面积热阻8.0 K·mm²/W，验证接触/界面项不能被简单体材料并联忽略。

https://doi.org/10.1109/STHERM.2012.6188818

### [S12] NIST silicon温度相关热导率汇编

用于：300--600 K工程式$k_{Si}(T)=28600/(T-100)$ W/(m·K)及320 K中心值130 W/(m·K)。

https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication400-86.pdf

### [S13] Kim and Yoo，stacked package DAF/EMC公开参数

用于：常规EMC 0.88 W/(m·K)的工程锚点。该来源为公开专利，不代表HBM厂商MUF配方。

https://patents.justia.com/patent/20260047392

## 13. 数值兼容性验证

2026-08-23，使用校准后的材料张量和当前仓库的 `3D-ICE-Server --power-trace`，在仅存在于 `/tmp` 验证副本中的临时顶部边界下完成单slot transient求解。验证功耗由外部 trace 提供；交付 `.flp` 不含功耗，交付 `.stk` 不含该边界。

| 模型 | Thermal cells | Connections | Factorization | 外部trace |
|---|---:|---:|---:|---:|
| HBM3E 8H | 50,336 | 293,568 | 4.21 s | 9列，1 slot通过 |
| HBM4 12H | 73,568 | 430,848 | 11.09 s | 13列，1 slot通过 |

该测试仅证明 `.stk/.flp/.layout` 的解析、输出 ID 和求解器兼容性，不构成温度精度验证。温度验证仍需要实测封装热阻、真实冷板/接触边界和工作负载功耗。
