# 废都物语 GBA 移植原型

把《Ruina 废都物语》的原始事件数据与规则接到原生 GBA 运行时的实验工程。供爱好者参考、修改与继续完善。

[v0.7 下载：工程与试玩 ROM](https://github.com/shiyi1133/Ruina-GBA/releases/tag/v0.7)

解压合集后，`试玩/` 中的 `.gba` 可直接用 GBA 模拟器打开；`工程/` 是与它匹配的源码和转换资源。
这版包含完整游戏数据，可继续游玩，支持普通 SAV；**全流程、全部结局和实机尚未验收**。

![首次地图](docs/首次地图.png)
![战斗选项](docs/战斗选项.png)

## v0.7 的主要变化

- 地图和人物保留原尺寸，通过滚动查看；光标、边缘箭头、文字与地图分层。
- 头像保留独立 RGB555 颜色；插图与战斗适配 240×160，部分原动画简化为切换。
- 菜单只更新变化的区域。战斗支持逐级 B 返回并保留上级选择，取消不消耗资源。
- 游戏与音乐欣赏均用简化音色，游戏过程中进一步简化。
- 剧情、技能数值、物品、配方、敌人与奖励数据保持原包内容。

这是有选择的 RM2000 兼容运行时，**并非完整 EasyRPG Player 的 GBA 移植**。颜色、分辨率与部分演出仍受 GBA 限制。

## 构建

已验证 Linux/WSL + Python 3 + GNU Arm Embedded 13.2.1：

```sh
python3 tools/build.py --incremental
```

输出为 `build/废都物语_GBA_开篇开发验证版.gba`。可通过 `ARM_TOOLCHAIN_PREFIX` 指定 `arm-none-eabi-` 前缀。
已转换资源随工程提供，正常重建不需要原 ZIP、系统字体或 Python 图像库。Windows 原生构建尚未验证。

重新转换素材时设置 `RUINA_SOURCE_ARCHIVE`、`RUINA_FONT`，并安装 Pillow/NumPy。详细操作见 `工程使用说明.txt` 与 `README.txt`。

## 工程入口与验证

- `runtime/rm2k/`：事件、战斗、地图、物品、存档等共用逻辑。
- `platform/gba/`：GBA 显示、音频、按键与存储。
- `source/`：本作启动、特殊列表和音乐欣赏。
- `build/`：保留的转换资源；编译产物由构建命令生成。
- `tools/validate_balanced.py`：当前验证入口，需外部 mGBA 开发库、C 编译器和图像库。
- `evidence/`：各版真实测试结果，包含失败、拒绝和未运行记录；请核对报告中的 ROM SHA-256。

发行包的源码 ZIP 已新解压重建，并与试玩 ROM 逐字节核对。模拟器抽查覆盖四种出身、首战、第一 CP、菜单返回、普通存档恢复和画面/声音专项，不能代替完整通关。

## 来源和许可

引擎及工具采用 GPL-3.0-or-later；上游代码及许可见 `third_party/`、`sources.lock.json` 与 `LICENSE`。
原游戏素材及汉化、修复内容保留各自权利归属。完整来源和署名见 `CREDITS.txt`。
