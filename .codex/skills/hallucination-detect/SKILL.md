---
name: hallucination-detect
description: "大模型幻觉检测与纠正：责任链检查器、知识库比对、F1 加权决策。用于检测 LLM 输出中的事实冲突、年份错误、数值矛盾等。"
---

# 🔍 大模型幻觉检测器

基于责任链模式的幻觉检测系统——`hallucination_detector.py` 遍历 14 个检查器，
每个检查器返回 `(result_type, confidence)` 或 `None`，最终用 F1 加权合并决策。

## 触发条件

当用户提到以下情况时使用本 skill：
- 检测某段文本是否包含幻觉
- 对比声明与知识库事实
- 运行质量门禁测试
- 添加新的幻觉检查器
- 诊断幻觉检测器的行为
- `$hallucination-detect` 或 `$幻觉检测`

## 核心命令

```bash
# 事实核查
python3 hallucination_detector.py "朱元璋发明了火锅"

# 语法检查
python3 -c "import hallucination_detector"

# 完整测试套件（5 组，必须全绿）
python3 test_fact_checker.py

# 知识图谱检查器测试
python3 test_graph_checker.py

# 压力测试
python3 test_stress.py

# 启动感知网关
python3 awareness_gateway.py --port 8800 --mock
```

## 架构概览

```
claim → AnchorEngine → _compare_with_fact()
                         ├── Checker 1: 精确匹配
                         ├── Checker 2: 年份冲突
                         ├── Checker 3: 数值矛盾
                         ├── ... (14 个检查器)
                         └── Checker 14: 语义回退
                                   ↓
                         F1 加权决策 → 结果
```

## 知识库

| 存储 | 规模 | 用途 |
|------|------|------|
| `knowledge/fact_store.db` | 704万条，1.6GB | 事实数据库 |
| `knowledge/kb_core.json` | 语义索引 | 快速检索 |
| `kb_user.json` | 用户补充 | 自定义事实 |

## 质量门禁（改动后必须执行）

1. `python3 test_fact_checker.py` — 5 组全绿
2. `python3 -c "import hallucination_detector"` — 无语法错误
3. 新增检查器必须有 docstring
4. 不得破坏 Checker.registry 注册顺序

## 添加新检查器

只需两步：
1. 在 `checker_classes.py` 中继承 `Checker` 类，实现 `check()` 方法
2. 用 `@checker` 装饰器注册

```python
@checker
class DateConflictChecker(Checker):
    """检测日期冲突"""
    def check(self, claim, fact):
        # 返回 (result_type, confidence) 或 None
        ...
```

## 架构铁律

- 所有代码必须服务于大模型幻觉检测
- 必须接入真实数据管道（fact_store.db）
- 禁止悬浮的"认知架构"沙盒
- 改动后必须通过质量门禁
- 纯 Python 标准库，禁用外部依赖

## 关键文件

| 文件 | 职责 |
|------|------|
| `hallucination_detector.py` | 主检测引擎 |
| `checker_classes.py` | 14 个检查器实现 |
| `checker_registry.py` | 检查器装饰器 + 注册表 |
| `test_fact_checker.py` | 5 组单元测试 |
| `awareness_gateway.py` | LLM 感知网关 |
| `config.json` | 检测器配置 |
