# Homework 1 代码包入口

解压 `Homework1_Code_Report.zip` 后，在解压根目录执行：

```bash
python3 -m unittest discover -s homework1/tests -v
bash -n homework1/src/run_community.sh
```

1. `homework1/src/community.py` 是六阶段 mapper/reducer 的共用入口；`run_community.sh` 提交真实 Hadoop Streaming jobs。去重、共同 followee 整数计数、同分数值 ID 升序、自身排除与零分补齐均在完整用户集合上执行。输入二列顺序必须显式确认。
2. Hadoop 3.3.6 / JDK11 / Python3 运行说明在 `homework1/cluster/LAB_E2E.md`。课程数据由 `fetch_course_data.py` 从题目链接取得；已有文件先校验，再复用。为新实验生成独立配置和输出根；已有 NameNode 不重新 format。实际私密访问配置留在实验室账号中。
3. `graph_audit.py build` 从原始输入构建磁盘去重索引并统计规模；`validate` 全量检查输出用户集合、格式与候选合法性，另做固定种子和定向用户精确重算；`export` 流式导出并核对全部1,000 suffix。各子命令的 `--help` 提供参数，ID不转浮点。中图历史全量参考对比脚本在 `scripts/compare_top10.py`。
4. `RESUME_FROM_STAGE=n` 要求所有上游成功标记，拒绝既有下游目录或阶段日志。先检查活动作业；失败输出及日志移入独立归档目录并保留 job IDs 后，再继续首个未成功阶段。`COMPRESS_INTERMEDIATES=1 INTERMEDIATE_REPLICATION=1` 仅影响04/05；单副本中间结果失去后需重算。`STOP_AFTER_BLOCKS=1` 用于初次容量检查，与从04以后恢复互斥。
5. 最终 PDF 和可编辑报告位于 `homework1/report/`，真实已脱敏证据位于 `homework1/evidence/`。`PACKAGE_MANIFEST.json` 为包内每个文件记录字节和 SHA-256；服务器交付目录另有 ZIP 的 SHA256SUMS。学生信息、署名、声明、课程要求及平台上传按 `docs/FINAL_SUBMISSION.md` 由本人处理。

中图与大图结果在独立 `Homework1_Results.zip`：包含全量结果、全部 suffix 归档及验证/哈希清单。选取与本人学号末三位对应的中图和大图文件；无需向程序提供完整学号。

完整 Git checkout 的仓库字节清单由 `scripts/verify_repository.py` 检查；此 allowlist 代码包以自己的 PACKAGE_MANIFEST 为准。快照哈希验证只说明文件完整性，实际实验成功以 JobHistory、counters 和独立结果验证为依据。
