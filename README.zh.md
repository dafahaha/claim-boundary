# claim-boundary

**用实测范围清单给研究草稿的措辞设闸门。** JSON manifest 记录种子数、对比臂、环境和
是否观察到差异；扫描器逐行标出越过边界的声明：无对比臂却写优越性、n<3 写"稳定"、
普适化外推、种子数对不上、把零结果包装成胜利。

纯 Python 标准库，离线运行，中英双语短语表。

> **范围前置说明：** 词表只覆盖已知的夸大模式，不是穷尽所有创意改写；它是确定性的
> 兜底，不是语义审稿人。每条 finding 都需人工复核——词表工具会有误报。

## 为什么存在

AI 写作助手和研究者升级措辞的速度快于升级证据：只有一个臂、一个种子或根本没观察到
差异时，仍会出现 "outperforms"、"generalizes to all"、"stable across seeds"。
claim-boundary 是提交前的确定性闸门，不是文风改写器。

## 安装

无需编译，无需依赖。

- Claude Code：`claude --plugin-dir ./claim-boundary`，或在
  `.claude-plugin/marketplace.json` 注册本地市场。
- 便携 skill（Codex/Cursor/Gemini CLI/Roo Code）：把 `skills/claim-boundary/`
  复制到客户端的 skills 目录。

## 用法

```bash
python skills/claim-boundary/scripts/claim_boundary.py draft.md \
  --manifest scope.json [--json] [--output report.md]
```

Manifest（见 `assets/example-manifest.json`）：

```json
{
  "seeds": 3,
  "envs": ["CartPole-v1"],
  "arms": ["method", "baseline"],
  "no_difference": false
}
```

### 退出码

| 码 | 含义 |
|---|---|
| 0 | 干净 |
| 2 | 警告（低 n 优越性、未声明环境、manifest 不一致） |
| 3 | 失败（夸大、外推、数字不符、零结果包装成胜） |
| 1 | 用法 / IO / manifest 格式错误 |

## 相关工作

- [q1-reviewer-mcp](https://pypi.org/project/q1-reviewer-mcp/) 是 LLM 驱动的 Q1
  Reviewer#2 模拟器（红旗矩阵、夸大声明、n<3 重复、绝对化语言）；它依赖宿主 LLM、
  面向生物医药，且不读机器可读 manifest。[OVER_CLAIM_GUARD](https://bahayonghang.github.io/academic-writing-skills/skills/typst-paper/resources/references/OVER_CLAIM_GUARD.html)
  是静态措辞替换表，无 manifest 交叉核对、无退出码。本工具与之互补：确定性、离线、
  双语，把草稿措辞与 JSON manifest 逐字段对账，并给出 CI 可闸门的退出码。
- 与 [seedlot](https://github.com/dafahaha/seedlot) 配对：seedlot 核对数字
  （n、均值、CI、重叠），claim-boundary 核对措辞是否超出声明的实测范围——
  组成"诚实报告"两步。

## 测试

```bash
python -m pytest tests/ -q
```

38 个测试，仅标准库；人工谓词变异抽查（翻转 R1 臂闸门会使优越性测试变红；记录在
CHANGELOG）。

## 限制（诚实披露）

- 基于词表：只抓已知短语，抓不到所有创意夸大；预期有误报，行动前逐条阅读。
- 信任 manifest；无法验证实验真的跑过。
- 不是统计检验、不是语义审稿人、也不是文字编辑；每条 finding 都需人工判断。

## 许可证

MIT，© 2026 Daizhi Liao (dafahaha)。
