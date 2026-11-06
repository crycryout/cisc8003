# Homework 1 代码与实验入口

**本仓库版本不附带原始课程数据和 Yelp 文件。** 先读根目录的接续记录；`cluster/LAB_E2E.md` 是当前部署说明。原始打包版 README 保存在 `../docs/history/`，其中“数据已在包内”的说法只适用于此前交付的 ZIP，不适用于本 Git checkout。

## 本地检查

```bash
python3 -m unittest discover -s tests -v
python3 cluster/lab_preflight.py --work-dir "$HOME"
bash cluster/bootstrap_node.sh --plan
```

第二条在当前主机执行只读检查，不是集群测量。完整中图参考结果和原始本地日志在 `artifacts/`；用途和解压方式见 `../docs/EVIDENCE_INDEX.md`。

## 数据准备

```bash
python3 src/fetch_course_data.py medium --decompress
python3 src/fetch_course_data.py shakespeare
```

先检查 Shakespeare tar 的成员及目录，再安全提取到独立目录，仅将文本交给 `src/prepare_words.py --source TEXT_DIRECTORY --output data/shakespeare_prepared-new`。参考 manifest 是 `data/shakespeare_prepared/manifest.json`，共 196 个文件、6,460,189 字节。将准备好的输入放到 `data/shakespeare_prepared/small` 和 `data/shakespeare_prepared/merged.txt`，或在核对 manifest 后修改本次运行脚本的输入路径。不要覆盖参考 manifest，也不要把归档/图片当作文本。

Yelp 使用官方公开 ZIP，具体 URL、大小、sha256 和 gzip-tar 扩展名陷阱见 `../docs/H800_CODEX_HANDOFF.md`。上传 HDFS 前应使用完整、未压缩的 review JSONL。

## 四机必做入口

完成部署和 smoke test，上传真实输入后，在 master 上执行：

```bash
source "$HOME/hadoop-env-user.sh"
source generated-lab/homework-env.sh
REPETITIONS=1 bash cluster/run_required.sh \
  /hw1/input/yelp/reviews.json /hw1/input/community/medium.txt
```

脚本执行两种 Shakespeare 设置、四组 Yelp 设置和 Q2 六阶段；保留新输出及日志。先确认一次完整成功，正式对照可设 `REPETITIONS=3`。计时字段按 JobHistory 定义，不能用提交端 wall-clock 替代。

## 主要实现

| 路径 | 用途 |
|---|---|
| `src/community.py`、`src/run_community.sh` | 分块精确共同关注 Top-10，六阶段 Streaming |
| `src/run_wordcount.py`、`src/metrics.py` | Q1 执行、实际 M/R 数、七项计时、原始 History 和输出校验 |
| `src/validate_medium.py` | 覆盖全体用户并独立抽样重算 |
| `src/filter_suffix.py`、`src/export_suffixes.py` | 完整计算后按学号末三位导出 |
| `cluster/` | 架构适配、配置、只读预检、部署与总入口 |

`report/` 中的 Markdown/PDF 是待补实测的历史草稿，`build_report.py` 用 ReportLab 和 DejaVu 字体生成 PDF。Hadoop/Python 核心实现与单元测试只依赖 Python 标准库；生成报告时才需准备 ReportLab 与对应字体。
