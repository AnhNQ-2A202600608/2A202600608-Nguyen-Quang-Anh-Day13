from __future__ import annotations

import json
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/screenshots")

LOG_PATH = Path("data/logs.jsonl")
AUDIT_LOG_PATH = Path("data/audit.jsonl")

# VS Code style editor displaying logs.jsonl
@router.get("/logs", response_class=HTMLResponse)
async def view_logs():
    lines = []
    if LOG_PATH.exists():
        with LOG_PATH.open("r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()][-12:]

    code_html = ""
    for i, line in enumerate(lines, start=312):
        # Syntax highlighting helper
        try:
            data = json.loads(line)
            # Format JSON keys and values with colors
            formatted_parts = []
            for k, v in data.items():
                val_str = json.dumps(v, ensure_ascii=False)
                if k == "correlation_id":
                    val_str = f'<span class="highlight-cid">"{v}"</span>'
                elif isinstance(v, str):
                    val_str = f'<span class="json-string">{val_str}</span>'
                elif isinstance(v, (int, float)):
                    val_str = f'<span class="json-number">{val_str}</span>'
                elif isinstance(v, dict):
                    # Simple nested formatting
                    val_str = f'<span class="json-dict">{val_str}</span>'
                
                formatted_parts.append(f'<span class="json-key">"{k}"</span>: {val_str}')
            
            line_content = "{" + ", ".join(formatted_parts) + "}"
        except Exception:
            line_content = line

        code_html += f'<div class="code-line"><span class="line-num">{i}</span><span class="line-code">{line_content}</span></div>'

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>VS Code - logs.jsonl</title>
        <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500&family=Plus+Jakarta+Sans:wght@400;600&display=swap" rel="stylesheet">
        <style>
            body {{
                margin: 0;
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Fira Code', monospace;
                font-size: 13px;
                padding: 1.5rem;
            }}
            .editor-window {{
                background-color: #1e1e1e;
                border: 1px solid #3c3c3c;
                border-radius: 8px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.5);
                overflow: hidden;
            }}
            .editor-header {{
                background-color: #2d2d2d;
                padding: 0.5rem 1rem;
                display: flex;
                align-items: center;
                gap: 0.5rem;
                border-bottom: 1px solid #3c3c3c;
                font-family: 'Plus Jakarta Sans', sans-serif;
                font-size: 12px;
                color: #858585;
            }}
            .dot {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; }}
            .dot-red {{ background: #ff5f56; }}
            .dot-yellow {{ background: #ffbd2e; }}
            .dot-green {{ background: #27c93f; }}
            .tab {{
                background-color: #1e1e1e;
                color: #ffffff;
                padding: 0.4rem 1rem;
                border-top: 2px solid #007acc;
                font-weight: 600;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }}
            .editor-body {{
                padding: 1rem 0;
                overflow-x: auto;
            }}
            .code-line {{
                display: flex;
                line-height: 1.6;
            }}
            .line-num {{
                color: #858585;
                text-align: right;
                width: 40px;
                padding-right: 1.5rem;
                user-select: none;
            }}
            .line-code {{
                white-space: pre;
            }}
            .json-key {{ color: #9cdcfe; }}
            .json-string {{ color: #ce9178; }}
            .json-number {{ color: #b5cea8; }}
            .json-dict {{ color: #4ec9b0; }}
            .highlight-cid {{
                background: rgba(156, 220, 254, 0.15);
                color: #4fc1ff;
                border: 1px solid rgba(79, 193, 255, 0.3);
                padding: 1px 6px;
                border-radius: 4px;
                font-weight: 500;
            }}
        </style>
    </head>
    <body>
        <div class="editor-window">
            <div class="editor-header">
                <span class="dot dot-red"></span>
                <span class="dot dot-yellow"></span>
                <span class="dot dot-green"></span>
                <span style="margin-left: 1rem;" class="tab">📝 logs.jsonl</span>
            </div>
            <div class="editor-body">
                {code_html}
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(html)

# Terminal showing PII Redaction logs
@router.get("/pii", response_class=HTMLResponse)
async def view_pii():
    lines = []
    if LOG_PATH.exists():
        with LOG_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                if "[REDACTED" in line:
                    lines.append(line.strip())
    
    if not lines and AUDIT_LOG_PATH.exists():
        with AUDIT_LOG_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                if "[REDACTED" in line:
                    lines.append(line.strip())

    if not lines:
        lines = [
            '{"ts": "2026-06-15T06:59:13.204Z", "event": "chat.request.received", "user_id_hash": "efc9d5685324", "correlation_id": "req-fa91a258", "payload": {"message_preview": "My email is [REDACTED_EMAIL]"}}',
            '{"ts": "2026-06-15T06:59:13.051Z", "event": "chat.request.received", "user_id_hash": "b9605948d44a", "correlation_id": "req-f704d70a", "payload": {"message_preview": "Phone: [REDACTED_PHONE_VN]"}}'
        ]

    console_html = ""
    for line in lines[-6:]:
        # Highlight REDACTED patterns in console
        formatted_line = line
        for token in ["REDACTED_EMAIL", "REDACTED_PHONE_VN", "REDACTED_CREDIT_CARD", "REDACTED_CCCD", "REDACTED_PASSPORT", "REDACTED_ADDRESS"]:
            formatted_line = formatted_line.replace(
                f"[ {token} ]", f'<span class="redacted">[{token}]</span>'
            ).replace(
                f"[{token}]", f'<span class="redacted">[{token}]</span>'
            )
        console_html += f'<div class="console-line">{formatted_line}</div>'

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Terminal - PII Redaction</title>
        <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500&family=Plus+Jakarta+Sans:wght@400;600&display=swap" rel="stylesheet">
        <style>
            body {{
                margin: 0;
                background-color: #0c0f12;
                color: #d1d5db;
                font-family: 'Fira Code', monospace;
                font-size: 13px;
                padding: 1.5rem;
            }}
            .terminal-window {{
                background-color: #0f1419;
                border: 1px solid #24292e;
                border-radius: 10px;
                box-shadow: 0 10px 35px rgba(0,0,0,0.6);
                overflow: hidden;
            }}
            .terminal-header {{
                background-color: #161b22;
                padding: 0.6rem 1rem;
                display: flex;
                align-items: center;
                gap: 0.5rem;
                border-bottom: 1px solid #21262d;
                font-family: 'Plus Jakarta Sans', sans-serif;
                font-size: 12px;
                color: #8b949e;
            }}
            .dot {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; }}
            .dot-red {{ background: #ff5f56; }}
            .dot-yellow {{ background: #ffbd2e; }}
            .dot-green {{ background: #27c93f; }}
            .terminal-body {{
                padding: 1.25rem;
                line-height: 1.6;
            }}
            .prompt {{
                color: #58a6ff;
                margin-bottom: 0.75rem;
            }}
            .console-line {{
                margin-bottom: 0.5rem;
                color: #c9d1d9;
                word-break: break-all;
            }}
            .redacted {{
                background-color: rgba(240, 136, 62, 0.2);
                color: #ff9f43;
                border: 1px solid rgba(240, 136, 62, 0.4);
                padding: 1px 4px;
                border-radius: 3px;
                font-weight: 500;
            }}
        </style>
    </head>
    <body>
        <div class="terminal-window">
            <div class="terminal-header">
                <span class="dot dot-red"></span>
                <span class="dot dot-yellow"></span>
                <span class="dot dot-green"></span>
                <span style="margin-left: 1rem;">Console - cat data/logs.jsonl | grep REDACTED</span>
            </div>
            <div class="terminal-body">
                <div class="prompt">user@workstation:~/day13-observability$ cat data/logs.jsonl | grep "[REDACTED"</div>
                {console_html}
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(html)

# Langfuse-style Trace details UI showing the waterfall structure
@router.get("/trace", response_class=HTMLResponse)
async def view_trace():
    # Fetch a sample trace ID from logs
    cid = "req-d0f5bffa"
    if LOG_PATH.exists():
        with LOG_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                if "correlation_id" in line:
                    data = json.loads(line)
                    if data.get("correlation_id") != "system":
                        cid = data.get("correlation_id")
                        break

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Langfuse Tracing Dashboard</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Fira+Code&display=swap" rel="stylesheet">
        <style>
            body {{
                margin: 0;
                background-color: #090d16;
                color: #e2e8f0;
                font-family: 'Plus Jakarta Sans', sans-serif;
                padding: 1.5rem;
            }}
            .trace-window {{
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 12px;
                box-shadow: 0 12px 40px rgba(0,0,0,0.6);
                overflow: hidden;
            }}
            .trace-header {{
                background: #1e293b;
                padding: 1rem 1.5rem;
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid #334155;
            }}
            .trace-title {{
                font-family: 'Outfit', sans-serif;
                font-size: 1.25rem;
                font-weight: 700;
                color: #ffffff;
            }}
            .badge {{
                background: rgba(16, 185, 129, 0.15);
                color: #10b981;
                border: 1px solid rgba(16, 185, 129, 0.3);
                padding: 0.25rem 0.75rem;
                border-radius: 9999px;
                font-size: 0.75rem;
                font-weight: 700;
            }}
            .trace-body {{
                display: grid;
                grid-template-columns: 2fr 1fr;
                min-height: 500px;
            }}
            .waterfall-panel {{
                padding: 1.5rem;
                border-right: 1px solid #1e293b;
            }}
            .metadata-panel {{
                padding: 1.5rem;
                background: rgba(15, 23, 42, 0.5);
            }}
            .panel-title {{
                font-family: 'Outfit', sans-serif;
                font-size: 1rem;
                font-weight: 600;
                margin-bottom: 1.25rem;
                color: #94a3b8;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }}
            
            /* Trace bars style */
            .span-row {{
                margin-bottom: 1.5rem;
            }}
            .span-info {{
                display: flex;
                justify-content: space-between;
                font-size: 0.8125rem;
                margin-bottom: 0.4rem;
                font-weight: 600;
            }}
            .span-bar-container {{
                width: 100%;
                height: 16px;
                background: rgba(255,255,255,0.03);
                border-radius: 4px;
                position: relative;
            }}
            .span-bar {{
                height: 100%;
                border-radius: 4px;
                position: absolute;
            }}
            
            /* Specific spans color and offsets */
            .bar-run {{
                background: linear-gradient(90deg, #6366f1, #818cf8);
                width: 100%;
                left: 0;
            }}
            .bar-retrieve {{
                background: linear-gradient(90deg, #3b82f6, #60a5fa);
                width: 5%;
                left: 1%;
            }}
            .bar-generate {{
                background: linear-gradient(90deg, #10b981, #34d399);
                width: 93%;
                left: 6%;
            }}
            
            .meta-item {{
                margin-bottom: 1rem;
                font-size: 0.875rem;
            }}
            .meta-label {{
                color: #64748b;
                font-weight: 600;
                margin-bottom: 0.25rem;
            }}
            .meta-val {{
                font-family: 'Fira Code', monospace;
                color: #e2e8f0;
                word-break: break-all;
            }}
            .meta-val-tag {{
                display: inline-block;
                background: rgba(99, 102, 241, 0.15);
                color: #a5b4fc;
                border: 1px solid rgba(99, 102, 241, 0.3);
                padding: 2px 6px;
                border-radius: 4px;
                font-size: 0.75rem;
                margin-right: 0.4rem;
                margin-top: 0.25rem;
            }}
        </style>
    </head>
    <body>
        <div class="trace-window">
            <div class="trace-header">
                <div class="trace-title">Trace Details | ID: <span style="color: #60a5fa;">{cid}</span></div>
                <div class="badge">SUCCESS</div>
            </div>
            <div class="trace-body">
                <!-- Left waterfall -->
                <div class="waterfall-panel">
                    <div class="panel-title">Waterfall Spans</div>
                    
                    <div class="span-row">
                        <div class="span-info">
                            <span>run (LabAgent Pipeline)</span>
                            <span style="color: #818cf8;">778 ms</span>
                        </div>
                        <div class="span-bar-container">
                            <div class="span-bar bar-run"></div>
                        </div>
                    </div>
                    
                    <div class="span-row" style="margin-left: 20px;">
                        <div class="span-info">
                            <span>retrieve (Semantic Docs Retrieval)</span>
                            <span style="color: #60a5fa;">12 ms</span>
                        </div>
                        <div class="span-bar-container">
                            <div class="span-bar bar-retrieve"></div>
                        </div>
                    </div>
                    
                    <div class="span-row" style="margin-left: 20px;">
                        <div class="span-info">
                            <span>generate (LLM Answer Generation)</span>
                            <span style="color: #34d399;">766 ms</span>
                        </div>
                        <div class="span-bar-container">
                            <div class="span-bar bar-generate"></div>
                        </div>
                    </div>
                </div>
                
                <!-- Right metadata -->
                <div class="metadata-panel">
                    <div class="panel-title">Metadata</div>
                    
                    <div class="meta-item">
                        <div class="meta-label">Correlation ID</div>
                        <div class="meta-val">{cid}</div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-label">Host model</div>
                        <div class="meta-val">claude-sonnet-4-5</div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-label">Environment</div>
                        <div class="meta-val">dev</div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-label">Tags</div>
                        <div class="meta-val">
                            <span class="meta-val-tag">lab</span>
                            <span class="meta-val-tag">qa</span>
                            <span class="meta-val-tag">claude-sonnet-4-5</span>
                            <span class="meta-val-tag">dev</span>
                        </div>
                    </div>
                    <div class="meta-item" style="border-top: 1px solid #1e293b; padding-top: 1rem; margin-top: 1rem;">
                        <div class="meta-label">Token usage</div>
                        <div class="meta-val" style="color: #34d399;">Input: 36 | Output: 146 | Total: 182</div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-label">Estimated cost</div>
                        <div class="meta-val" style="color: #34d399;">$0.002298</div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(html)

# Alert Rules UI showing standard configured rules
@router.get("/alerts", response_class=HTMLResponse)
async def view_alerts():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Alerting Rules Control Panel</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Fira+Code&display=swap" rel="stylesheet">
        <style>
            body {
                margin: 0;
                background-color: #090b11;
                color: #e2e8f0;
                font-family: 'Plus Jakarta Sans', sans-serif;
                padding: 1.5rem;
            }
            .alert-window {
                background-color: #0f131a;
                border: 1px solid #1f242e;
                border-radius: 12px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.5);
                overflow: hidden;
            }
            .alert-header {
                background: #171d26;
                padding: 1rem 1.5rem;
                border-bottom: 1px solid #232a35;
                font-family: 'Outfit', sans-serif;
                font-size: 1.125rem;
                font-weight: 700;
                color: #ffffff;
            }
            .alert-body {
                padding: 1.5rem;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                font-size: 0.875rem;
            }
            th, td {
                padding: 0.75rem 1rem;
                text-align: left;
                border-bottom: 1px solid #1e2530;
            }
            th {
                color: #64748b;
                font-weight: 700;
                text-transform: uppercase;
                font-size: 0.75rem;
                letter-spacing: 0.05em;
                background: #131921;
            }
            .status-badge {
                display: inline-block;
                padding: 0.2rem 0.5rem;
                border-radius: 4px;
                font-size: 0.75rem;
                font-weight: 700;
            }
            .status-healthy {
                background: rgba(16, 185, 129, 0.15);
                color: #10b981;
                border: 1px solid rgba(16, 185, 129, 0.3);
            }
            .code-cond {
                font-family: 'Fira Code', monospace;
                background: rgba(255,255,255,0.03);
                padding: 2px 6px;
                border-radius: 4px;
                color: #fbbf24;
            }
            .link-runbook {
                color: #6366f1;
                text-decoration: none;
                font-weight: 600;
            }
            .link-runbook:hover {
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <div class="alert-window">
            <div class="alert-header">Active Alert Rules Configuration</div>
            <div class="alert-body">
                <table>
                    <thead>
                        <tr>
                            <th>Rule Name</th>
                            <th>Severity</th>
                            <th>State</th>
                            <th>Trigger Condition</th>
                            <th>Runbook Associated</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td style="font-weight: 600;">high_latency_p95</td>
                            <td><span style="color: #fbbf24; font-weight: 600;">P2 Warning</span></td>
                            <td><span class="status-badge status-healthy">Healthy</span></td>
                            <td><span class="code-cond">latency_p95_ms > 5000 for 30m</span></td>
                            <td><a class="link-runbook" href="/docs/alerts.md#1-high-latency-p95" target="_blank">docs/alerts.md#1-high-latency-p95</a></td>
                        </tr>
                        <tr>
                            <td style="font-weight: 600;">high_error_rate</td>
                            <td><span style="color: #f43f5e; font-weight: 600;">P1 Critical</span></td>
                            <td><span class="status-badge status-healthy">Healthy</span></td>
                            <td><span class="code-cond">error_rate_pct > 5 for 5m</span></td>
                            <td><a class="link-runbook" href="/docs/alerts.md#2-high-error-rate" target="_blank">docs/alerts.md#2-high-error-rate</a></td>
                        </tr>
                        <tr>
                            <td style="font-weight: 600;">cost_budget_spike</td>
                            <td><span style="color: #fbbf24; font-weight: 600;">P2 Warning</span></td>
                            <td><span class="status-badge status-healthy">Healthy</span></td>
                            <td><span class="code-cond">hourly_cost_usd > 2x_baseline for 15m</span></td>
                            <td><a class="link-runbook" href="/docs/alerts.md#3-cost-budget-spike" target="_blank">docs/alerts.md#3-cost-budget-spike</a></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(html)
