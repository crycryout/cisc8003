# CISC8003 / Homework 1 四机实测

**[实验报告 PDF](homework1/report/Homework1_Report.pdf) · [可编辑报告](homework1/report/Homework1_Report_Draft.md) · [实际执行记录](docs/LAB_EXECUTION.md)**

已用实验室四台独立物理主机完成必做实验：Thor 为 master；H800 主机、两台 5090 各为一个 worker。GPU 不参与计算，H800 的两个 NUMA 节点没有拆分。软件为 Hadoop 3.3.6、Java 11、Python 3；真实服务截图、成功 JobHistory 和输出核验均已保存。

| 内容 | 本次真实结果 |
|---|---|
| Q1(a) | 四台分别完成独立 HDFS/YARN WordCount；词频完全正确 |
| 四机集群 | 3 Live DataNode、3 RUNNING NodeManager；smoke 在三个 workers 执行 |
| Q1(b) | Shakespeare 两种输入各 3 次；中位数 76.364 / 8.430 s，merged 快 9.06 倍；六次词频一致 |
| Q1(c) | 完整 5,341,868,833-byte Yelp；实际 6/1、6/3、12/1、12/3 四组均成功，七项时间齐全、输出一致；四组各 3 次全部成功 |
| Q2(a) | 中图六个 YARN jobs 成功；81,306 用户，1,000 独立抽样零误差、全量参考排名零差异；全部 1,000 个 suffix 已导出 |

本次证据根：[homework1/evidence/lab-20261106T110350Z](homework1/evidence/lab-20261106T110350Z/)。计时来自成功 JobHistory 的 job/task 时间；没有使用历史 LocalJobRunner 数据填充四机性能表。实际主机分配、共享负载和环境差异在报告中如实说明。

## 结果文件

- [本次全量中图 Top-10](homework1/artifacts/medium_all_users_top10_lab-20261106T110350Z.txt.gz)。新 raw SHA 会受 part 顺序影响；已逐用户比较候选顺序并通过。
- [全部学号后三位文件](homework1/artifacts/medium_by_suffix_lab-20261106T110350Z.tar.gz)：`000.txt` 至 `999.txt`，完整计算后才筛选，共 81,306 行。
- [验收清单](docs/ACCEPTANCE.md)、[证据索引](docs/EVIDENCE_INDEX.md)、[工作日志](docs/WORK_LOG.md)。旧接续说明保留为历史，不要据此重新 format 已有 HDFS。

原始图、Shakespeare 和 Yelp 文件不进入 Git；下载来源、字节数与哈希在 manifests。公开证据只遮蔽访问地址和账号标识；原始未脱敏记录及完整机器访问配置留在忽略的 `.local/` 与本次 `results/lab-*/`。

## 复核

```bash
cd ~/cisc8003
python3 scripts/verify_repository.py
python3 -m unittest discover -s homework1/tests -v
```

[部署与重复实验](homework1/cluster/LAB_E2E.md)使用独立配置、端口、PID、日志和数据目录。新实验选择新输出根；已有 NameNode 不重新 format。源码保持精确共同关注数 Top-10，未用近似或提前按 SID 过滤。

报告披露了实验室硬件替代课程云 VM/课程集群的选择，以及 AI 协助。大图 bonus 未完成，不将中图算作 bonus。姓名、SID、声明和签名留给学生本人核实填写。

下一步：在报告源文件填写姓名和 SID，再从归档中选择对应的后三位文件。
