# 🔍 Hallucination Detector — LLM 幻觉检测中间件

[![CI](https://github.com/malaxiya20250530-glitch/shiyan2925/actions/workflows/test.yml/badge.svg)](https://github.com/malaxiya20250530-glitch/shiyan2925/actions)
[![Build](https://github.com/malaxiya20250530-glitch/shiyan2925/actions/workflows/build-binaries.yml/badge.svg)](https://github.com/malaxiya20250530-glitch/shiyan2925/actions)
[![Python](https://img.shields.io/badge/Python-3.13-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-Proprietary-red)](LICENSE)
[![Lines](https://img.shields.io/badge/Code-17K%20lines-brightgreen)](.)
[![Stars](https://img.shields.io/github/stars/malaxiya20250530-glitch/shiyan2925?style=social)](https://github.com/malaxiya20250530-glitch/shiyan2925)

> **零外部依赖** | **14 检查器责任链** | **四级管道检测** | **自进化知识库** | **跨平台加密编译**

一个可独立部署的 LLM 安全中间件。像 CDN 一样接入你的 AI 应用，在大模型输出到达用户之前，拦截其中的幻觉和事实错误。

---

## ⚡ 5 秒体验

```bash
# 检测一条声明
python3 hallucination_detector.py "朱元璋发明了火锅"
```
输出：
```
🔴 [矛盾] 朱元璋发明了火锅
   证据: 朱元璋是明朝开国皇帝，1328-1398 年
   来源: 明史
   可信度: 90%
```

---

## 🏗️ 架构

```
用户请求 → awareness_gateway (OpenAI 兼容 API)
              ├─ BillingMiddleware  ← 计费 + 限流
              ├─ ObserverSecurity   ← 安全中间件
              ├─ HallucinationDetector
              │    ├─ 14 个 Checker 加权责任链
              │    ├─ Knowledge Graph (608 条事实)
              │    ├─ Vector KB (混合检索)
              │    └─ Web Verifier (联网交叉验证)
              ├─ Consensus Engine   ← 多模型共识
              ├─ Alignment Analyzer ← 对齐分析
              └─ Feedback → Auto KB Updater (自进化)
```

## 🚀 核心能力

| 能力 | 说明 |
|------|------|
| **管道检测** | KB → 向量检索 → 联网验证 → 绝对化断言，四级级联 |
| **加权责任链** | 14 个检查器各带 F1 权重，高权重优先裁决 |
| **自进化** | 用户反馈 → 重映射 → KB 自动更新 |
| **多协议** | Ollama + OpenAI 双协议，一行命令切换 |
| **计费系统** | API Key + 套餐分级 + 按 token 计费 |
| **行业知识库** | 医疗 (45 条) + 法律 (52 条) 垂直领域 |
| **可视化仪表盘** | 实时幻觉率、检测日志、计费统计 |
| **加密编译** | Cython → .so 二进制，GitHub Actions 四平台云编译 |
| **零依赖** | 纯 Python 标准库，无 pip install |

## 📦 快速开始

### 安装

```bash
git clone git@github.com:malaxiya20250530-glitch/shiyan2925.git
cd shiyan2925
# 零依赖，直接运行！
```

### 三种使用方式

**1. CLI 单条检测**
```bash
python3 hallucination_detector.py "爱迪生发明了电灯泡"
```

**2. 启动网关 (OpenAI 兼容)**
```bash
python3 awareness_gateway.py --mock --port 8800
# 然后像调用 OpenAI 一样使用
curl http://localhost:8800/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-f你的key" \
  -d '{"model":"mock","messages":[{"role":"user","content":"你好"}]}'
```

**3. 可视化仪表盘**
```bash
python3 dashboard_server.py --port 8080
# 浏览器打开 http://localhost:8080
```

### API 计费

```bash
# 创建 API Key（支持 free/basic/pro/enterprise 四档）
python3 billing.py create "客户A" pro

# 查看统计
python3 billing.py stats

# 分发密钥给客户，按 token 自动扣费
```

---

## 🧪 测试

```bash
# 单元测试
python3 test_fact_checker.py

# 全量集成测试
python3 test_knowledge_graph.py
python3 test_alignment_middleware.py
python3 test_observer_security.py
python3 test_feedback_store.py

# 端到端 DeepSeek 实测
python3 test_deepseek.py
```

## ☁️ 云编译

推送代码后 GitHub Actions 自动编译四平台 `.so`/`.pyd`：

| 平台 | Runner |
|------|--------|
| Linux x86_64 | ubuntu-latest |
| macOS x86_64 | macos-13 |
| macOS arm64 (M1/M2) | macos-latest |
| Windows x86_64 | windows-latest |

详见 [Actions](https://github.com/malaxiya20250530-glitch/shiyan2925/actions)

---

## 📊 项目规模

- **17,733 行** Python 代码
- **61 个** 模块
- **14 个** 幻觉检查器
- **608 条** 知识库事实
- **6 条** CI/CD 工作流
- **5 组** 单元测试 + 集成测试

---

## 🗺️ 路线图

- [x] 14 检查器加权责任链
- [x] 自进化反馈系统
- [x] API 计费 + 限流
- [x] 医疗 + 法律行业知识库
- [x] 可视化仪表盘
- [x] 跨平台加密编译
- [ ] 多语言国际化
- [ ] 插件市场
- [ ] 云端 SaaS 版

---

## 📄 许可证

专有软件 — 保留所有权利。联系作者获取商用授权。

Copyright (c) 2025-2026 李桥
