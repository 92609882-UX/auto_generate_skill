---
name: minecraft-labpbr-textures
description: 为 Minecraft 像素风材质包生成 Iris/LabPBR 的 _n 和 _s 贴图（16×16 底色图放大到 128×128）。用户提到 LabPBR、PBR 材质包、_n/_s 贴图、法线/高度/光滑度贴图生成时使用。
---

# Minecraft LabPBR 贴图生成（_n / _s）

这份 skill 记录了作者制作像素风 PBR 材质包的方法：从底色贴图（不带 `_n`、`_s` 后缀的原始贴图）直接算出 `_n` 和 `_s` 的每个通道，再合成。方法来自作者的经验，并用参考材质包"零雾构想 v5003"核对过：方块部分统计了约 1240 张，整包（物品、实体、盔甲、纹饰、连接纹理、模型改动、版本适配）也已逐张分析，见 `reference/pack-layout.md`。

不使用 Substance 3D Designer，全部由本文末尾的 Python 脚本完成。

## 前提

- 输入是原版风格的 16×16 底色贴图，或它放大后的版本（边长是 16 的倍数，每个原始像素是一个纯色方块）。
- 输出是 128×128：一个原始像素对应一个 8×8 块。下文的"块"都指这个 8×8 块。
- "亮度"= 0.299R + 0.587G + 0.114B，直接用 sRGB 数值，不做线性化。

## 工作目录和训练记录

- 作者的工作目录是 `E:\mcproperty\auto_generate`。开始工作前先请求访问这个文件夹，读其中的 `README.md` 和 `training_log.md`。
- `training_log.md` 记录了作者在历次训练里给出的修正和理由。**其中的结论优先于本文的默认值。**
- 参考材质包在 `E:\mcproperty\05‘s_resourcepacks`（主包是"零雾构想 v5003"的 zip）。
- 训练的做法见该目录下的 `TRAINING.md`。每轮训练结束，把新结论写进 `training_log.md`；结论稳定后，建议作者更新这份 skill。
- 文件夹里的 `labpbr_gen.py` 可能比本文末尾的版本新。两者不同时，用文件夹里的。

## 工作流程

1. 用工作目录里的 `labpbr_gen.py`；没有的话，把本文末尾的脚本原样保存为 `labpbr_gen.py`。需要 `numpy` 和 `Pillow`。
2. 拿到底色贴图。贴图在用户电脑上时，在用户的文件夹里就地处理，或只取需要的文件。
3. 对每张贴图先**看图**，再确定参数（见"每张贴图要定的参数"）。
4. 需要判断的参数（凸起范围、结构修正、混合材质的块、发光的块）先给出方案和理由，等作者确认。不要用单一阈值自动决定后直接批量生成。
5. 运行脚本生成 `_n`、`_s`，并按"交付约定"输出各通道灰度图。
6. 运行 `check_n`、`check_s` 检查，再把结果交给作者看灰度图。

批量处理时，把每张贴图的参数存成一份配置（JSON 或 Python 字典），方便作者修改后重跑。

## 交付约定

- 作者不进游戏预览，靠各通道的灰度图判断是否合格。
- 每张贴图交付：`xxx_n.png`、`xxx_s.png`，以及每个通道单独的灰度图 `xxx_n_R.png`、`xxx_n_G.png`、`xxx_n_B.png`、`xxx_n_A.png`、`xxx_s_R.png`……
- 默认把灰度图放在单独的 `channels/` 子文件夹，材质包目录里只留 `_n`、`_s`。作者另有要求时照作者的来。

## 整包做法（参考包「零雾构想 v5003」）

完整的数据、表格和命令见 `reference/pack-layout.md`。做整包时先读它。要点：

1. **分辨率**：方块、物品、实体、盔甲层一律放大到 **8 倍**（16×16 → 128×128，64×64 → 512×512），这样法线和 AO 才平滑。纹饰、字体、GUI 保持原尺寸。
   **底色贴图也要按同样的倍数放大、和 `_n`/`_s` 一起写进包** —— 光影是拿底色的尺寸去索引
   `_n` 里的高度的，两边分辨率不一致就会读错、出现大片波浪。这是整包能不能出视差的前提，
   详见下面第 13 条。
2. **LabPBR 声明**：`assets/minecraft/optifine/texture.properties` 写一行 `format=lab-pbr/1.3`。不需要 shaders 文件夹。
3. **覆盖范围**：只要有 `_n` 就一定配 `_s`；反过来不一定。透明的破坏裂纹（`destroy_stage_*`）两个都不做；火、岩浆、传送门、**粒子精灵图、炼药锅里的液体**这类没有实体表面的只做 `_s`（给透光和自发光），不做 `_n`；盔甲纹饰也只做 `_s`。没有 `_e` 贴图，自发光一律走 `_s` 的 A 通道。
   **不做的目录**：GUI 图标、状态效果图标、调色板（`palettes/`）、环境天空（`environment/`），以及 NeoForge `separate_transforms` 里 `perspectives.gui` 专用的 `*_gui.png` —— 光影照不到它们。
4. **物品 / 实体 / 盔甲层**：照常从底色明暗算高度、法线和 AO，但 `_n` 的 A 通道整张写 255（保持精灵是平的、不做视差），AO 保留（B 通道）。透明背景要洗干净：`_n` 用 127/127/255/255，`_s` 用 R=G=B=0、A=255。`_s` 的 B 一律 0。脚本用 `flat=True, flat_ao=True, transparent_flat=True` 和 `clear_alpha=True`。
5. **盔甲纹饰**：只有 `_s`。参考包里 R=127、G=0、B 和 A 随纹饰明暗升高（B 88–144、A 123–174）；空白像素 R=G=B=0、A=255。这套编码和 LabPBR 常见写法不同，照抄前先问作者。
6. **动画**：底色有 `.png.mcmeta` 时，`_n`/`_s` 要各带一份同样的 `.mcmeta`，否则光影下会错帧。
7. **连接纹理（去接缝）**：`optifine/ctm/` 里用 `method=overlay` + `connectBlocks`，把泥土接草地/菌丝/灰化土/土径、下界岩接菌岩时的硬边抹掉。贴图通常只在最上面 2 个原始像素有内容。参考包的两份配置见 `reference/pack-layout.md` 第 7 节。
8. **随机变体（破重复）**：石头、沙子、深板岩、基岩、沙砾类等 9 个方块族各多画 3 张逐像素变体，配好 `_n`/`_s`，再在 blockstate 里用 `"weight": 1` 随机选。树叶用 4 个 `y` 方向同权重随机。
9. **版本适配**：`pack.mcmeta` 用 `supported_formats`（参考包写 `[1, 64]`、`min_format`/`max_format` 放宽），`lang/zh_cn.json` 覆写 `pack.incompatible.confirm.*` 提示玩家强行加载。
10. **不照搬参考包的地方**：`_s` 的 G 通道按规范填，`_s` 的 R 不叠 HBAO。矿石颗粒的 G=219 是唯一例外。
11. **前置库 / 共享库并进主包，不另开资源包**：模组的前置库命名空间和本体不同（例如 Iron's Lib 的
    `irons_lib` 对 Iron's Spellbooks 的 `irons_spellbooks`），玩家装本体时必然一起装。直接在同一份
    资源包的 `assets/` 下多放一个命名空间目录即可，多命名空间互不冲突，用户不用多下载一个包。
12. **亮色布料不能当金属**：逐像素金属判据（灰色 `sat<0.20`）会把白色布袍整片判成银甲
    （`_s` 的 G=230）。盔甲层只认明显的金色镶边（`R≥170`、`G≥130`、`B<R−60`、`G>B+40`），
    其余按布面（B 20）/ 皮革；方块上真正的金属格栅才用原来的灰色判据。石质雕像和
    石头碎屑粒子不给自发光（`bright` 兜底会把整张灰噪点粒子点亮）。
13. **底色贴图必须和 `_n`/`_s` 同分辨率、一起放进包**（第 17 轮定案；这是视差正常的前提，
    比高度怎么调都重要）：
    * **光影读高度读的是 `_n` 的 A 通道，但索引坐标是拿「底色贴图」的尺寸算的。**
      Helian MMCO 的 `libs/Parallax.glsl`（`bilinearHeightSample`）就是
      `texelFetch(normals, ..., albedoTexSize)`。只把 `_n`/`_s` 放大到 128×128、底色还是
      模组自带的 16×16 时，光影只读到高度图的**左上角一小块**再拉伸铺满整个方块 ——
      掠射角下就是大片平滑波浪。这跟高度做多深、什么形态毫无关系，所以第 6～16 轮
      怎么调高度都还在。
    * **对照参考包**：零雾构想 v5003 是 **1282 底色 + 1264 `_n`**，方块都 128×128，
      两边同分辨率，所以它在同一套光影设置下视差正常。
    * **做法**：底色按 `_n`/`_s` 同样的 `cell` 倍做**最近邻**放大写进包（像素画外观不变），
      动画贴图把 `.mcmeta` 一起复制。脚本用 `gen_pbr.base_upscaled()` / `save_base()`；
      方块入口 `gen_pbr.WRITE_BASE = True`（默认开），实体/模型走 `MODS[...]['write_base'] = True`，
      各模组入口脚本都会自动带上。
    * **高度用底色亮度分档**（零雾的实际做法）：`height_from_colour()`，亮度 → `[lower, 255]`，
      按 `step`（实测多为 4 或 8）量化。亮处高、暗处低，一张图 6–11 档、密布小落差，
      处处参与视差。下限 `lower` 查下面「A 通道：高度」的档位表。实测和零雾同档
      （`stone_bricks` 207–255 7 档、`cobblestone` 199–255 8 档、`gravel`/`dirt` 199–255）。
      同一类颜色变体用同一个 `lower`。
    * **仍写平 A=255（只补 AO）的例外**：植物、树叶、玻璃、镂空石雕、雕像、地图标记、
      流体、水晶，以及物品 / 实体 / 盔甲层的精灵图。它们本来就是平的，给高度只会在
      透明边缘冒假边。除此之外的完整立方体面、家具台面都走真实视差。
    * **「面数多、UV 细小」的薄模型必须压平整张 A=255（第 19 轮定案）**：这是分辨率
      对上之后**仍然会波浪**的一类。POM 的位移是按 **UV 空间**走的：烛台、吊灯、火盆、
      神像、墓碑、方尖碑、灵魂吸收器这类模型由几十根 1~2 像素粗的细杆拼成，每块面比
      位移还窄，光线一步就跨出这块面 —— 光影用 `fract()` 把采样折回本岛（见下面
      「POM 是岛内步进」那条），于是一步就绕到岛的别的部位，掠射角下糊成作者看到的
      波浪。判据不靠肉眼：扫描 `models/block/*.json`（含 parent 链），一张贴图只要
      **没有任何实心立方体用它**，且用它的模型满足「元件数 ≥ 6」且「面的窄边中位数
      ≤ 3.5 像素」，就整张写 255（光影跳过视差、位移恒 0）、**AO 照常保留**。
      实现见 `tools/model_scan.py` 与 `gen_pbr.model_flatten_stems()`，
      `classification.csv` 里标 `+thin_flat`。**别误伤大平面模型**：木桶、斜板、
      地毯、暗祭坛这种要道面宽度 ≥ 4 像素、不会波浪的，仍保留真实视差。
      （第 22 轮把这条推广成**按 texel 分**：同一张图集里大面给视差、细面压平 +
      边界挡墙，见下面「模型图集：大面给真实视差」那条。）
    * **模型图集：大面给真实视差、细面压平，边界留 A=255 挡墙（第 22 轮定案）**。
      屠夫工艺的屠夫台 / 展示柜 / 柜台这类图集（64/80 像素）里 **同时** 混着两种面：
      台面 / 柜身是「一块面用一个放大 UV 岛」（4×4 ~ 3.2×4），木框 / 卡子 / 细杆是
      0.2~1.5 像素宽的窄面。整张给视差，细面就波浪（第 19 轮作者的反馈）；整张压平，
      大面就没视差（第 21 轮改完后作者的新反馈）。做法：
        1. 扫 `models/block/*.json`（含 parent 链），一张贴图只要被 **UV 窄边 ≥ 3.0
           （16 格空间）** 的面用到，就把那个 UV 矩形（内缩 2 个原始像素）标成「大面」；
        2. 大面内圈给高度，其余 texel 的 `_n` A 写 255（法线、AO 照常算，细件仍有明暗）；
           **第 24 轮起大面的高度不再用真实分档（木板 207 / 展示柜 215），而是 255 附近
           的窄带 `[244, 253]`、`step=2`**：家具是 4×4 的 UV 岛（`quadSize≈4`），真实分档
           下实测位移 **0.17~0.45 个岛宽**、掠射角撕成斜纹；窄带下射线几步就撞面，只剩
           **0.06~0.16 个岛宽**，既保留一点真实视差、又不再波浪；
        3. 内缩那一圈 255 是**挡墙**：光影的 POM 在本面自己的 UV 岛里步进，`clampCoordRange()`
           用 `fract()` 折回（见下一条），步到岛边界会折到对边、采到岛另一头 —— 挡墙让射线
           先撞上高度 1.0 的高墙就地停下，不会折回。
      实物：`gen_pbr_butchery.py` 的 `big_face_mask()`（规格里标 `big_faces=True`）/
      `FURNITURE_KEY` / `furniture_spec()`。没有任何大面的图集（标本制作台主图、
      晾皮架以外的 `taxidermy_table_front/side/top`）掩码为空 → 自然整张压平，
      所以不需要单独的「薄家具」名单（第 21 轮的 `THIN_FURNITURE_KEY` 已取消）。
     * **A 高度不是越深越好，看「位移 ÷ UV 岛宽」（第 24 轮定案，最实用的一条判据）**：
       给定视线，位移 ≈ 常数 × `quadSize` × 高度落差，`quadSize = 1/岛宽`（16 格空间）。
       同一张图集里 4×4 的台面位移 0.2~0.4 岛宽就撕、0.05~0.1 就干净 —— **要不要给真实
       高度、给多深，取决于这个比值，不取决于「是不是家具」**。实操分档：「铺地的完整
       方块面」（UV 岛 16 格 == 整张图）给真实分档；「一块面用一个放大 UV 岛的图集 / 模型」
       （岛 3~8 格）用 255 附近的窄带或整张压平；「平面件 / 精灵图 / 皮肤」整张 A=255。
       **法线与视差解耦**：不给视差也能有强法线（下一条）。
     * **`_n` 法线：`pixel=True` 的整块填充给平面件用（第 24 轮补强）**：屠夫家具原先
       `bump=False` 只有 1 像素窄边，`|n|` 均值 1.2~7.9，作者反馈「没法线」；实体皮肤
       更明显 —— 窄法线在光滑的劫掠兽毛皮上 `|n|` 均值只有 **1.1**，几乎不可见。改用
       `gen_pbr.block_normals()` 的**整块填充法线**（每个 texel 按邻居亮度差给一个朝向、
       再按 `cell` 放大）后，家具 9.2~22.3、劫掠兽 17.7~20，和参考包「尝鲜·立体模型」
       实测的 20.9 同档。所以：**小 UV 岛图集、模型图集、实体皮肤一律走
       `flat=True, flat_ao=True, pixel=True`（A=255 + 整块法线 + AO）**；
       窄法线只在铺地大图（`bump=True` + 三圈宽倒角）里用。
     * **易错点：跨函数用「文件名」当字典键，先去掉扩展名**（第 24 轮踩到）：傀儡装配的
       `big_face_mask()` 内部缓存键是**不带 `.png`** 的 STEM（`table_top`），调用方传的却是
       `os.path.basename(path)`（`table_top.png`），`.get()` 永远 `None`、掩码全空、高度 A
       一路 255，光影直接**跳过视差**（作者看到的就是「工作台没有视差」）。修法一行
       `os.path.splitext(tex_name)[0]`。**自查动作**：掩码类函数返回 `None` / 全空时，
       不要当成「这张图本来就没大面」，先核对键和后缀。

     > 家具规格见 `gen_pbr_butchery._furn()`（`pixel=True` 整块法线 + `soft=True` 的
     > 244~253 窄带）；傀儡工作台见 `gen_pbr_golems.process_block()` 同样两条。
    * **光影的 POM 是「岛内」步进，不会采到图集别处**（第 22 轮查清楚，很重要）：
      Helian 的 `calculateParallax` 把局部坐标经 `clampCoordRange()` = `coordRange.xy +
      fract(coord) * coordRange.zw` 折回**这一块面自己的 UV 岛**，所以第 21 轮用
      `review_pixel.render` 把整张图集当一个面渲染、看到「采到图集别处」的结论是错的：
      那个渲染既把步长 `quadSize=1/岛宽` 放大了好几倍、又用错了采样范围。要看家具的
      视差对不对，得用 `tools/review_furniture_pom.py`（按真实模型 UV，带岛内折回）。
    * **细面的波浪根因**：位移步长 = (视线切向/法向) / 步数 × 0.2 × 视差深度 × `quadSize`，
      `quadSize = 1 / UV岛宽`。所以 **UV 岛越窄、位移相对岛越大**（0.2 宽的细杆
      `quadSize=80`，一步就绕岛好几圈 → 采到岛内别处、糊成条纹）；大台面 `quadSize≈4`，
      位移只有约 1 个原始像素，跟零雾的原版方块同一量级。判断该不该给视差，量 UV 岛宽，
      别只看模型元件数。
    * **光影跳过视差的门槛**（调高度时要记得）：Photon `depth < 1/255`（A=255）、
      Helian `startHeight < 1.0`、IterationRP `h < 1.0`；开「视差平滑」时又会把台阶插值成
      连续斜坡。所以真实参与视差的面别整片写 255。
    * **波浪的本质是位移场突变**：Photon v1.3b（`include/surface/parallax.glsl`）、IterationRP
      （`Lib/IndividualFunctions/Parallax.glsl`）、Helian MMCO（`libs/Parallax.glsl`）都是沿视线
      在高度场里步进、撞到高度面才取底色。**一片像素位移为 0、紧挨着的像素位移很深**，
      掠射角下就把纹理撕成条纹 —— 那才是波浪。这一条在分辨率对上之后才真正起作用。
    * **已废弃**：第 14 轮的「基准面 + 浅坑」浮雕（`relief=True`）和第 16 轮的「像素画风
      平面浮雕」（`pixel=True`，整张压平）—— 两者都是**分辨率没对上**时、用失真的自查渲染
      调出来的，只是把波浪换了个形状。第 8 轮的「平台正好 255 + 沟缝下沉」更糟
      （光影会跳过视差、和旁边深坑形成位移突变），也别再用。相关函数与旧诊断脚本保留备查。
    * **自查必须渲染，而且要用玩家实际在用的光影**：`tools/shader_pom.py` 逐行搬了
      Photon / IterationRP / Helian（含「平滑视差」分支）和 Complementary 的 POM；
      `tools/review_parallax.py` 把我们的方块和零雾的原版方块放在**同一组光影参数**下渲染
      对比，产物 `review-millenaire/parallax_vs_zerofog.png`。判据是两边位移场形态一致、
      没有斜向条纹。`tools/review_relief.py` / `review_wave.py` 是旧诊断工具，保留备查。
    * 分类实现见 `tools/gen_pbr_millenaire.py` 的 `classify()`；`flat_model_stems()` 仍保留，
      只用来在报告里区分「贴给非完整立方体模型」和「贴给完整立方体」两类，不再决定是否做视差。


## 模型 / 实体贴图（UV 图集）

模组的实体皮肤（村民 64×32、怪物 64×64、盔甲层 64×32）和模型图集不是铺在方块表面的
底色，做法和物品精灵图同一类，但有几条实测差异（数据来自参考包新一轮的「立体模型·床」，
逐张量过）：

1. **放大 8 倍**：64×64 → 512×512，64×32 → 512×256，法线和 AO 才平滑。
   大图（128×128、256×128）按比例缩到最长边 512 就够，不必硬做 1024²/2048²（又慢又占体积）。
   **底色同样按这个倍数放大写进包**（同「整包做法」第 13 条）：实体 `_n` 虽然 A=255 不做视差，
   但保持底色与 `_n` 同分辨率，能避免任何按底色尺寸去采样法线 / 高度的光影读错位置。
2. **平面高度 + 保留 AO**：`_n` 的 A 整张 255（不做视差），B 照底色明暗算 HBAO，
   比物品更轻（参考包最暗到 152，82.7% 的像素是 255）。
3. **法线不要压弱、要宽**：参考包实体 `_n` 的 R/G 偏离 127 最大到 ±105，约一半像素不是平的。
   只用方块那套「边缘 1 像素窄法线」会明显偏软（实测覆盖率只有百分之几）。
   做法是窄法线之外再给凸起结构加三圈倒角（±29 / ±19 / ±9），
   面板会像被压出来的浮雕，覆盖率接近参考包。
   **第 24 轮实测补充**：对**平滑皮肤**（劫掠兽毛皮这类几乎无硬边的底图），窄法线 + 倒角
   仍然几乎不可见 —— `|n|` 均值只有 **1.1**（因为倒角要有「凸起/背景」之分，平滑图里
   `bump` 覆盖了大半张，倒角加不上去）。这种情况直接改用 `pixel=True` 的
   `block_normals()` 整块填充法线：劫掠兽 1.1 → **17.7**、刽子手 14.6、盔甲层 13.9，
   和参考包 20.9 同档。**选法：有硬边的方块 / 厚模型用窄法线 + 倒角；平滑皮肤、
   模型图集、小 UV 岛图集用整块填充。**
4. **不跨 UV 边界环绕**：把高度图向四周复制一圈再算窄法线，否则贴图接缝处会冒出
   一圈假凸起。透明像素洗干净：`_n` 写 127/127/255/255，`_s` 写 R=G=B=0、A=255。
5. **`_s`**：R 按材质家族取（皮肤 / 布 / 羊毛 / 皮革 / 毛皮 / 骨 / 木 / 植物 / 宝石 / 金属…）；
   G 按材质表，盔甲里再逐像素把铁（230）、金（231）单独取 `regions`；
   B 给孔隙度：布、羊毛、皮革 8–20，其余 0（参考包 v5003 的实体 B 全是 0，
   新一轮给布料加了孔隙度，我们跟新的）；A 一律 255，眼睛/发光件才给一点点，值减半。
6. **一层模型方块**：门、活板门、铁轨、梯子、栏杆、锁链、作物这类「没有实体面」的
   贴图，`_n` 的 A 整张 255；铁砧、木桶、讲台、织布机这类真有开口的，开口内部
   降到 87 上下（「真实凹洞」一档），其余表面仍在 255 附近。前一类写平 A 的同时
   **B（AO）要保留**（参考包这类贴图 AO 均值 226–253、最暗到 67；只有 `flat_ao` 关掉才会是 255）；
   判据同「整包做法」第 13 条：扫描模型文件，看这张贴图有没有被实心立方体用到。
   **第 19 轮起这条规则自动化了**：`tools/model_scan.py` 直接算出「面数多、UV 细小」
   的薄模型贴图集合，`+thin_flat` 命中就整张 A=255、保留 AO，不再靠肉眼点名。
7. **材质有参考包对应方块时，照那张方块的 `_s` 取值**（第 23 轮，傀儡装配）：
   铜 `R150~206 / G255 / B0`、金 `R209~225 / G255 / B0`、铁 `R163~180 / G255 / B0`、
   下界合金 `R126~141 / G232 / B0`、幽匿 `R65~80 / G0 / B191(SSS)`。彩色金属一律
   `G=255`（底色当 F0），金属才有自己的颜色；做法是量参考包方块 `_s` 的中位数，
   不是照 LabPBR 预设表。没有对应方块的兼容材质按字面发挥（金属 `G=255`，
   木头/铁木 `G=232, B=8`，纸/壳类非金属 + 孔隙度）。
   **参考包里已有同款实体贴图时可以直接搬**：傀儡装配的 `metal_golem` 与零雾的
   `entity/iron_golem` 是同一套 128×128 UV，就把底图 + `_n` + `_s`（1024×1024）整体
   搬进模组命名空间，不做二次生成 —— 前提是逐像素比对确认骨架对齐。
   实物见 `tools/gen_pbr_golems.py`（`copy_iron_golem()`、`GOLEM_MAT`）。

配套脚本：`tools/gen_pbr_entities.py`；**平面件 / 皮肤 / 模型图集**另见
`tools/gen_pbr_savage.py`（第 24 轮，野蛮与蹂躏：按目录 + 文件名关键词分四类，
铺地方块真实视差 / 模型图集与皮肤走 `flat + pixel` / 物品粒子走 `flat + AO`）。

## LabPBR 1.3 速查

| 贴图 | 通道 | 含义 | 编码 |
|---|---|---|---|
| `_n` | R | 法线 X | 127 为平，大于 127 朝右 |
| `_n` | G | 法线 Y | DirectX：大于 127 朝下 |
| `_n` | B | AO | 255 无遮蔽，0 全遮蔽 |
| `_n` | A | 高度 | 255 最高，0 为 25% 方块深度；最小用 1 |
| `_s` | R | 感知光滑度 | 粗糙度 = (1 − 光滑度)² |
| `_s` | G | F0 或金属 | 0–229 为线性 F0；230–237 预设金属；255 以底色为 F0 的金属 |
| `_s` | B | 孔隙度或 SSS | 0–64 孔隙度；65–255 次表面散射 |
| `_s` | A | 自发光 | 1–254 发光强度；255 表示不发光 |

预设金属：230 铁，231 金，232 铝，233 铬，234 铜，235 铅，236 铂，237 银。238–254 未定义，不要用。

规范原文：https://shaderlabs.org/wiki/LabPBR_Material_Standard

## `_n` 的生成规则

### A 通道：高度

1. **前提（最重要，第 17 轮定案）：底色贴图必须和 `_n`/`_s` 同分辨率、一起放进包。**
   光影是拿**底色贴图**的尺寸去索引法线图里的高度的（Helian 的 `bilinearHeightSample`
   用 `albedoTexSize` 算 `texelFetch(normals, …)` 的坐标）。只放大 `_n`/`_s`、底色还是
   16×16 时，光影只读到高度图的左上角一小块、再拉伸铺满整个方块 —— 掠射角下就是大片
   平滑的波浪，跟高度深浅无关，怎么调高度都还在。参考包「零雾构想 v5003」是
   **1282 底色 + 1264 `_n`**（方块都 128×128），两边同分辨率，所以视差正常。
   配套：`gen_pbr.py` 的 `WRITE_BASE`。
2. **高度用底色亮度分档**（零雾的实际做法）：`height_from_colour()`，亮度 → `[lower, 255]`，
   按 `step`（实测多为 4 或 8）量化。亮处高、暗处低，一张图 6–11 档、密布小落差，
   处处参与视差。下限 `lower` 查下面的分档表。实测我们与零雾同档（`stone_bricks` 207–255 7 档、
   `cobblestone` 199–255 8 档、`gravel`/`dirt` 199–255）。
3. 旧做法（第 14 轮）「基准面 + 浅坑 + 只有 3 个高度值」的浮雕**已停用**：那是当时没发现
   分辨率问题时、用失真的自查渲染调出来的，只是把波浪换了个形状。旧做法（第 8 轮）
   「平台正好 255 + 沟缝下沉」更糟（光影会跳过视差），也别再用。
4. 换算：深度（原始像素）= (255 − A) / 63.75。191 正好是 1 个像素深。
5. 有结构的地方按形状修正，不按亮度：砖缝颜色浅但最低；矿物颗粒颜色深但要抬高；原木顶面的年轮按同心环分层；功能方块按面板和开口分层。用 `height_overrides` 实现。
6. **植物、树叶、玻璃、镂空石雕、雕像、地图标记、流体**这类精灵 / 镂空整张 A=255（只补 AO）。
7. **书架要按「书插在格子里」分层，不能直接按亮度抬白书页（第 19 轮）**：书架侧面的
   底色里，书页是整张最亮的（接近纯白），旧的「亮度 → 高度」会把它抬到最高，看起来
   像一块白板从柜面戳出来（作者原话「白色书页色凸出来了」）。正确的层次从外到内是：
   木框 + 中间隔板（第 8 行）**最前** → 书脊 → 书页 → 格子暗部 **最深**。固定四档
   即可：框 231、书脊 215、白书页（格子内、L≥185 且低饱和）191、格内暗部（L≤48）175。
   判据只看「是不是格子内部、是不是近白、是不是暗部」，不依赖木头的明暗。实现见
   `gen_pbr_spellbooks.py` 的 `bookshelf_height()`（智慧木书架 9 张）。
8. **图集模型（家具 / 工作台）：小 UV 岛是视差和波浪不可调和的根因，想给视差就必须「去图集化」（第 25 轮定案）。**
   光影的 POM 只在**这一面自己的 UV 岛**里步进（Helian `calculateParallax` 的
   `clampCoordRange()`），步长 ∝ `quadSize = 1 / 岛宽`。图集模型里一块 16 格的大面常常
   只用到 64×64 图集的 4×4 格（= 整图的 1/4），`quadSize = 4`：同样的高度差，位移是
   原版方块（岛 = 整张、`quadSize = 1`）的 **4 倍**。于是
   「给真实高度（A 下到 207）→ 位移 0.3~0.6 岛宽 → 掠射角撕成条纹」「高度压到 244~253
   → 位移只剩 0.06~0.16 → 作者说没视差」是一对**物理上不能同时满足**的要求
   （第 19、21、22、23、24 轮反复踩）。正确解法是 `tools/deatlas.py`：
   - 把每个面用到的 UV 矩形**单独裁成一张贴图**，模型里把这个面的 `uv` 写成整张
     （`0..16`，按原来的翻转方向：`u0<u1` 则新 uv 的 u 是 `0→16`，否则 `16→0`），
     岛 = 整张贴图、`quadSize = 1`；裁出来就是图集里的原像素，整数倍最近邻放大，
     **外观一个像素都不变**。
   - 覆写 `models/block/*.json`（把 parent 链摊平；只改命中面的 `uv`/`texture`，
     几何 / `display` / `render_type` / `ambientocclusion` 一个字段不动）。
     要覆写 **block model** 而不是 `models/custom/*`，否则多个用不同贴图的 block model
     共用一个 custom model 会串图。
   - 只拆 `min(岛宽, 岛高) >= 1 格` 的面；更细的框 / 栅条留在图集里（它们 `quadSize`
     更大，绝不能给高度）。
   - 拆出来的贴图 `_n` A 给**真实高度**（木/石 207~255、柜类 215~255，和零雾同档），
     位移 r3 ≈ 0.10、r6 ≈ 0.20 岛宽；三个保险：高度用轻模糊亮度（低频）、
     `cutout` 的透明像素写 A=255（洞是洞不是坑）、四周留 1 原始像素 255 挡墙
     （裁出来的块不可平铺，防光影 `fract()` 折回出现重复花纹）。
   - 图集那张 `_n` 的高度整张压平 A=255（只剩细面用它），但**法线照旧**整块填充。
   - `_s` 不动：拆分贴图的 `_s` 直接从原 `_s` 同区域裁。
   判据：位移 = 0 或压到 0.05 以下 = 没视差；超过 0.25 岛宽 = 波浪。先离线渲染
   `tools/review_deatlas.py` 确认再交付。

高度（也就是视差）基本来源于底色，但要根据贴图的结构做微调。这种微调需要从宏观上理解这张底色画的是什么材质、什么结构，没有固定公式，要在和作者的反复训练中养成。所以：亮度映射出来的高度只是草稿，结构修正的方案要用 16×16 的数值网格展示给作者确认；作者的修改和理由记进 `training_log.md`。

高度下限分档（参考包统计，624 张）：

| 档位 | A 下限 | 代表方块 |
|---|---|---|
| 无高度 | 255 | 植物、树叶、玻璃、镂空石雕、雕像、地图标记、铁轨、栏杆、混凝土、带釉陶瓦、潜影盒、物品、实体 |
| 基准面（浮雕顶面，占多数） | 255 − base | 所有走浮雕的方块：默认 231，粗糙散粒材质 223。**不要写 255** —— 光影会跳过视差，和旁边的坑形成位移突变 |
| 浅坑（浮雕第 1 档） | 255 − base − step | 略暗于局部背景的纹路：木纹、细砖缝 |
| 深坑（浮雕第 2 档） | 255 − base − 2·step | 明显低于局部背景的结构：砖缝、木板缝、开口 |
| 近似平坦 | 240–251 | 骨块侧面 243，石英块底面 247 |
| 光滑 | 224–239 | 冰、雪、砂岩顶面 239；磨制安山岩/闪长岩/花岗岩 235；草方块顶面、末地石、蘑菇柄 231；去皮原木、黑曜石、幽匿块、西瓜、南瓜侧面 227 |
| 轻度起伏 | 208–223 | 陶瓦、泥巴、青金石块、黏液块 223；羊毛 221；沙子、平滑玄武岩 219；绿宝石块、滴水石、蜂蜜块 215；石英、磨制黑石、深板岩瓦 211 |
| 标准起伏 | 192–207 | 石头、凝灰岩、方解石、所有木板、各种砖、砂岩侧面、苔藓块、灵魂沙、钻石矿、铁矿 207；切制铜、下界合金块 203；圆石、深板岩、黑石、安山岩、闪长岩、花岗岩、多数矿石、泥土、耕地、黏土、草方块侧面、金块、钻石块 199；铜块、凝灰岩砖 195 |
| 深起伏 | 160–191 | 原木树皮、基岩、沙砾、远古残骸、岩浆块、粗铁块 191；铁块、粗铜块、荧石、工作台、命令方块 183；下界岩、下界矿石、缠根泥土、菌岩侧面 175；原木顶面、砂土 167 |
| 真实凹洞 | 63–159 | 只有开口内部降到这么低，其余表面仍在 190 以上：书架、熔炉/高炉/烟熏炉正面 71；打开的木桶、雕刻南瓜 63；发射器、投掷器 107；织布机、讲台正面 87–99；蜂巢、蜂箱正面 127–139 |

石头、深板岩、下界岩的上限是 231 而不是 255。

定档的依据，按影响从大到小：

1. 是不是完整的不透明方块面。不是就没有高度。
2. 有没有真实的开口或凹洞。有就让开口内部单独取 1.5–3 个像素深。
3. 加工程度：越精细下限越高。圆石 199 → 石头 207 → 磨制安山岩 235。
4. 颗粒粗细：越粗越深。砂土 167 → 泥土 199 → 沙子 219 → 雪 239。
5. 有没有边框或缝隙：木板和砖的缝在 207，带厚边框的铁块在 183。
6. 同一方块的不同面可以不同档：原木顶面 167、侧面 191；砂岩侧面 207、顶面 239。

同一类颜色变体（16 色陶瓦、羊毛）用相同的下限。氧化阶段不改变下限。

### R、G 通道：法线

平面值是 127（不是 128）。方向是 DirectX：表面向右下降时 R 大于 127，向下下降时 G 大于 127。

**窄法线（主体）**

- 法线基本都产生在底色变化的边缘上：相邻两个块颜色不同、高度不同，边界上就有一条法线。
- 宽度 1px，并且**全部落在较高那个块的一侧**。块的内部是平的。
- 强度由高度差决定（脚本里的 `EDGE_TABLE`）：

| 高度差 | 4 | 8 | 12 | 16 | 24 | 32 | 48 | 64 |
|---|---|---|---|---|---|---|---|---|
| 偏移量 | 5 | 9 | 13 | 18 | 54 | 58 | 71 | 77 |

- 高度差到 20 以上时强度跳到 54 以上，这是参考包的实测行为。
- **法线必须清晰可见。** 底色变化小的贴图（例如去皮原木）按高度差算出来会太弱，这时适当提高强度，不完全依赖底色。用 `min_edge`（强度下限）或 `edge_gain`（倍率）。

**宽法线（补充）**

- 以块为单位：凸起结构边缘那一圈块整块向外倾斜，让凸起看起来更圆润。
- 档位：±9、±19、±29。
- 两类方块都用：
  - 有规律性结构的：木板（每块木板边缘 ±9）、砖块（每块砖边缘 ±19）。
  - 自然方块：圆石、泥土、沙砾、下界岩等。它们没有规律结构，但表面有大块凸起，凸起的边缘同样做宽法线（参考包多为 ±19）。
- 整个方块的倒角：磨制石材最外一圈 ±19；铁块最外圈 ±9、第二圈 ±19；潜影盒由外到内 ±29、±19、±9；玻璃最外圈 ±2。这种情况用 `wide_wrap=False`。
- 不是所有材质都用：石头只有窄法线。

**凸起范围怎么定**

凸起范围是审美判断，不是一条规则能算出来的。依据是：底色亮度、材质本身的特征、人会把这些低像素图案看成什么形状。目标是一个美观的凸起范围。

做法：

1. 看底色贴图，结合材质提出 16×16 的凸起范围。
2. 用 16 行、每行 16 个字符的网格（`#` 凸起，`.` 非凸起）展示给作者，并写出理由。
3. 作者确认或修改后再生成。

高度阈值只能当起点。参考包里"最低一两档高度当凹坑、其余为凸起"对泥土和砂土吻合 97%–98%，圆石 91%，沙砾只有 73%。材质越复杂，越需要人工判断。

作者的判断标准还没有经过逐张校准。遇到拿不准的贴图，多给一两个候选方案让作者选，并把作者的修改理由记下来，建议更新到这份 skill 里。

**圆柱渐变**

- 原木侧面为了做出圆柱体效果，在 R 通道水平方向叠加渐变。
- 渐变以 1px 为单位，近乎连续，形状是椭圆函数，不按块分级。
- 脚本默认参数是对参考包去皮橡木原木的拟合：两端约 ±84。G 方向没有渐变。

### B 通道：AO

- 就是在高度图上做 HBAO，没有其他处理。
- 表现：较高的块内部是 255；遮蔽出现在较低的块里，紧贴较高邻块处最暗，逐像素平滑过渡到 255。整体很轻。
- 脚本里的 HBAO 是自己实现的近似，参数对着参考包拟合过（平均差约 2/255），不等于 SD 的节点。

### 没有高度的贴图

植物、玻璃、镂空贴图等用 `flat=True`：A 为 255，不做 AO，但窄法线照常按底色变化生成。

## `_s` 的生成规则

原则：各通道都依赖底色，根据材质信息把底色亮度控制到某个范围内。G、B 按材质取固定值。

### R 通道：光滑度

- 把底色亮度线性映射到该材质的 R 范围。
- **不叠加 HBAO。** 参考包的 R 叠加了 HBAO，作者认为视觉影响不大，选择不做。
- 有结构修正的贴图单独处理。例：红砖的灰缝亮但粗糙，要反向（`r_invert`）或把灰缝作为单独的区域。

各材质的 R 范围（参考包实测；下限含参考包的 HBAO 压暗，实际可取高 0–10）：

| 材质 | R 范围 | 材质 | R 范围 |
|---|---|---|---|
| 基岩 | 15–36 | 木板 | 112–149 |
| 沙砾 | 22–48 | 下界合金块 | 121–141 |
| 深板岩 | 29–103 | 紫珀块 | 123–159 |
| 泥土 | 32–127 | 骨块侧面 | 126–136 |
| 草方块顶面 | 30–100 | 去皮原木 | 137–160 |
| 下界岩 | 35–124 | 紫水晶块 | 140–168 |
| 石头 | 45–103 | 铜块 | 137–208 |
| 圆石 | 46–160 | 黏液块、蜂蜜块 | 152–177 |
| 沙子 | 45–177 | 铁块 | 156–180 |
| 凝灰岩 | 47–120 | 绿宝石块 | 164–191 |
| 原木树皮 | 49–90 | 石英块 | 167–223 |
| 安山岩 | 53–124 | 冰 | 174–184 |
| 苔藓块 | 54–88 | 雪 | 176–188 |
| 砂岩 | 62–96 | 磨制安山岩 | 178–240 |
| 石砖 | 62–128 | 黑曜石 | 196–219 |
| 平滑石头 | 62–160 | 金块 | 202–226 |
| 原木顶面 | 70–132 | 浮冰 | 205–216 |
| 末地石 | 71–96 | 钻石块 | 207–232 |
| 羊毛 | 85–114 | 带釉陶瓦 | 215–248 |
| 树叶 | 85–127 | 玻璃、染色玻璃 | 235–249 |
| 煤炭块 | 89–127 | 蓝冰 | 237–248 |
| 混凝土 | 92（整张同值） | 红砖 | 23–97 |
| 陶瓦 | 109–130 | | |

规律：加工程度越高、材料越致密，R 越高，范围越窄。表里没有的材质，按这个规律参照相近材质取值，并告诉作者取的是什么。

### G 通道：F0 或金属

**作者的决定：按 LabPBR 规范定义的值来填，不沿用参考包的值。** 参考包里非金属多为 0，氧化铜用了未定义的 243、249，深色铁制品用了代表铝的 232，这些都不照搬。

| 材质 | G 值 | 说明 |
|---|---|---|
| 一般非金属（石头、木头、泥土、羊毛、陶瓦、植物等） | 10 | F0 约 4% |
| 冰、雪、水质的东西 | 5 | F0 约 2% |
| 玻璃、石英、紫水晶 | 10–12 | F0 约 4%–5% |
| 绿宝石 | 18 | F0 约 7% |
| 钻石 | 44 | F0 约 17% |
| 铁及铁制品（铁块、铁门、铁砧、漏斗、炼药锅、锁链、铁轨） | 230 | 预设金属：铁 |
| 金 | 231 | 预设金属：金 |
| 未氧化的铜 | 234 | 预设金属：铜 |
| 其他金属、合金、氧化的铜、下界合金 | 255 | 以底色作为 F0 |

这张表里非金属和宝石的数值是按物理 F0 换算出来的建议值，作者只确认了"按规范定义"这个方向，具体数值第一次使用时请作者过目。

**例外（第 22 轮作者点名）：铁锅类照零雾构想的「炼药锅」那一组值来。** 作者要求「血栅、
金属屠夫台、女巫坩埚、炼金锅的材质都按照零雾构想的炼药锅来」，所以这四样不按上面的
规范值（230 铁），而是照参考包实测：`_s` R = 116~141（均值 135~139，随底色亮度略升）、
**G = 232**（预设金属铝）、B = 0、A = 255，`_n` 高度基本整张 255（锅身是平的，法线 / AO
保留）。这是作者明确指定的，改这些材质时照做，别再套 230。

### B 通道：孔隙度或 SSS

按材质取固定值（参考包实测，直接沿用）。同一个像素只能二选一。

孔隙度（越松散、越吸水越高）：

| B 值 | 材质 |
|---|---|
| 0 | 金属、石头、深板岩、基岩、黑石、方解石、混凝土、磨制石材 |
| 4–8 | 木板、木门、活板门、去皮原木、原木顶面、切制砂岩、砂岩顶面 |
| 10–12 | 红砖、灰化土顶面、草方块顶面 |
| 14 | 圆石、安山岩、闪长岩、花岗岩、凝灰岩、玄武岩、下界岩 |
| 16–17 | 沙砾、泥砖、泥坯、砂岩侧面 |
| 20 | 羊毛 |
| 22–25 | 原木树皮、泥土、砂土、耕地、草方块侧面、干草块 |
| 28 | 泥巴、菌丝顶面 |
| 30 | 沙子、红沙、灵魂沙、灵魂土、混凝土粉末 |

次表面散射（越薄、越透光越高；取值落在间隔 32 的台阶上）：

| B 值 | 材质 |
|---|---|
| 95 | 陶瓦、黏土、蜡烛、蛋糕、荧石、红石灯 |
| 127 | 带釉陶瓦、珊瑚块、滴水石、紫珀块 |
| 159 | 蘑菇块、仙人掌、南瓜、西瓜、骨块、石英、苔藓块、下界疣块、海绵、钻石块、绿宝石块、青金石块、红石块 |
| 191 | 蓝冰、雪、细雪、树脂块 |
| 223 | 树叶、花、草、树苗、作物、藤蔓、紫水晶、蜂蜜块、黏液块、浮冰 |
| 255 | 冰、玻璃类、霜冰 |

### A 通道：自发光

- **不发光的像素一律 255，绝不用 0。** 0 在一些光影下会导致错误。不发光的贴图也是整张 255。
- `_s` 一律存成带 A 通道的 RGBA，不要存成没有 A 通道的 RGB。
- 只有发光的块写入 1–254 的值：整块同一个值，或者按底色亮度映射到一个范围。
- 参考强度：光源本体高，装饰性微光低。

| 发光部位 | A 值 |
|---|---|
| 矿石里的矿物颗粒 | 47–95 |
| 结构方块 | 64 |
| 命令方块、哭泣的黑曜石 | 96–127 |
| 海晶灯 | 96–107 |
| 火把火焰 | 127 |
| 南瓜灯面部 | 140–200 |
| 荧石、蛙明灯 | 167–223 |
| 刷怪笼 | 191 |
| 末地烛 | 223 |

### 混合材质的贴图

同一张贴图里个别块的材质和主体不同时，这些块的 R、G（必要时 B）单独取值，用 `regions` 实现。例：

- 木门、活板门、木桶：木头是主体，金属件单独取铁的值。
- 书架、工作台：木头是主体，金属件单独取值。
- 矿石：石头是主体，矿物颗粒取对应矿物块的 R 范围和 G 值，通常还带自发光。

哪些块属于另一种材质，同样先给出 16×16 网格方案，请作者确认。

## 每张贴图要定的参数

| 参数 | 用途 | 怎么定 |
|---|---|---|
| `lower`、`upper`、`step` | **当前的高度规则**：底色亮度 → `[lower, 255]` 分档 | `lower` 查「A 通道：高度」的档位表；`step` 实测多为 4 或 8；`upper` 默认 255 |
| `relief` 及 `relief_*` | 第 14 轮的「基准面 + 浅坑」浮雕，**已废弃** | 不要再用：它是分辨率没对上时调出来的，只是把波浪换了个形状。旧脚本保留仅为兼容 |
| `flat` | 无高度的贴图（精灵 / 镂空 / 流体 / 物品 / 实体） | 查「A 通道：高度」第 6 条的例外清单 |
| `flat_ao` | 平面高度但保留 AO | 物品、实体、盔甲层精灵图；薄模型压平（`+thin_flat`）时也开着 |
| `model_flatten_stems` | 自动找出「面数多、UV 细小」的薄模型贴图 | 扫 `models/block/*.json`（`tools/model_scan.py`），命中就整张 A=255 且保留 AO；报告标 `+thin_flat` |
| `big_face_mask` | 图集里「大面」的内圈掩码（第 22 轮） | 扫 `models/block/*.json`，UV 窄边 ≥ 3.0 的面标成内圈（外留 2 原始像素当挡墙）；非大面 texel 的 A 写 255。见「模型图集：大面给真实视差」 |
| `flat_band`、`flat_blur`、`flat_smooth` | 旧式「浅视差」参数，**已废弃** | 第 16 轮的整张压平 / 浅视差路线，别再用 |
| `transparent_flat` | 透明像素写成 127/127/255/255 | 物品、实体等带透明背景的贴图 |
| `height_overrides` | 结构修正 | 看图判断，需确认 |
| `bump`、`wide_levels`、`wide_wrap` | 宽法线 | 完整立方体面照常用（给凸起结构加软倒角）；只有确定要「整张压平」的面才关 |
| `cylinder` | 圆柱渐变 | 原木侧面 |
| `min_edge`、`edge_gain` | 提高窄法线强度 | 底色变化小时使用，看灰度图调整 |
| `r_range`、`r_invert` | 光滑度范围 | 查 R 范围表 |
| `g`、`b` | F0/金属、孔隙度/SSS | 查表 |
| `regions` | 混合材质 | 看图判断，需确认 |
| `emission` | 自发光 | 看图判断，需确认 |
| `clear_alpha` | `_s` 的透明像素 R/G/B 清零 | 物品、实体等带透明背景的贴图 |

## 用法示例

```python
import numpy as np
import labpbr_gen as lg

tex = lg.load_texels('block/oak_planks.png')          # 16x16 或 128x128 都可以

# 宽法线的凸起范围：先按高度阈值起个草稿，展示给作者确认后再用
H0 = lg.height_from_colour(tex, lower=207)
bump = H0 > (H0.min() + H0.max()) / 2

n, H = lg.build_n(tex, lower=207, step=4, bump=bump, wide_levels=(9,))
s = lg.build_s(tex, r_range=(112, 149), g=10, b=8)

print(lg.check_n(n), lg.check_s(s))                    # 空列表表示通过
lg.save_with_channels(n, 'out/oak_planks_n.png', 'out/channels')
lg.save_with_channels(s, 'out/oak_planks_s.png', 'out/channels')

# 原木侧面：圆柱渐变，并提高窄法线强度
n, H = lg.build_n(lg.load_texels('block/stripped_oak_log.png'), lower=227, cylinder=True, min_edge=9)

# 整个方块的倒角
n, H = lg.build_n(tex, lower=235, bump=np.ones((16, 16), bool), wide_levels=(19,), wide_wrap=False)

# 矿石：矿物颗粒是另一种材质，并且发光
grains = lg.mask_from_rows(['................'] * 16)       # 换成确认过的网格
s = lg.build_s(tex, r_range=(31, 103), g=10, b=0,
               regions=[dict(mask=grains, r_range=(207, 232), g=44)],
               emission=[dict(mask=grains, range=(47, 95))])

# 物品 / 实体 / 盔甲层精灵图：平面高度、保留 AO、透明背景洗干净
tex = lg.load_texels('item/apple.png')
n, H = lg.build_n(tex, lower=200, flat=True, flat_ao=True, transparent_flat=True)
s = lg.build_s(tex, r_range=(20, 180), g=0, b=0, clear_alpha=True)
```

把凸起范围展示给作者时，可以这样打印网格：

```python
print('\n'.join(''.join('#' if v else '.' for v in row) for row in bump))
```

## 还没有定下来的事

- 凸起范围（宽法线）和高度的结构微调，判断标准没有逐张校准过，只有原则。这是训练的主要内容。
- 窄法线强度下限 `min_edge` 没有固定值。物品、实体、盔甲层精灵图的法线强度也没定；参考包实测偏移到约 ±57（围绕 127 的 76–184），可以先用 `min_edge` / `edge_gain` 调，再请作者看灰度图。
- G 通道的非金属和宝石数值是建议值，待作者过目。
- 参考包里较低一侧紧贴边界的像素有 2–5 的小偏移。作者的规则是法线全部在较高一侧，脚本没有加这个偏移。
- 盔甲纹饰 `_s` 的 B/A 随明暗变化（B 88–144、A 123–174）是做什么用的没有确认，先记在 `reference/pack-layout.md`，不照搬。
- 随机变体（`_05_random_*`）是逐像素手绘的，脚本没有自动生成变体的办法；要做只能一张张画，或者用同一素材轻微扰动后再人工检查。

## 脚本：labpbr_gen.py

**工作目录里的 `labpbr_gen.py` 始终是权威版本**（比下面这份多 `hbao_strength` 参数和法线合成长度限制等改动）。两者不一致时以文件为准；本文这份用于没有文件的场合。

```python
"""LabPBR 1.3 _n / _s generator for pixel-art Minecraft textures (16x16 source texels -> 128x128 output).

_n : R,G = normal (DirectX, flat = 127), B = AO, A = height
_s : R = smoothness, G = F0 / metal id, B = porosity / SSS, A = emission (255 = none)

Everything is computed on a 16x16 grid of source texels; each texel becomes an 8x8 block.
"""
import os
import numpy as np
from PIL import Image

CELL = 8          # output pixels per source texel
GRID = 16         # source texels per side
# height step (A units) across a texel boundary -> normal offset on the higher side (measured from the reference pack)
EDGE_TABLE = [(0, 0), (4, 5), (8, 9), (12, 13), (16, 18), (20, 54), (24, 54), (32, 58),
              (40, 62), (48, 71), (56, 73), (64, 77), (128, 100)]


# ---------- input ----------
def load_texels(path):
    """Read a base-colour texture (16x16, or NxN with N a multiple of 16) as a 16x16 RGBA float array.
    For upscaled textures the centre pixel of every cell is used."""
    a = np.asarray(Image.open(path).convert('RGBA')).astype(float)
    if a.shape[0] != a.shape[1] or a.shape[0] % GRID:
        raise ValueError(f'{path}: expected a square texture whose side is a multiple of 16, got {a.shape[:2]}')
    n = a.shape[0] // GRID
    c = (n - 1) // 2
    return a[c::n, c::n][:GRID, :GRID]


def luminance(tex):
    """sRGB values used directly, no linearisation."""
    return 0.299 * tex[..., 0] + 0.587 * tex[..., 1] + 0.114 * tex[..., 2]


def remap(L, lo, hi, invert=False, mask=None):
    """Linearly map luminance (min..max over `mask`) to lo..hi."""
    sel = L if mask is None else L[mask]
    a, b = sel.min(), sel.max()
    t = np.zeros_like(L) if b == a else (L - a) / (b - a)
    t = np.clip(1 - t if invert else t, 0, 1)
    return lo + t * (hi - lo)


def up(t):
    return np.kron(t, np.ones((CELL, CELL)))


# ---------- _n ----------
def height_from_colour(tex, lower, upper=255, step=4):
    """Brighter = higher. Quantised so that values sit on upper - k*step. Never below 1."""
    h = remap(luminance(tex), lower, upper)
    h = upper - np.round((upper - h) / step) * step
    return np.clip(h, max(lower, 1), upper)


def edge_strength(delta):
    xs = [a for a, _ in EDGE_TABLE]
    ys = [b for _, b in EDGE_TABLE]
    return float(np.round(np.interp(delta, xs, ys)))


def narrow_normals(H, min_edge=0, gain=1.0):
    """1px-wide normal on the HIGHER texel's side of every boundary where height differs.
    min_edge / gain raise the strength for low-contrast textures so the edges stay visible."""
    N = GRID * CELL
    R = np.zeros((N, N))
    G = np.zeros((N, N))

    def es(d):
        return max(edge_strength(d) * gain, min_edge)

    for ty in range(GRID):
        for tx in range(GRID):
            h = H[ty, tx]
            y0, x0 = ty * CELL, tx * CELL
            d = h - H[ty, (tx + 1) % GRID]
            if d > 0:
                R[y0:y0 + CELL, x0 + CELL - 1] += es(d)     # surface falls to the right -> R > 127
            d = h - H[ty, (tx - 1) % GRID]
            if d > 0:
                R[y0:y0 + CELL, x0] -= es(d)
            d = h - H[(ty + 1) % GRID, tx]
            if d > 0:
                G[y0 + CELL - 1, x0:x0 + CELL] += es(d)     # surface falls downward -> G > 127 (DirectX)
            d = h - H[(ty - 1) % GRID, tx]
            if d > 0:
                G[y0, x0:x0 + CELL] -= es(d)
    return R, G


def _shift(m, dy, dx, wrap):
    s = np.roll(np.roll(m, dy, 0), dx, 1)
    if not wrap:
        if dy == 1: s[0, :] = False
        if dy == -1: s[-1, :] = False
        if dx == 1: s[:, 0] = False
        if dx == -1: s[:, -1] = False
    return s


def wide_normals(bump, levels=(19,), wrap=True):
    """'Wide normals': whole 8x8 texels on the border of a raised structure tilt outward.
    bump   : 16x16 bool mask of the raised structure(s).
    levels : tilt per ring from the outside in, e.g. (19,) or (29, 19, 9). Usual values 9 / 19 / 29.
    wrap   : True if the texture tiles (structures continue across the border);
             False to treat the texture border as the structure's edge (e.g. a bevel round the whole block)."""
    bump = np.asarray(bump, bool)
    Rt = np.zeros((GRID, GRID))
    Gt = np.zeros((GRID, GRID))
    m = bump.copy()
    for lv in levels:
        left = m & ~_shift(m, 0, 1, wrap)
        right = m & ~_shift(m, 0, -1, wrap)
        top = m & ~_shift(m, 1, 0, wrap)
        bottom = m & ~_shift(m, -1, 0, wrap)
        Rt += lv * (right.astype(int) - left.astype(int))
        Gt += lv * (bottom.astype(int) - top.astype(int))
        m = m & ~(left | right | top | bottom)
    return up(Rt), up(Gt)


def cylinder_gradient(centre=63.7, half_width=67.6, bulge=29.9, axis='x'):
    """Per-pixel (continuous) elliptical gradient that makes a face read as a cylinder (log sides).
    axis='x' -> returns an R offset; axis='y' -> use the result as a G offset."""
    n = GRID * CELL
    x = np.arange(n)
    u = np.clip((x - centre) / half_width, -0.999, 0.999)
    s = bulge * u / (half_width * np.sqrt(1 - u * u))
    g = 127 * s / np.sqrt(1 + s * s)
    return np.tile(g, (n, 1)) if axis == 'x' else np.tile(g[:, None], (1, n))


def hbao(H, radius=12, strength=0.6, dirs=16, depth_px=0.03):
    """Horizon-based AO on the stepped height map. Parameters were fitted to the reference pack
    (mean abs error about 2/255); it is an approximation, not Substance Designer's HBAO node."""
    h = up(H) * depth_px
    occ = np.zeros_like(h)
    for k in range(dirs):
        ang = 2 * np.pi * k / dirs
        dx, dy = np.cos(ang), np.sin(ang)
        hor = np.zeros_like(h)
        for r in range(1, radius + 1):
            sx, sy = int(round(dx * r)), int(round(dy * r))
            if sx == 0 and sy == 0:
                continue
            sh = np.roll(np.roll(h, -sy, 0), -sx, 1)
            hor = np.maximum(hor, (sh - h) / np.hypot(sx, sy) * (1 - (r - 1) / radius))
        occ += hor / np.sqrt(1 + hor * hor)
    return np.clip(1 - strength * occ / dirs, 0, 1) * 255


def build_n(tex, lower, upper=255, step=4, height=None, height_overrides=None,
            bump=None, wide_levels=(19,), wide_wrap=True, cylinder=False,
            min_edge=0, edge_gain=1.0, ao=True, flat=False, flat_ao=False,
            transparent_flat=False):
    """Returns (RGBA uint8 image, 16x16 height array).
    height           : optional ready-made 16x16 height array (skips the luminance step).
    height_overrides : list of (16x16 bool mask, value) applied after the luminance step
                       (mortar lines, openings, raised ore grains ...).
    flat             : True for textures that carry no height (plants, glass, cut-outs): A = 255.
                       By default this also drops AO; pass flat_ao=True to keep it.
    flat_ao          : with flat=True, still compute AO from the (unwritten) height map.
                       The reference pack does this for item / entity / armour-layer sprites:
                       A is 255 everywhere (no parallax) while B keeps a light self-shadow.
    transparent_flat : force fully transparent texels to the reference pack's clean values
                       (R=G=127, B=255, A=255). Used for item sprites, whose background must
                       not pick up normals or a silhouette shadow."""
    H = np.array(height, float) if height is not None else height_from_colour(tex, lower, upper, step)
    for mask, value in (height_overrides or []):
        H[np.asarray(mask, bool)] = value
    H = np.clip(H, 1, 255)
    R, G = narrow_normals(H, min_edge, edge_gain)
    if bump is not None:
        wr, wg = wide_normals(bump, wide_levels, wide_wrap)
        R += wr
        G += wg
    if cylinder:
        R += cylinder_gradient()
    A = np.full((GRID * CELL,) * 2, 255.0) if flat else up(H)
    B = hbao(H) if (ao and (not flat or flat_ao)) else np.full((GRID * CELL,) * 2, 255.0)
    if transparent_flat:
        tr = up(tex[..., 3]) <= 0
        R[tr] = 0.0
        G[tr] = 0.0
        B[tr] = 255.0
        A[tr] = 255.0
    out = np.dstack([127 + R, 127 + G, B, A]).round().clip(0, 255).astype('uint8')
    out[..., 3] = np.maximum(out[..., 3], 1)          # height 0 breaks POM in some shaders
    return Image.fromarray(out, 'RGBA'), H


# ---------- _s ----------
def build_s(tex, r_range, g=10, b=0, r_invert=False, regions=None, emission=None,
            clear_alpha=False):
    """r_range  : (lo, hi) smoothness range for the material; luminance is mapped linearly into it. No HBAO overlay.
    g, b     : constant F0/metal id and porosity/SSS value for the main material.
    regions  : list of dicts for texels whose material differs (metal fittings, ore grains ...):
               {'mask': 16x16 bool, 'r_range': (lo, hi), 'g': int, 'b': int (optional), 'r_invert': bool (optional)}
    emission : list of dicts {'mask': 16x16 bool, 'value': int} or {'mask': ..., 'range': (lo, hi)}
               (range maps luminance inside the mask). 254 = strongest; 255 means "no emission".
    clear_alpha : force fully transparent texels to R=G=B=0, A=255 (the reference pack's item sprites).
               Note this only zeroes R/G/B; emission A stays 255, never 0."""
    L = luminance(tex)
    main = np.ones((GRID, GRID), bool)
    for reg in (regions or []):
        main &= ~np.asarray(reg['mask'], bool)
    if not main.any():
        main[:] = True
    R = remap(L, r_range[0], r_range[1], r_invert, main)
    Gc = np.full((GRID, GRID), float(g))
    Bc = np.full((GRID, GRID), float(b))
    A = np.full((GRID, GRID), 255.0)
    for reg in (regions or []):
        m = np.asarray(reg['mask'], bool)
        if not m.any():
            continue
        R[m] = remap(L, reg['r_range'][0], reg['r_range'][1], reg.get('r_invert', False), m)[m]
        Gc[m] = reg['g']
        if 'b' in reg:
            Bc[m] = reg['b']
    for em in (emission or []):
        m = np.asarray(em['mask'], bool)
        if not m.any():
            continue
        if 'range' in em:
            A[m] = remap(L, em['range'][0], em['range'][1], False, m)[m]
        else:
            A[m] = em['value']
        A[m] = np.clip(A[m], 1, 254)
    if clear_alpha:
        tr = tex[..., 3] <= 0
        R[tr] = 0.0
        Gc[tr] = 0.0
        Bc[tr] = 0.0
        A[tr] = 255.0
    out = np.dstack([up(R), up(Gc), up(Bc), up(A)]).round().clip(0, 255).astype('uint8')
    return Image.fromarray(out, 'RGBA')


# ---------- output ----------
def save_with_channels(img, path, channel_dir=None):
    """Save the combined texture plus one greyscale PNG per channel (<name>_R.png ... <name>_A.png)."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    img.save(path)
    stem = os.path.splitext(os.path.basename(path))[0]
    cdir = channel_dir or os.path.dirname(os.path.abspath(path))
    os.makedirs(cdir, exist_ok=True)
    for i, c in enumerate('RGBA'):
        img.getchannel(i).save(os.path.join(cdir, f'{stem}_{c}.png'))


def check_n(img):
    """Basic LabPBR sanity checks for a generated _n. Returns a list of problems (empty = OK)."""
    a = np.asarray(img.convert('RGBA')).astype(float)
    problems = []
    if a[..., 3].min() < 1:
        problems.append('height contains 0 (minimum should be 1)')
    x = (a[..., 0] - 127) / 127
    y = (a[..., 1] - 127) / 127
    if (x * x + y * y).max() > 1.0:
        problems.append('normal xy longer than 1 somewhere (z cannot be reconstructed)')
    return problems


def check_s(img):
    """Basic checks for a generated _s. Returns a list of problems (empty = OK)."""
    a = np.asarray(img.convert('RGBA'))
    problems = []
    if img.mode != 'RGBA':
        problems.append('_s must be saved as RGBA so that non-emissive pixels carry A = 255')
    if (a[..., 3] == 0).any():
        problems.append('emission (A) contains 0; non-emissive pixels must be 255, never 0')
    g = a[..., 1]
    if ((g >= 238) & (g <= 254)).any():
        problems.append('G uses 238-254, which LabPBR leaves undefined')
    return problems


def mask_from_rows(rows, on='#'):
    """Build a 16x16 bool mask from 16 strings of 16 characters, e.g. '####....####....'."""
    if len(rows) != GRID or any(len(r) != GRID for r in rows):
        raise ValueError('mask needs 16 rows of 16 characters')
    return np.array([[ch == on for ch in r] for r in rows])
```
