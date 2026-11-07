# 给服务器 Codex 的当前任务

更新时间：2026-11-07。必做四机实验与报告主体已完成；本轮补完 Q2(b) 大图加分题和最终提交包。

请完整读取并直接执行 [BONUS_COMPLETION_HANDOFF.md](BONUS_COMPLETION_HANDOFF.md)，再核对根目录 AGENTS.md、LAB_EXECUTION.md、WORK_LOG.md 和 ACCEPTANCE.md。正常可逆操作和现有四台机器的计算已获授权，不要只给计划，不要重跑已经完成的整套 Q1/中图实验。

复用 Thor master、H800 和两台 5090 workers，恢复现有隔离配置而非重新 format。先下载并核实原题 Ref[8] 大图，执行前三阶段，依据实际 CandidatePairs 与各节点磁盘检查容量，再继续完整精确全用户 Top-10。完成独立验证、000–999 后缀、真实 JobHistory/截图、报告、代码和结果包，并同步仓库。

现有 validate_medium.py 与 export_suffixes.py 会把全图/结果装入内存；大图需评估内存或增加流式/磁盘支持。RESUME_AFTER_BLOCKS 只恢复前三阶段，阶段 4–6 中断须明确检查恢复点，不删除已有成功结果。具体命令、验证标准、资源边界和最终验收均见新接续文档。

缺少完整 SID 不阻塞计算与导出；姓名、SID、本人声明与签名留给用户核实。保留实验室替代云 VM、AI 协助和未取得教师正式批准的真实说明，不代签、不虚构许可。只有真实大图输入、作业和验证完成后才能勾选 bonus。

旧 H800_CODEX_HANDOFF.md 保留历史，不以其中“必做尚未执行”的表格判断当前进度。若遇到真实访问、数据或容量阻塞，先完成不依赖阻塞的部分，保存精确恢复点，再说明缺少什么。
