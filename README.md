# 🤖 Personal AI Employee

> A Local-First AI Employee system with autonomous task execution, skill architecture, and constitutional governance.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Status](https://img.shields.io/badge/Status-Active-success)](https://github.com)

## 🌟 Overview

The **Personal AI Employee** is a production-ready, markdown-driven autonomous task execution engine that operates entirely on your local machine. Built with constitutional governance and skill-based architecture, it processes tasks through a pipeline of specialized AI skills while maintaining full auditability and traceability.

## ✨ Features

- 🏠 **Local-First**: All data stays on your machine - no external data leakage
- 📚 **Constitutional Governance**: Company Handbook acts as immutable ruleset for all AI behavior
- 🛠️ **Skill Architecture**: Reusable skill system with inheritance and chaining capabilities
- 🔄 **Automated Pipeline**: Filesystem watcher → Task Manager → Skill Executor → Completion
- 📝 **Full Audit Trail**: Complete logging of all decisions, transitions, and executions
- ⚡ **Self-Managing**: Automatically processes tasks with minimal human intervention

## 🗂️ Repository Structure

```
📁 Personal AI Employee/
├── 📁 Bronze Tier/           # Core AI Employee system
│   ├── 📄 filesystem_watcher.py     # Monitors /Inbox for new tasks
│   ├── 📄 orchestrator.py           # Central execution engine
│   ├── 📄 Company_Handbook.md       # Constitutional authority
│   ├── 📁 Skills/                  # Skill architecture
│   ├── 📁 Dashboard/               # Command center
│   ├── 📁 Inbox/                   # Incoming tasks
│   ├── 📁 Needs_Action/            # Pending tasks
│   ├── 📁 Done/                    # Completed tasks
│   ├── 📁 Logs/                    # Comprehensive logging
│   └── 📁 Plans/                   # Generated task plans
```

## 🏗️ Bronze Tier Components

The Bronze Tier represents the foundational AI Employee system with these key components:

### 📋 **Constitutional Framework**
- **Company Handbook v2.0**: Immutable ruleset governing all AI behavior
- **4-Tier Approval System**: From fully autonomous (Tier 0) to highly restricted (Tier 3)
- **Error Classification**: E1-E4 severity levels with escalation protocols

### ⚙️ **Core Architecture**
- **Skill Base Contract (SK-BASE)**: Universal interface for all skills
- **File Processor (SK-010)**: Task intake and classification
- **Task Manager (SK-011)**: Lifecycle transitions and routing
- **Task Executor (SK-012)**: Primary reasoning loop
- **Filesystem Watcher**: Monitors /Inbox with anti-reprocessing safeguards
- **Orchestrator**: Central engine with completion-driven loops

### 🔄 **Task Lifecycle**
1. 📥 **Inbox**: Tasks enter as markdown files
2. ⏳ **Needs Action**: Prioritized queue with metadata
3. 🤖 **Processing**: AI executes through 7-step reasoning loop
4. ✅ **Done**: Completed with full audit trail

## 🚀 Usage

1. Place a task file in the `/Inbox` directory
2. The `filesystem_watcher.py` detects the new file
3. `orchestrator.py` processes the task through the skill pipeline
4. Results appear in `/Done` with complete logs in `/Logs`

## 📊 Skills System

| Skill ID | Name | Purpose | Tier |
|----------|------|---------|------|
| SK-BASE | Skill Base | Universal contract for all skills | N/A |
| SK-010 | File Processor | Task intake and classification | 0 |
| SK-011 | Task Manager | Lifecycle transitions | 0 |
| SK-012 | Task Executor | Primary reasoning loop | 0 |

## 🛡️ Security & Safety

- 🔐 **Secret Detection**: Halts processing if sensitive data detected
- 📜 **Append-Only History**: Never overwrites existing files
- ⚖️ **Constitutional Limits**: Strict adherence to Company Handbook
- 🔄 **Stale Loop Protection**: Automatic halting after 3 repeated cycles

## 📈 Development Tiers

- 🥉 **Bronze Tier**: Core autonomous task execution
- 🥈 **Silver Tier**: Advanced skill chaining and planning
- 🥇 **Gold Tier**: Multi-agent coordination and complex workflows

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for more details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with Claude for AI reasoning
- Designed for local-first, privacy-conscious operation
- Inspired by constitutional governance principles

---

> 🚀 *Ready to automate your personal workflows with a trustworthy, local-first AI assistant*