本目录同时保留旧版、开发中失败/拒绝记录与新版结果。
已发布 v0.2 的通过项以交付/v0.2/ 工程包中的 acceptance_receipt.json 及相同 ROM SHA-256 为准。
开发版分项结果见 mechanisms/functional_status.json；该状态明确不等于全游戏验收通过。
chapter_progress/stopped.png 和 refactor/menus/failed_commands.json 等历史停止记录不表示当前通过流程失败，也不计为当前通过证据。
refactor/rejected_* 保存问题定位和测试脚本不符合原作限制时的失败记录，后续按原数据修正验证方式。
菜单验收里的“锻造/制甲”明确为 not_run；不能把总报告 pass 理解为全部制作系统已通过。
普通存档为实际流程副本；intentional_corruption 用于坏档拒绝测试。
mechanisms/ 下主机受控测试会设置角色、开关、敌人 HP 等测试输入，不计作自然剧情通关。
mechanisms/battle_capacity 是单独的 GBA 测试程序，使用原敌群验证十目标选择，没有改写试玩 ROM。
