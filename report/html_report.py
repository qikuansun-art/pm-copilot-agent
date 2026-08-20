"""Deterministic standalone HTML report generation."""

from html import escape

from models.state import AgentState
from utils.flow_mermaid import product_flow_to_mermaid


def _text(value: object) -> str:
    """Escape one dynamic value for safe insertion into HTML."""
    return escape(str(value), quote=True)


def _list_section(title: str, items: list[str]) -> str:
    """Render one card containing an escaped string list."""
    content = "".join(f"<li>{_text(item)}</li>" for item in items)
    return f'<section class="card"><h2>{title}</h2><ul>{content}</ul></section>'


def _business_flow_section(state: AgentState) -> str:
    """Render the optional ProductFlow with deterministic Mermaid source."""
    flow = state.product_flow
    if flow is None:
        return ""
    description = (
        f'<p class="flow-description">{_text(flow.description)}</p>'
        if flow.description
        else ""
    )
    mermaid = _text(product_flow_to_mermaid(flow))
    return f"""
<section class="card business-flow">
  <h2>业务流程</h2>
  <h3>{_text(flow.title)}</h3>
  {description}
  <div class="flow-canvas"><pre class="mermaid">{mermaid}</pre></div>
</section>"""


def _revision_section(state: AgentState) -> str:
    """Render compact revision lineage without duplicating full plans."""
    if not state.review_feedback:
        return ""
    entries: list[str] = []
    for item in state.review_feedback:
        version_to = item.version_to or item.version
        version_from = item.version_from or max(1, version_to - 1)
        revision_type = (
            "新增条件" if item.revision_type == "added_condition" else "Review 修改意见"
        )
        summaries = "".join(
            f"<li>{_text(summary)}</li>" for summary in item.revision_summary
        )
        summary_html = f"<ul>{summaries}</ul>" if summaries else ""
        entries.append(
            f"""
<article class="revision-item">
  <div class="revision-heading"><strong>V{version_from} → V{version_to}</strong><span>{revision_type}</span></div>
  <p><b>用户修改意见：</b>{_text(item.feedback)}</p>
  {summary_html}
  <time>{_text(item.created_at)}</time>
</article>"""
        )
    return '<section class="card"><h2>Revision History</h2>' + "".join(entries) + "</section>"


def generate_html_report(state: AgentState) -> str:
    """Generate a complete standalone HTML report from existing state."""
    plan = state.final_output
    if plan is None:
        raise ValueError("Task has no final plan")

    sections = "".join(
        [
            _list_section("核心问题", plan.problems),
            _list_section("目标用户", plan.target_users),
            _list_section("关键场景", plan.key_scenarios),
            _list_section("核心需求", plan.requirements),
            _list_section("解决方案", plan.solution),
            _business_flow_section(state),
            _list_section("MVP 范围", plan.mvp_scope),
            _list_section("后续规划", plan.future_scope),
            _list_section("风险与注意事项", plan.risks),
            _revision_section(state),
        ]
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_text(plan.title)} · 产品方案报告</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: #f4f7fb; color: #26344a; font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", Arial, sans-serif; line-height: 1.7; }}
    main {{ width: min(1100px, calc(100% - 32px)); margin: 36px auto 64px; }}
    .report-header {{ padding: 36px; border-radius: 18px; background: linear-gradient(135deg, #174f9f, #2778df); color: white; box-shadow: 0 18px 45px #1f5da32b; }}
    .report-header h1 {{ margin: 0 0 10px; font-size: clamp(26px, 4vw, 40px); line-height: 1.25; }}
    .report-header p {{ margin: 0; color: #eaf2ff; }}
    .meta {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 22px; }}
    .meta span {{ padding: 5px 10px; border: 1px solid #ffffff42; border-radius: 999px; background: #ffffff17; font-size: 12px; }}
    .card {{ margin-top: 18px; padding: 24px 28px; border: 1px solid #e1e8f1; border-radius: 14px; background: white; box-shadow: 0 8px 24px #29415d0a; }}
    .card h2 {{ margin: 0 0 14px; color: #244a7d; font-size: 20px; }}
    .card h3 {{ margin: -4px 0 8px; font-size: 16px; }}
    ul {{ margin: 0; padding-left: 22px; }}
    li + li {{ margin-top: 7px; }}
    .flow-description {{ margin: 0 0 14px; color: #65758a; }}
    .flow-canvas {{ max-height: 720px; overflow: auto; padding: 16px; border: 1px solid #e4eaf2; border-radius: 10px; background: #fbfcfe; }}
    .mermaid {{ min-width: 560px; margin: 0; text-align: center; }}
    .revision-item {{ padding: 16px 0; border-top: 1px solid #edf1f6; }}
    .revision-item:first-of-type {{ border-top: 0; }}
    .revision-heading {{ display: flex; align-items: center; gap: 10px; }}
    .revision-heading span {{ padding: 3px 8px; border-radius: 999px; background: #edf4ff; color: #3166aa; font-size: 11px; }}
    .revision-item p {{ margin: 8px 0; }}
    .revision-item time {{ color: #8a96a7; font-size: 11px; }}
    @media (max-width: 640px) {{ main {{ width: min(100% - 20px, 1100px); margin-top: 10px; }} .report-header, .card {{ padding: 20px; }} }}
  </style>
</head>
<body>
  <main>
    <header class="report-header">
      <h1>{_text(plan.title)}</h1>
      <p>{_text(plan.summary)}</p>
      <div class="meta">
        <span>版本 V{state.task.plan_version}</span>
        <span>状态 {_text(state.task.current_stage.value)}</span>
        <span>生成时间 {_text(state.task.updated_at)}</span>
      </div>
    </header>
    {sections}
  </main>
  <script type="module">
    import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
    mermaid.initialize({{ startOnLoad: true, securityLevel: "strict", theme: "neutral" }});
  </script>
</body>
</html>"""
