# 项目身份
你正在维护 `hallucination_detector.py` —— 一个幻觉检测模块，核心是 `_compare_with_fact()` 函数和优先级检查器链。项目位于 Android Termux 环境，所有代码在 `/data/data/com.termux/files/home/`。

# 核心约束（必须遵守）

## 架构底线
- **检查器注册**：新增检查器只需两步——写函数 + 把名字加到 `_PRIORITY_CHECKERS` 列表
- **不破坏责任链**：`_compare_with_fact()` 保持 2 层嵌套，不改成其他模式
- **单一职责**：每个 `_check_xxx` 只做一种冲突检测，返回 `(result_type, confidence)` 或 `None`

## 质量门禁（改动后必须做）
- 运行 `python3 test_fact_checker.py`，确保 5 组测试全部通过
- 运行 `python3 -c "import hallucination_detector"` 确保无语法错误
- 新增函数必须有 docstring（一句话说清做什么）
- 不改动 `_PRIORITY_CHECKERS` 顺序除非明确知道优先级变更

## 禁止项
- ❌ bare except —— 用 `except (URLError, OSError, ValueError)` 等具体异常
- ❌ 硬编码配置 —— 用 `config.json` 或环境变量
- ❌ 超过 8 层嵌套 —— 发现后立即用提前返回或提取函数重构
- ❌ eval / exec / os.system / shell=True
- ❌ 引入外部依赖 —— 保持纯 Python 标准库

# 编码习惯

## 命名
- 变量：`snake_case`
- 检查器方法：`_check_` 开头，如 `_check_year_conflict`
- 私有函数：前缀 `_`

## 代码组织
- 导入顺序：标准库 → 本地模块
- 函数长度：不超过 50 行，超过则拆分
- 注释：解释"为什么"，不解释"做什么"

## 测试风格
- 无外部依赖，纯 `python3 test_fact_checker.py` 运行
- 测试函数命名：`test_<功能>_<场景>`
- 用列表驱动测试覆盖多个输入

# 决策记录

| 决策 | 原因 | 日期 |
|------|------|------|
| 用责任链模式代替深层嵌套 | 13层嵌套无法维护 | 2026-05-30 |
| 检查器用列表注册而非类继承 | 简单、直观、新增成本低 | 2026-05-30 |
| 单元测试覆盖命中/未命中/优先级 | 为后续修改提供安全网 | 2026-05-30 |
| 同义词映射 SYNONYM_MAP 扩充 KB | 突破关键词天花板 | 2026-05-29 |
| 双协议 Ollama/OpenAI SSE | 网关对接真实 LLM | 2026-05-29 |

# 已完成
- [x] 静态扫描 bare except 清零
- [x] 嵌套 13→6（`_compare_with_fact` 拆为 5 个子检查器）
- [x] 单元测试 221 行，5 组场景，全部通过
- [x] `_PRIORITY_CHECKERS` 模块级常量提取
- [x] 同义词映射 + bigram 语义回退
- [x] 网关 Ollama 协议兼容

# 常用命令
```bash
# 单元测试
python3 test_fact_checker.py

# 语法检查
python3 -c "import hallucination_detector"

# 快速事实核查
python3 hallucination_detector.py "朱元璋发明了火锅"

# 启动网关
python3 awareness_gateway.py --port 8800 --mock

# 演示
bash demo_auto_captions.sh
```
