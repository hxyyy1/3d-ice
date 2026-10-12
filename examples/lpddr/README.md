# LPDDR5X 1-Pkg 与 LPDDR6 1-Pkg 校准参考热模型

本目录包含两套面向 3D-ICE 4.0 的 LPDDR 单封装子模型：

- `lpddr5x_1pkg/model.stk`：16 GB LPDDR5X，8颗物理die、4个z向tier，每tier并排2颗die；
- `lpddr6_1pkg/model.stk`：16 GB LPDDR6前瞻模型，8颗16 Gb die、4个z向tier，每tier并排2颗die。

LPDDR5X模型已使用Samsung官方4-tier/0.65 mm公告、Micron 496-ball mechanical drawing、公开LPDDR5X die size、移动PoP截面和DAF供应商资料进行交叉校准。LPDDR6尚无公开量产package mechanical drawing，因此只对die容量/面积和FBGA类型进行了约束，外部包络与层厚仍沿用LPDDR5X校准结构作为前瞻假设。

两套模型均不包含预设功耗或热边界；必须从外部power trace输入功耗，并在完整封装中添加真实散热边界。

## 1. 证据等级

| 等级 | 含义 |
|---|---|
| A | 厂商/标准组织公开产品数据或mechanical drawing |
| B | 同行评审论文、IEEE/IMAPS资料或官方材料/封装供应商数据 |
| C | 根据A/B数据和明确公式得到的推导值 |
| D | 因缺少公开截面而采用的假设，必须后续校准 |

文中`[S1]`至`[S15]`对应第11节来源；体积热容的完整材料来源和公式统一列于`../thermal_calibration/thermal_conductivity_calibration.tex`。

## 2. 校准结论

### 2.1 LPDDR5X 1-Pkg

Samsung 0.65 mm LPDDR5X公告明确说明：16 GB package采用4-tier结构，每个tier包含2颗LPDDR DRAM，因此总计8颗物理die，而不是4颗die [S1]。

| 参数 | 校准值 | 等级与来源 |
|---|---:|---|
| 容量 | 16 GB | A：[S1] |
| 物理die数量 | 8 | A：4 tiers × 2 dies/tier，[S1] |
| z向功耗tier | 4 | A/C：[S1] |
| Package footprint | 14 mm × 12.4 mm | A/C：496-ball机械图及Samsung package类型，[S2][S3] |
| Package总高 | 0.65 mm | A：[S1] |
| BGA ball count | 496 | A/C：[S2][S3] |
| BGA standoff | 0.20 mm | A：[S2] |
| 单颗die公开尺寸 | 6.55 mm × 5.60 mm | B：[S4] |
| 模型网格对齐die尺寸 | 6.50 mm × 5.60 mm | C：对公开尺寸取整 |
| 每颗die总厚度 | 50 μm | B：[S5][S7] |
| DAF厚度 | 10 μm | B：[S6][S7] |
| Package substrate | 100 μm | B：[S5] |
| Top EMC | 110 μm | C：由总高度闭合；接近[S5]的120 μm公开截面 |

该模型是厂商中立的校准组合：容量/4-tier信息来自Samsung，14×12.4 mm/496-ball/0.20 mm ball height来自Micron mechanical drawing。它不对应单一具体料号，但内部结构不再是无约束猜测。

### 2.2 LPDDR6 1-Pkg

Samsung已公开LPDDR6支持16-128 Gb、x24及357/518/1295 FBGA；SK hynix和Samsung的首代LPDDR6 die均为16 Gb [S9]-[S11]。公开资料尚未给出16 GB package的物理堆叠和mechanical drawing。

| 参数 | 前瞻值 | 等级与来源 |
|---|---:|---|
| 目标容量 | 16 GB | C/D：8 × 16 Gb |
| 物理die数量 | 8 | D：容量闭合假设 |
| z向功耗tier | 4，每tier 2 dies | D：沿用LPDDR5X拓扑 |
| Package footprint | 14 mm × 12.4 mm | D：沿用LPDDR5X |
| Package总高 | 0.65 mm | D：沿用LPDDR5X |
| BGA ball count | 518 | A：[S9] |
| BGA standoff/diameter | 0.20/0.27 mm | D：沿用496-ball机械尺度 |
| 单颗die目标面积 | 约44.5 mm² | B/C：[S12] |
| 模型die尺寸 | 6.25 mm × 7.00 mm = 43.75 mm² | C：网格对齐近似 |
| Die/DAF/substrate/EMC厚度 | 与LPDDR5X相同 | D |

因此LPDDR6仍是前瞻参考模型；物理拓扑具有合理约束，但不能视为量产package截面。

## 3. 建模范围与物理拓扑

LPDDR模型采用wire-bond stacked-die FBGA/PoP拓扑：

```text
Top EMC
Tier 4: 两颗并排DRAM die
DAF
Tier 3: 两颗并排DRAM die
DAF
Tier 2: 两颗并排DRAM die
DAF
Tier 1: 两颗并排DRAM die
DAF
BT/organic package substrate
BGA solder/air collapsed layer
PCB或下层package（未包含）
```

每个tier在3D-ICE中只占一个z高度，但`.layout`内包含两块并排Si区域。模型不显式解析wire bond；其热传导和焦耳热相对主垂直路径通常较小，但高速I/O下仍需复核。

模型包含BGA standoff，但不包含PCB、SoC、interposer、顶层TIM/lid或任何热边界。当前3D-ICE实现不能稳定构建完全无散热边界的独立模型，必须先并入完整系统并添加真实边界。

## 4. 垂直结构与高度闭合

两套模型使用同一参考高度分配：

```text
110 μm top EMC

Tier 4: 2 μm active + 48 μm passive Si
10 μm DAF
Tier 3: 2 μm active + 48 μm passive Si
10 μm DAF
Tier 2: 2 μm active + 48 μm passive Si
10 μm DAF
Tier 1: 2 μm active + 48 μm passive Si
10 μm bottom DAF

100 μm package substrate
200 μm BGA standoff
------------------------------------------------
650 μm package total
```

高度闭合：

```text
110 + 4 × (2 + 48) + 4 × 10 + 100 + 200 = 650 μm
```

参数交叉关系：

- Samsung给出0.65 mm总高、4 tiers、2 dies/tier [S1]；
- Micron 496-ball mechanical drawing给出约0.20 mm ball height和约0.68 mm总高参考 [S2]；
- 移动PoP公开截面给出50 μm die、100 μm upper substrate和120 μm top EMC [S5]；
- DAF厂商明确提供LPDDR用5/10/20 μm产品，薄die堆叠论文也使用50 μm die + 10 μm DAF [S6][S7]；
- 因此选择50 μm总die、10 μm DAF、100 μm substrate、200 μm BGA，剩余110 μm EMC。

2 μm active是热源数值层，不表示真实晶体管/BEOL恰好为2 μm；48 μm passive Si与其合计为50 μm物理die厚度。

## 5. 层数与功耗模块数

| 组成 | 3D-ICE层数 | 物理含义 |
|---|---:|---|
| Top EMC | 1 | 模封与高度闭合 |
| Active/source tiers | 4 | 每层对应一个2-die tier |
| Passive Si/EMC tiers | 4 | 每层layout含两颗die |
| DAF/EMC tiers | 4 | 每层layout含两块DAF |
| Package substrate | 1 | BT/organic substrate |
| BGA collapsed layer | 1 | solder balls + air |
| 合计 | 15 | 8颗物理die、4个z向tier |

外部trace仍只需要4列，而不是8列，因为模型的功耗分辨率为tier级。若各物理die功耗相同：

```text
P_tier = P_pkg / 4
P_die  = P_pkg / 8
```

## 6. `.layout`与`.flp`

### LPDDR5X

`dram_silicon.layout`每个tier包含两块网格对齐Si：

```text
Die A: position (500, 3400), size 6500 × 5600 μm
Die B: position (7000, 3400), size 6500 × 5600 μm
```

该尺寸近似公开6.55×5.60 mm die [S4]。`daf.layout`在相同位置放置两块DAF，外围材料保持EMC。

### LPDDR6

```text
Die A: position (750, 2600), size 6250 × 7000 μm
Die B: position (7000, 2600), size 6250 × 7000 μm
```

每颗面积43.75 mm²，用于近似公开约44.5 mm²首代LPDDR6 die [S12]。位置与长宽比仍属D级假设。

`dram_active.flp`用一个`DRAM_ACTIVE_EQ`覆盖整个14×12.4 mm tier，网格为56×62。`.flp`不含`power values`，外部trace是唯一功耗源。

## 7. 材料及等效关系

下表使用SI单位：

| 材料/等效层 | LPDDR5X kx,ky,kz [W/(m·K)] | LPDDR6 kx,ky,kz [W/(m·K)] | Cv [MJ/(m³·K)] | 等级 |
|---|---:|---:|---:|---|
| Silicon | 130,130,130 | 130,130,130 | 1.710 | B/C；约320 K参考值[S14] |
| EMC | 0.88,0.88,0.88 | 0.88,0.88,0.88 | 1.520 | B/C；公开PBGA mold基线 |
| DAF | 0.3,0.3,0.3 | 0.3,0.3,0.3 | 1.500 | B/D |
| Package substrate等效 | 33.071,33.071,0.447 | 同左 | 1.7554 | C/D；BT/Cu体积守恒混合 |
| Active tier等效 | 6.649,1.589,55.027 | 5.661,1.980,65.961 | 1.612/1.614 | C；有限体积均质化 |
| BGA solder/air等效 | 0.0275,0.0275,0.6230 | 0.0275,0.0275,0.6247 | 0.2807/0.2931 | C/D；SAC305/air体积混合 |

### 7.1 Active tier

LPDDR5X每tier Si面积分数：

```text
f_Si = 2 × 6.5 × 5.6 / (14 × 12.4) = 0.419355
```

LPDDR6每tier：

```text
f_Si = 2 × 6.25 × 7.0 / (14 × 12.4) = 0.504032
```

垂直热导率按Si/EMC面积并联。面内方向不再使用穿过die中心的一维路径，而是在现有56×62网格上求解$\nabla\!\cdot(k\nabla T)=0$，两侧施加单位温差、正交边界绝热，再由总热流反演$k_x$和$k_y$。这避免旧LPDDR5X $k_x=11.677$ W/(m·K)仅代表die带中心路径、没有计入上下EMC旁路面积的问题。active tier热容按用户要求保持原值，不随新的Si/EMC基础热容重算。

### 7.2 Package substrate

基材本征值仍采用BT-glass laminate的0.34 W/(m·K)[S14]。由于公开mechanical drawing没有铜叠层，本模型采用2层、每层12 μm Cu、面内铜覆盖率35%的D级中心值；铜层与介质在面内并联、贯穿方向串联。该项把旧各向同性0.34修正为$(33.071,33.071,0.447)$ W/(m·K)。真实铜图或过孔密度可直接替换上述三个输入量。

热容采用公开BT substrate的$\rho=1.91$ g/cm³、$c_p=837.36$ J/(kg·K)，即约1.60 MJ/(m³·K)，再与有效Cu体积分数$f_{Cu}=2\times12/100\times0.35=0.084$混合，得到1.7554 MJ/(m³·K)。旧值1.60只代表纯BT matrix，未计入模型已经使用的铜层。

### 7.3 BGA collapsed layer

LPDDR5X采用496个、约0.27 mm直径、0.20 mm高的SAC球 [S2]：

```text
f_ball = 496 × π × (0.27/2)² / (14×12.4) = 0.163587
```

LPDDR6采用公开518-ball类型 [S9]，直径/高度暂沿用LPDDR5X：

```text
f_ball = 518 × π × (0.27/2)² / (14×12.4) = 0.170843
```

SAC与air的面积并联只给出$k_z\simeq9.5$--9.9 W/(m·K)的体材料上界。Johnson等的BGA子模型表明焊盘/基板热收缩会使简单面积法高估约一个数量级[S14]。因此模型再串联名义面积热阻$R''_{c}=3.0\times10^{-4}$ m²K/W，得到表中的0.6230/0.6247 W/(m·K)；面内按未灌封球阵列取air的0.0275 W/(m·K)。LPDDR6球径/高度和$R''_c$仍应由正式mechanical drawing与实测结构函数替换。

热容使用SAC305的$C_v\approx1.71$ MJ/(m³·K)和320 K air的0.00111 MJ/(m³·K)按相同球面积分数混合，得到0.2807/0.2931 MJ/(m³·K)。

完整公式、敏感性边界以及可复现脚本见`../thermal_calibration/thermal_conductivity_calibration.tex`和`../thermal_calibration/calibrate_conductivity.py`。

## 8. 功耗输入

上游只需提供一个`P_pkg(t)`，转换为4个tier值：

```text
P_T1 = P_T2 = P_T3 = P_T4 = P_pkg / 4
```

Trace顺序为底部T1到顶部T4。交付`.stk`默认：

```text
transient step 0.01, slot 0.01 ;
```

应按真实功耗采样周期修改。交付`.flp`无预设功耗，不会先执行基准值。

Micron资料给出LPDDR5X约4 pJ/bit和self-refresh <1 mW [S13]，但这不足以定义具体package TDP；LPDDR6也只有相对能效信息。因此两套模型均必须使用外部实测或系统级`P_pkg(t)`。

## 9. 与完整封装集成

1. 合并material/layer/die/stack到系统`.stk`；
2. 保留`.flp`和两个`.layout`；
3. 用正式mechanical drawing修正BGA并连接PCB/下层package；
4. 加入SoC、interposer、PCB、TIM/lid/cold plate或空气路径；
5. 在系统外表面设置真实热边界；
6. 把每个LPDDR placement的`P_pkg(t)`展开为4列trace；
7. 使用`3D-ICE-Server --power-trace`联合求解。

## 10. 残余不确定性

### LPDDR5X

- 16 GB/8-die/4-tier/0.65 mm为官方；
- 14×12.4 mm、496 balls、0.20 mm BGA来自同类公开mechanical drawing，并非Samsung该料号图纸；
- 50 μm die、10 μm DAF、100 μm substrate、110 μm EMC由多源交叉约束，但仍非同一截面实测；
- 两颗die的平面摆放和wire-bond路径仍是近似。

### LPDDR6

- 16 Gb die、约44.5 mm²、x24和518 FBGA具有公开依据；
- 16 GB/8-die/4-tier、14×12.4×0.65 mm和BGA尺寸均为前瞻假设；
- 发布量产mechanical drawing后应整体替换package几何，而不是仅微调EMC。

两模型均忽略wire-bond显式热传导；substrate铜走线已均质化，但真实图形、过孔和界面热阻仍未知。稳态时Cv不影响温度，但瞬态时间常数对这些D级热容参数敏感。

## 11. 参数来源

### [S1] Samsung 0.65 mm LPDDR5X公告

用于：12/16 GB、0.65 mm、4-tier、每tier 2 dies、热阻改善21.2%、未来6/8-tier路线。

https://news.samsung.com/global/samsung-electronics-begins-mass-production-of-industrys-thinnest-lpddr5x-dram-packages-for-on-device-ai

### [S2] Micron 496-ball LPDDR5 mechanical drawing

用于：14×12.4 mm、496 balls、约0.27 mm球径、0.20±0.03 mm ball height、约0.68 mm package height和SAC302材料。

https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/8885/496b-y31m-qdp-8dp-mobile-lpddr5.pdf

### [S3] Samsung LPDDR产品页

用于：LPDDR5X支持496/563/441/315/245 FBGA，以及LPDDR6支持357/518/1295 FBGA。

https://semiconductor.samsung.com/dram/lpddr/

### [S4] FMS 2025 DRAM physical analysis presentation

用于：Samsung 16 Gb LPDDR5X die约6.55×5.60 mm、36.68 mm²。

https://files.futurememorystorage.com/proceedings/2025/20250807_DRAM-304-1_Jeongdong-Choe_Short-version.pdf

### [S5] Boeing/IEEE RWW mobile PoP analysis

用于：公开移动DRAM截面中的50 μm die、100 μm upper substrate和约120 μm top EMC。

https://rww2020.iot.ieee.org/wp-content/uploads/sites/124/2020/01/01-26-2020-Timothy-T-Lee-Boeing-Presentation.pdf

### [S6] LG Chem LPDDR DAF

用于：LPDDR/stacked memory可用5、10、20 μm DAF。

https://www.lgchem.com/product-detail/daf?lang=en_US

### [S7] Thin-die/DAF公开研究

用于：50 μm Si die与10 μm DAF组合，以及多层memory stack常见5/10 μm DAF。

https://www.researchgate.net/publication/303597835_Ultrasonic_Bonding_of_Die_Attach_Film_DAF-Laminated_Thin_Silicon_Dies_on_Glass_Substrates_at_Room_Temperature

### [S8] Micron Y52P LPDDR5X data sheet

用于：D1/D2/D4/D8 die-count编码、quad/eight-die电气组织，以及0.675 mm WFBGA的body/ball机械尺度。

https://www.mouser.com/catalog/specsheets/Micron_10-16-2025_315b-441b-561b-563b-y52p-sdp-ddp-qdp-8dp-lpddr5x.pdf

### [S9] Samsung LPDDR6产品页

用于：16-128 Gb、最高14.4 Gb/s、x24和357/518/1295 FBGA。

https://semiconductor.samsung.com/dram/lpddr/

### [S10] SK hynix 1c LPDDR6公告

用于：16 Gb LPDDR6 die和相对LPDDR5X的性能/能效改善。

https://news.skhynix.com/en/1c-lpddr6-development-2026/

### [S11] ISSCC 2026 LPDDR6 disclosures

用于：SK hynix 16 Gb/14.4 Gb/s与Samsung 16 Gb/12.8 Gb/s首代die。

https://submissions.mirasmart.com/ISSCC2026/PDF/ISSCC2026AdvanceProgram.pdf

### [S12] ISSCC 2026公开分析

用于：Samsung首代16 Gb LPDDR6 die约44.5 mm²；该面积为二级公开提取，非package图纸。

https://morethanmoore.substack.com/p/lpddr6-samsungsk-hynix-at-isscc-2026

### [S13] Micron LPDDR5X CAMM2 Technical Brief

用于：约4 pJ/bit与self-refresh <1 mW参考。

https://assets.micron.com/adobe/assets/urn:aaid:aem:4e076108-df95-4c2d-8785-06c30049afb5/renditions/original/as/lpddr5x-camm2-technical-brief.pdf

### [S14] 基础材料与BGA等效方法

Si温度相关工程式：https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication400-86.pdf

BT substrate与BGA等效方法：https://doi.org/10.1109/ITHERM.1998.689523

### [S15] Kim and Yoo，stacked package DAF/EMC公开参数

用于：四层stacked-die示例中的常规EMC 0.88 W/(m·K)、底层绝缘DAF 0.3 W/(m·K)，并界定高导热DAF需要专用填料而不能默认采用。

https://patents.justia.com/patent/20260047392

## 12. 数值兼容性验证

2026-08-23，使用校准后的材料张量和当前`3D-ICE-Server --power-trace`，在仅存在于`/tmp`验证副本中的临时顶部边界下完成单slot transient求解；交付模型无预设功耗和热边界。

| 模型 | Layers | Cells | Connections | Factorization | 外部trace |
|---|---:|---:|---:|---:|---:|
| LPDDR5X 1-Pkg | 15 | 52,080 | 301,996 | 3.06 s | 4列，1 slot通过 |
| LPDDR6 1-Pkg | 15 | 52,080 | 301,996 | 3.06 s | 4列，1 slot通过 |

该测试只证明`.stk/.flp/.layout`解析、外部trace和求解器兼容性，不构成产品温度精度验证。
