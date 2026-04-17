# MFS-Memory

**Memory File System** - A thermodynamics-inspired memory management system for AI agents.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: 300 passed](https://img.shields.io/badge/tests-300%20passed-green.svg)]()
[![Coverage](https://img.shields.io/badge/coverage-66%25-green.svg)]()

---

## 🎯 Overview

MFS (Memory File System) is a sophisticated memory management system designed for AI agents, particularly OpenClaw. It uses thermodynamic principles to organize, retrieve, and manage conversational memories with intelligent prioritization.

### Key Features

- **Thermodynamic Four Systems**: Energy (U), Heat (H), Temperature (T), Entropy (S), Free Energy (G)
- **SQLite FTS5**: Full-text search with BM25-like scoring
- **Knowledge Graph**: Automatic concept extraction and relationship mapping
- **Anti-Hallucination**: WAL (Write-Ahead Logging) for audit trails and rollback
- **Multi-modal Support**: Images, audio, and text with AI-generated summaries
- **Concurrent Access**: Thread-safe operations with proper locking

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/totwoto02/MFS-Memory.git
cd MFS-Memory

# Install dependencies
pip install -e .

# Run tests
pytest tests/ -v
```

### Basic Usage

```python
from mfs.mft import MFT

# Initialize MFT (Master File Table)
mft = MFT(db_path="mfs.db")

# Create a memory
inode = mft.create(
    path="/user/preferences",
    type="NOTE",
    content="User prefers dark mode and concise responses"
)

# Read a memory
result = mft.read("/user/preferences")
print(result["content"])

# Search memories
results = mft.search("preferences", scope="all")
for r in results:
    print(f"Path: {r['v_path']}, Content: {r['content']}")

# Update a memory
mft.update("/user/preferences", content="Updated preferences...")

# Delete a memory
mft.delete("/user/preferences")
```

---

## 📚 Core Concepts

### Thermodynamic Analogy

| Thermodynamics | MFS Memory System | Description |
|---------------|------------------|-------------|
| **Energy (U)** | Access Count | Total times a memory has been accessed |
| **Heat (H)** | Heat Score | Recent access frequency (0-100) |
| **Temperature (T)** | Relevance | Contextual relevance to current task |
| **Entropy (S)** | Controversy | Contradiction/uncertainty level |
| **Free Energy (G)** | Effectiveness | G = U - TS, determines if memory can be "extracted" |

### Memory States

| State | Heat Score | Description |
|-------|------------|-------------|
| 🔥 **Hot** | 70-100 | Frequently accessed, high priority |
| 🌤️ **Warm** | 40-69 | Moderately accessed |
| ❄️ **Cold** | 10-39 | Rarely accessed |
| 🧊 **Frozen** | 0-9 | Explicitly deprecated/low validity |

---

## 🔧 Architecture

```
MFS-Memory/
├── mfs/
│   ├── mft.py              # Master File Table (core)
│   ├── fts5_search.py      # Full-text search
│   ├── heat_manager.py     # Heat/Temperature system
│   ├── entropy_manager.py  # Entropy system
│   ├── free_energy_manager.py  # Free Energy calculation
│   ├── knowledge_graph.py  # Knowledge graph V2
│   ├── wal_logger.py       # Write-Ahead Logging
│   ├── integrity_tracker.py  # Anti-hallucination
│   └── ...
├── tests/
│   ├── test_mft.py
│   ├── test_fts5.py
│   ├── test_knowledge_graph.py
│   └── ...
├── docs/
│   ├── API.md
│   ├── DEVELOPER.md
│   └── ...
└── README.md
```

---

## 🧪 Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Test Coverage

```bash
pytest tests/ --cov=mfs --cov-report=html
```

### Expected Results

- ✅ **300 tests** passed
- ✅ **66% coverage** (meets 65% requirement)
- ✅ **0 warnings**

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [API.md](docs/API.md) | Complete API reference |
| [DEVELOPER.md](docs/DEVELOPER.md) | Developer guide |
| [INSTALL.md](docs/INSTALL.md) | Installation guide |
| [QUICKSTART.md](docs/QUICKSTART.md) | Quick start tutorial |

---

## 🔒 Privacy & Security

**Important**: This project is designed for **technical demonstration only**. 

- ✅ No personal data is included in the codebase
- ✅ All test data uses generic examples (e.g., "User A", "Test Friend")
- ✅ Configuration files (`.env`, credentials) are gitignored
- ✅ Sensitive operations require explicit user confirmation

**Before deploying to GitHub:**
1. Review all documentation for personal information
2. Remove any real user data from test files
3. Ensure `.gitignore` includes sensitive files
4. Use environment variables for credentials

---

## 🤝 MCP Integration

MFS provides MCP (Model Context Protocol) server for AI agent integration:

```json
{
  "mcpServers": {
    "mfs-memory": {
      "command": "python3",
      "args": ["-m", "mfs.mcp_server"],
      "cwd": "/path/to/MFS-Memory",
      "env": {
        "MFS_DB_PATH": "/path/to/mfs.db"
      }
    }
  }
}
```

### Available Tools

- `mfs_read` - Read memory by path
- `mfs_write` - Create or update memory
- `mfs_search` - Search memories by keyword
- `mfs_list` - List memories by type

---

## 📊 Performance

| Operation | Latency | Throughput |
|-----------|---------|------------|
| **Read** | ~0.00ms | ~10,000 ops/s |
| **Write** | ~0.28ms | ~3,500 ops/s |
| **Search** | ~50ms | ~20 ops/s |

*Measured on standard hardware with 10K+ memories*

---

## 🛠️ Development

### Code Quality

```bash
# Run linter
ruff check mfs/

# Format code
black mfs/

# Run tests
pytest tests/ -v
```

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature

# Commit changes
git add .
git commit -m "feat: add new feature"

# Push and create PR
git push origin feature/your-feature
```

---

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- Inspired by NTFS file system design
- Thermodynamic principles applied to information management
- Built for OpenClaw AI agent framework

---

**Version**: 1.0.0.0  
**Last Updated**: 2026-04-17  
**Maintainer**: [@totwoto02](https://github.com/totwoto02)
