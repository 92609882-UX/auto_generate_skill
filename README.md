# auto_generate：Minecraft LabPBR 贴图自动生成

这个文件夹保存了从底色贴图直接生成 `_n`、`_s` 贴图的全部方法、脚本和资料。新开对话时从这里开始。

## 新对话怎么开始

1. 在 Claude 桌面端连接两个文件夹：
   - `E:\mcproperty\auto_generate`（本文件夹）
   - `E:\mcproperty\05‘s_resourcepacks`（参考材质包）
2. 对 Claude 说："按 minecraft-labpbr-textures skill 工作，先读 auto_generate 里的 README.md、training_log.md 和 TRAINING.md，然后开始训练。"
3. 如果 skill 没有保存到账号里，就让 Claude 直接读本文件夹的 `SKILL.md`，内容是一样的。

## 给 Claude 的阅读顺序

1. `SKILL.md`：完整的规则、取值表和脚本说明。
2. `training_log.md`：作者在训练中给出的修正。**这里的结论优先于 SKILL.md 的默认值。**
3. `TRAINING.md`：训练怎么做。
4. `reference/`：需要查细节或数据来源时再读。

## 文件说明

| 文件 | 内容 |
|---|---|
| `SKILL.md` | skill 全文（和账号里的 skill 相同） |
| `labpbr_gen.py` | 生成脚本：`build_n`、`build_s`、`save_with_channels`、`check_n`、`check_s` |
| `train_tools.py` | 训练辅助：带坐标的底色预览、读取参考包的做法、逐通道对比 |
| `TRAINING.md` | 训练流程 |
| `training_log.md` | 训练记录和已确认的结论 |
| `reference/conventions.md` | 作者在对话中说明的全部约定（原始记录） |
| `reference/height-classification.md` | 参考包 `_n` A 通道的统计和高度分档 |
| `reference/normal-generation.md` | 参考包 `_n` R、G 通道的规律 |
| `reference/s-generation.md` | 参考包 `_s` 各通道的规律和取值表 |
| `reference/labpbr-spec.md` | LabPBR 1.3 规范速查 |
| `reference/pack-layout.md` | 参考包 v5003 的整包做法：物品/实体/盔甲/纹饰、CTM、随机变体、版本适配 |
| `data/*.csv` | 逐张贴图的统计数据 |
| `examples/n_test/` | 第一次试生成的四张 `_n`、各通道灰度图和对比图 |
| `training/` | 每轮训练的产出放这里，一轮一个子文件夹 |

## 参考材质包

- 位置：`E:\mcproperty\05‘s_resourcepacks`
- 主包：文件名含"零雾构想 v5003"的 zip，方块贴图在 `assets/minecraft/textures/block/`
- 贴图是 128×128。底色贴图里烘焙了少量阴影，脚本读取时取每个 8×8 块的中心像素作为该块的颜色。
- 整包（物品、实体、盔甲、纹饰、连接纹理、模型改动）的做法统计在 `reference/pack-layout.md`。
- 注意：参考包只是参考，不是标准答案。作者和参考包做法不同的地方，以作者为准（见 `training_log.md`）。

## 运行环境

Python 3，需要 `numpy` 和 `Pillow`。

```python
import labpbr_gen as lg
tex = lg.load_texels('stone.png')
n, H = lg.build_n(tex, lower=207, upper=231, step=8)
s = lg.build_s(tex, r_range=(52, 103), g=10, b=0)
lg.save_with_channels(n, 'out/stone_n.png', 'out/channels')
lg.save_with_channels(s, 'out/stone_s.png', 'out/channels')
```
