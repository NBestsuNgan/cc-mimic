# ⌁ cc-mimic

A lightweight Claude Code mimic — forge your own AI coding agent.

---

## ⚡ Quick Start

### Prerequisites

```bash
# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate
```

### 📦 Installation

```bash
cd ~/Users/user_name/desktop/cc-mimic
pip3 install -e .
```

---

## ⊹ Features

| Status    | Feature                                                                    |
| --------- | -------------------------------------------------------------------------- |
| ◌ Pending | Sandboxing                                                                 |
| ◌ Pending | LSP (Language Server Protocol)                                             |
| ◌ Pending | `apply_patch`                                                              |
| ◌ Pending | `skill.md`                                                                 |
| ✅ Done | `initialize .ai-agent and it configuration in the cwd() that call myagent` |

---

## ⚙ Configuration

Environment variables are resolved from the **current working directory**.

### Environment Variables

Create a `.env` file in the project root with the required variables:

```bash
cp .env.example .env
```

Then edit `.env` and add your API key:

```env
API_KEY=your_key_here
```

> **Note:** Replace `your_key_here` with your actual API key obtained from the [Openrouter Console](https://openrouter.ai/).

---

## ⊕ Contributing

Contributions are welcome! Feel free to open an issue or submit a pull request.
