# 🔍 PR-Probe

**PR-Probe** is a high-performance auditing tool designed to analyze GitHub Pull Requests for **Compliance** and **Engineering Velocity**. It helps teams ensure that PR templates are being used, approvals are happening before merges, and provides deep insights into delivery speed through industry-standard metrics.

---

## 🌟 Key Features

- **✅ Compliance Auditing**: Automatically checks if PRs use required templates and ensures they are approved by a human before being merged.
- **⚡ Performance Metrics**: 
  - **TAT (Turnaround Time)**: Measures the total time from PR creation to merge.
  - **TTR (Time to 1st Review)**: Measures team responsiveness from creation to the first feedback.
- **📁 Professional Exports**: Generates multi-sheet **Excel (.xlsx)** reports and structured **JSON** data.
- **🎯 Flexible Probing**: Scan entire GitHub Organizations or provide a specific list of repository URLs/names.
- **🚀 Built with `uv`**: Leveraging the fastest Python package manager for zero-config execution.
- **💾 Smart Caching**: Locally caches API responses to save rate limits and speed up repeated runs.

---

## 🚀 Quick Start

### 1. Prerequisites
Ensure you have [uv](https://github.com/astral-sh/uv) installed:
```bash
curl -LsSf https://astral-sh.uv/install.sh | sh
```

### 2. Configuration
Create a `.env` file in the root directory and add your GitHub Personal Access Token (PAT). 
**Note**: The token requires the `repo` scope for private repositories.

```bash
cp .env.example .env
# Edit .env and add:
# GITHUB_TOKEN=your_token_here
```

### 3. Run a Scan
```bash
# Scan an entire organization (last 7 days)
uv run pr-probe --org your-org-name --output both

# Scan specific repositories (comma or space separated)
uv run pr-probe --repos "https://github.com/org/repo1 org/repo2" --output xlsx
```

---

## 📊 Understanding the Metrics

| Metric | Definition | Why it matters? |
| :--- | :--- | :--- |
| **TAT** | **Turnaround Time** | Total time from PR creation to merge. High TAT indicates process bottlenecks. |
| **TTR** | **Time to 1st Review** | Time to the very first comment or approval. Measures team responsiveness. |

*All time-based metrics are reported in a human-readable `Xh:Ym` format (e.g., `2h:30m`).*

---

## 📂 Output Structure

All results are neatly organized in the `reports/` directory, grouped by execution timestamp:

```text
reports/
└── 20260430_183440/
    ├── pr_report.xlsx  <-- Multi-sheet (Audit + Summary)
    └── pr_report.json  <-- Full machine-readable data
```

### Excel Sheet Breakdown:
1.  **Detailed Report**: Line-by-line audit of every PR (Author, Merger, Approver, TAT, TTR).
2.  **Summary Metrics**: Aggregated averages and compliance percentages, both **Overall** and **Per-Repository**.

---

## 🛠️ Advanced Usage

| Flag | Description |
| :--- | :--- |
| `--days <N>` | Look back N days (default: 7). |
| `--output <format>` | Choose `xlsx`, `json`, or `both`. |
| `--no-cache` | Bypass local cache and fetch fresh data from GitHub. |
| `--repos "[list]"` | Support URLs, full names, or short names. |

---

## 📄 License
MIT
