"""Deterministic single-file HTML generation from PrototypeSpec V1/V2."""

import json
from html import escape

from models.prototype import PrototypeAction, PrototypeField, PrototypePage, PrototypeSpec


def _text(value: object) -> str:
    return escape(str(value), quote=True)


def _safe_json(value: object) -> str:
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            .replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def _field(field: PrototypeField, prefix: str = "") -> str:
    required = " required" if field.required else ""
    field_id, name, label = _text(prefix + field.id), _text(field.id), _text(field.label)
    if field.field_type == "textarea":
        control = f'<textarea id="{field_id}" name="{name}"{required} placeholder="请输入{label}"></textarea>'
    elif field.field_type == "select":
        options = '<option value="">请选择</option>' + "".join(f'<option value="{_text(x)}">{_text(x)}</option>' for x in field.options)
        control = f'<select id="{field_id}" name="{name}"{required}>{options}</select>'
    else:
        control = f'<input id="{field_id}" name="{name}" type="{field.field_type}"{required} placeholder="请输入{label}">'
    mark = "<em>必填</em>" if field.required else ""
    return f'<label class="form-field" for="{field_id}"><span>{label}{mark}</span>{control}</label>'


def _button(action: PrototypeAction, compact: bool = False) -> str:
    primary = " primary" if action.action_type in {"navigate", "submit_form", "update_status"} else ""
    small = " compact" if compact else ""
    return f'<button type="button" class="prototype-action{primary}{small}" data-action="{_text(action.id)}">{_text(action.label)}</button>'


def _actions(actions: list[PrototypeAction]) -> str:
    return f'<div class="page-actions">{"".join(_button(x) for x in actions)}</div>' if actions else ""


def _cards(page: PrototypePage) -> str:
    if page.cards:
        items = "".join(f'<article><span>{_text(x.label)}</span><strong>{_text(x.value)}</strong><small>{_text(x.description)}</small></article>' for x in page.cards)
        return f'<div class="stats-grid">{items}</div>'
    if page.page_type == "dashboard":
        return '<div class="stats-grid"><article><span>总记录</span><strong>24</strong><small>当前原型示例</small></article><article><span>处理中</span><strong>6</strong><small>状态模拟数据</small></article><article><span>本周更新</span><strong>12</strong><small>最近活动示例</small></article></div>'
    return ""


def _tabs(page: PrototypePage) -> str:
    return ('<div class="prototype-tabs" role="tablist">' + "".join(f'<button type="button" data-tab="{_text(x.id)}">{_text(x.label)}</button>' for x in page.tabs) + '</div>') if page.tabs else ""


def _legacy_table(page: PrototypePage) -> str:
    headers = [x.label for x in page.fields[:4]] or ["编号", "名称", "状态", "更新时间"]
    rows = [[f"{label}示例 {index}" for label in headers] for index in range(1, 4)]
    head = "".join(f"<th>{_text(x)}</th>" for x in headers)
    body = "".join("<tr>" + "".join(f"<td>{_text(x)}</td>" for x in row) + "</tr>" for row in rows)
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def _table(page: PrototypePage, statuses: list[str]) -> str:
    if page.table is None:
        return _legacy_table(page)
    controls = []
    if page.table.search_enabled or any(x.filter_type == "search" for x in page.table.filters):
        controls.append('<label><span>搜索</span><input type="search" data-table-search placeholder="搜索当前列表"></label>')
    for item in page.table.filters:
        if item.filter_type == "search":
            continue
        options = item.options or (statuses if item.filter_type == "status" else [])
        choices = '<option value="">全部</option>' + "".join(f'<option value="{_text(x)}">{_text(x)}</option>' for x in options)
        controls.append(f'<label><span>{_text(item.label)}</span><select data-table-filter="{_text(item.id)}">{choices}</select></label>')
    toolbar = f'<div class="table-controls">{"".join(controls)}</div>' if controls else ""
    head = "".join(f'<th>{_text(x.label)}</th>' for x in page.table.columns) + ("<th>操作</th>" if page.table.row_actions else "")
    return toolbar + f'<div class="table-wrap"><table data-record-table><thead><tr>{head}</tr></thead><tbody data-table-body></tbody></table><div class="table-empty" hidden>没有符合条件的记录</div></div>'


def _page(page: PrototypePage, statuses: list[str]) -> str:
    if page.page_type == "list":
        content = _cards(page) + _tabs(page) + _table(page, statuses) + _actions(page.actions)
    elif page.page_type == "detail":
        content = '<div class="detail-card" data-detail-content></div>' + _actions(page.actions)
    elif page.page_type == "form":
        content = f'<form class="prototype-form" data-page-form novalidate>{"".join(_field(x, page.id + "-") for x in page.fields)}</form>' + _actions(page.actions)
    else:
        content = _cards(page) + _actions(page.actions)
    return f'<section class="prototype-page" data-page="{_text(page.id)}" hidden><header class="page-header"><span>{_text(page.page_type)}</span><h2>{_text(page.title)}</h2><p>{_text(page.description)}</p></header><div class="page-card">{content}</div></section>'


def _panels(spec: PrototypeSpec) -> str:
    result = []
    for panel in spec.panels:
        fields = "".join(_field(x, f"panel-{panel.id}-") for x in panel.fields)
        result.append(f'<div class="panel-overlay" data-panel-overlay="{_text(panel.id)}" aria-hidden="true"><section class="prototype-panel {panel.panel_type}" data-panel="{_text(panel.id)}" role="dialog" aria-modal="true"><header><h3>{_text(panel.title)}</h3><button type="button" data-close-panel aria-label="关闭">×</button></header><form class="prototype-form panel-form" novalidate>{fields}</form>{_actions(panel.actions)}</section></div>')
    result.append('<div id="prototype-modal" class="panel-overlay modal-overlay" aria-hidden="true"><section class="prototype-panel modal" role="dialog" aria-modal="true"><header><h3>确认操作</h3><button type="button" data-close-panel aria-label="关闭">×</button></header><p>请确认是否继续当前操作。</p><div class="page-actions"><button type="button" data-close-panel>取消</button><button type="button" class="prototype-action primary" data-modal-confirm>确认</button></div></section></div>')
    return "".join(result)


def _action_map(spec: PrototypeSpec) -> dict:
    result = {}
    for page in spec.pages:
        for action in page.actions:
            result[action.id] = {"type": action.action_type, "target": action.target, "roles": action.visible_to_roles, "page": page.id}
        if page.table:
            for action in page.table.row_actions:
                result[action.id] = {"type": action.action_type, "target": action.target, "roles": action.visible_to_roles, "page": page.id, "row": True}
    for panel in spec.panels:
        for action in panel.actions:
            result[action.id] = {"type": action.action_type, "target": action.target, "roles": action.visible_to_roles, "panel": panel.id}
    return result


def _records(spec: PrototypeSpec) -> dict:
    result = {}
    for page in spec.pages:
        if page.table is None:
            continue
        rows = []
        for index in range(1, 5):
            row = {"__id": f"{page.id}-{index}"}
            for column in page.table.columns:
                if column.column_type == "status":
                    value = spec.statuses[(index - 1) % len(spec.statuses)] if spec.statuses else f"状态 {index}"
                    row["__status"] = value
                elif column.column_type == "date": value = f"2026-08-{19 + index:02d}"
                elif column.column_type == "number": value = index * 10
                elif any(x in column.field.lower() for x in ("id", "no", "code")): value = f"REC-{index:03d}"
                else: value = f"{column.label}示例 {index}"
                row[column.field] = value
            rows.append(row)
        result[page.id] = rows
    return result


def generate_interactive_prototype(spec: PrototypeSpec) -> str:
    """Generate deterministic standalone HTML without an LLM."""
    nav = "".join(f'<button type="button" data-nav-page="{_text(x.id)}">{_text(x.title)}</button>' for x in spec.pages)
    pages = "".join(_page(x, spec.statuses) for x in spec.pages)
    roles = ""
    if spec.roles:
        options = "".join(f'<option value="{_text(x.id)}">{_text(x.name)}</option>' for x in spec.roles)
        roles = f'<label class="role-switcher"><span>当前角色</span><select id="prototype-role">{options}</select></label>'
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{_text(spec.title)} · 交互原型</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;min-width:980px;background:#f4f7fb;color:#26354b;font-family:"PingFang SC","Microsoft YaHei",Arial,sans-serif}}button,input,textarea,select{{font:inherit}}button{{cursor:pointer}}.app-header{{height:64px;display:flex;align-items:center;justify-content:space-between;padding:0 28px;background:#fff;border-bottom:1px solid #e2e8f1}}.brand{{display:flex;align-items:center;gap:12px}}.brand i{{width:34px;height:34px;display:grid;place-items:center;border-radius:9px;background:#2169d5;color:#fff;font-style:normal;font-weight:800}}.brand strong,.brand small{{display:block}}.brand small{{color:#8996a8}}.role-switcher{{display:flex;align-items:center;gap:9px;font-size:11px}}.role-switcher select{{min-width:140px}}.app-layout{{min-height:calc(100vh - 64px);display:grid;grid-template-columns:230px 1fr}}aside{{padding:22px 14px;background:#fff;border-right:1px solid #e2e8f1}}aside>span{{display:block;margin:0 10px 10px;color:#9aa6b6;font-size:10px}}nav{{display:grid;gap:5px}}nav button{{border:0;border-radius:8px;padding:10px 12px;background:transparent;text-align:left}}nav button.active,nav button:hover{{background:#edf4ff;color:#205fb7;font-weight:700}}main{{width:min(1180px,calc(100% - 48px));margin:auto;padding:34px 0 64px}}.page-header span{{color:#3572ca;font-size:10px;font-weight:800}}.page-header h2{{margin:7px 0 5px}}.page-header p{{margin:0;color:#7a8799}}.page-card{{margin-top:20px;padding:22px;border:1px solid #e0e7f0;border-radius:14px;background:#fff}}.stats-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin-bottom:18px}}.stats-grid article{{padding:18px;border:1px solid #e6ebf2;border-radius:11px}}.stats-grid span,.stats-grid small{{display:block;color:#8491a3}}.stats-grid strong{{display:block;margin:8px 0;font-size:28px}}.prototype-tabs{{display:flex;margin-bottom:16px;border-bottom:1px solid #e3e9f1}}.prototype-tabs button{{border:0;border-bottom:2px solid transparent;padding:9px 13px;background:transparent}}.prototype-tabs button.active{{border-color:#2169d5;color:#2169d5;font-weight:700}}.table-controls{{display:flex;gap:10px;margin-bottom:14px}}.table-controls label{{display:grid;gap:5px;font-size:10px}}input,textarea,select{{width:100%;border:1px solid #d7e0eb;border-radius:8px;padding:10px 11px}}textarea{{min-height:100px}}.table-wrap{{overflow:auto}}table{{width:100%;border-collapse:collapse}}th,td{{padding:12px 14px;border-bottom:1px solid #e8edf3;text-align:left}}th{{background:#f7f9fc;font-size:11px}}tbody tr{{cursor:pointer}}tbody tr:hover{{background:#f8fbff}}.table-empty{{padding:28px;text-align:center}}.status-badge{{display:inline-flex;border-radius:999px;padding:4px 8px;font-size:10px;font-weight:700}}.badge-0{{background:#eaf3ff;color:#276ccc}}.badge-1{{background:#fff4dc;color:#9b6816}}.badge-2{{background:#eaf8f2;color:#16805a}}.badge-3{{background:#f1edff;color:#7352bf}}.detail-card{{border:1px solid #e5ebf2;border-radius:10px;overflow:hidden}}dl{{display:grid;grid-template-columns:1fr 1fr;margin:0}}dl div{{padding:15px 18px;border-bottom:1px solid #edf1f5}}dt{{color:#8793a4;font-size:11px}}dd{{margin:6px 0}}.prototype-form{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}.panel-form{{grid-template-columns:1fr}}.form-field{{display:grid;gap:7px}}.form-field:has(textarea){{grid-column:1/-1}}.form-field em{{margin-left:6px;color:#d34c4c;font-size:9px}}.page-actions,.row-actions{{display:flex;justify-content:flex-end;gap:8px;margin-top:20px}}.row-actions{{margin:0}}.prototype-action{{border:1px solid #d3deeb;border-radius:8px;padding:9px 13px;background:#fff}}.prototype-action.primary{{border-color:#2169d5;background:#2169d5;color:#fff}}.prototype-action.compact{{padding:5px 8px;font-size:10px}}.toast{{position:fixed;z-index:60;right:24px;bottom:24px;padding:12px 16px;border-radius:9px;background:#173a65;color:#fff;opacity:0;pointer-events:none}}.toast.visible{{opacity:1}}.panel-overlay{{position:fixed;z-index:40;inset:0;display:none;align-items:center;justify-content:center;background:#15243b66}}.panel-overlay.is-open{{display:flex}}.prototype-panel{{width:420px;max-height:calc(100vh - 40px);overflow:auto;padding:22px;background:#fff;box-shadow:0 24px 60px #15243b42}}.prototype-panel.modal{{border-radius:13px}}.prototype-panel.drawer{{position:absolute;top:0;right:0;height:100%;max-height:none}}.prototype-panel header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:18px}}.prototype-panel h3{{margin:0}}.prototype-panel header button{{border:0;background:transparent;font-size:22px}}
</style></head><body><header class="app-header"><div class="brand"><i>P</i><div><strong>{_text(spec.title)}</strong><small>{_text(spec.description)}</small></div></div>{roles}</header><div class="app-layout"><aside><span>页面导航</span><nav>{nav}</nav></aside><main>{pages}</main></div><div class="toast" role="status">操作成功</div>{_panels(spec)}
<script>
const prototypeSpec={_safe_json(spec.model_dump(mode="json"))};const actions={_safe_json(_action_map(spec))};const recordsByPage={_safe_json(_records(spec))};
const pageById=Object.fromEntries(prototypeSpec.pages.map(x=>[x.id,x])),panelById=Object.fromEntries(prototypeSpec.panels.map(x=>[x.id,x]));const pageElements=[...document.querySelectorAll('[data-page]')],navButtons=[...document.querySelectorAll('[data-nav-page]')],toast=document.querySelector('.toast');let currentRole=prototypeSpec.default_role||prototypeSpec.roles[0]?.id||null,currentPage=prototypeSpec.default_page,selectedRecord=null,activePanel=null,pendingAction=null,toastTimer;const activeTabs={{}};
function allowed(ids){{return !ids?.length||ids.includes(currentRole)}}function pageVisible(id){{return !!pageById[id]&&allowed(pageById[id].visible_to_roles)}}function badgeClass(value){{let h=0;for(const c of String(value||''))h=((h*31)+c.codePointAt(0))>>>0;return`badge-${{h%4}}`}}function badge(value){{const x=document.createElement('span');x.className=`status-badge ${{badgeClass(value)}}`;x.textContent=value||'-';return x}}function showToast(message){{toast.textContent=message;toast.classList.add('visible');clearTimeout(toastTimer);toastTimer=setTimeout(()=>toast.classList.remove('visible'),1800)}}
function showPage(id){{if(!pageVisible(id))return;currentPage=id;pageElements.forEach(x=>x.hidden=x.dataset.page!==id);navButtons.forEach(x=>x.classList.toggle('active',x.dataset.navPage===id));renderPage(id)}}function switchRole(id){{if(!prototypeSpec.roles.some(x=>x.id===id))return;currentRole=id;const select=document.getElementById('prototype-role');if(select)select.value=id;navButtons.forEach(x=>x.hidden=!pageVisible(x.dataset.navPage));updateActionVisibility();if(!pageVisible(currentPage)){{const first=prototypeSpec.pages.find(x=>pageVisible(x.id));if(first)showPage(first.id)}}else renderPage(currentPage)}}function updateActionVisibility(){{document.querySelectorAll('[data-action]').forEach(x=>x.hidden=!allowed(actions[x.dataset.action]?.roles))}}
function filtered(page){{const root=document.querySelector(`[data-page="${{CSS.escape(page.id)}}"]`);let rows=[...(recordsByPage[page.id]||[])],q=root.querySelector('[data-table-search]')?.value.trim().toLowerCase()||'';if(q)rows=rows.filter(r=>Object.entries(r).filter(([k])=>!k.startsWith('__')).some(([,v])=>String(v).toLowerCase().includes(q)));root.querySelectorAll('[data-table-filter]').forEach(control=>{{if(!control.value)return;const f=page.table.filters.find(x=>x.id===control.dataset.tableFilter),status=page.table.columns.find(x=>x.column_type==='status'),field=f?.filter_type==='status'?status?.field:f?.id;rows=rows.filter(r=>String(r[field]??r.__status??'')===control.value)}});const tab=page.tabs.find(x=>x.id===activeTabs[page.id]);if(tab&&prototypeSpec.statuses.includes(tab.label))rows=rows.filter(r=>r.__status===tab.label);return rows}}
function renderTable(page){{if(!page?.table)return;const root=document.querySelector(`[data-page="${{CSS.escape(page.id)}}"]`),body=root.querySelector('[data-table-body]');body.replaceChildren();const rows=filtered(page);for(const record of rows){{const tr=document.createElement('tr');tr.addEventListener('click',()=>{{selectedRecord=record;renderDetails()}});for(const column of page.table.columns){{const td=document.createElement('td');if(column.column_type==='status')td.append(badge(record[column.field]??record.__status));else td.textContent=record[column.field]??'-';tr.append(td)}}if(page.table.row_actions.length){{const td=document.createElement('td'),group=document.createElement('div');group.className='row-actions';for(const action of page.table.row_actions.filter(x=>allowed(x.visible_to_roles))){{const b=document.createElement('button');b.type='button';b.className='prototype-action compact';b.dataset.action=action.id;b.textContent=action.label;b.addEventListener('click',e=>{{e.stopPropagation();selectedRecord=record;dispatchAction(action.id,b)}});group.append(b)}}td.append(group);tr.append(td)}}body.append(tr)}}root.querySelector('.table-empty').hidden=rows.length>0}}
function renderDetails(){{document.querySelectorAll('[data-detail-content]').forEach(container=>{{container.replaceChildren();const detailPage=pageById[container.closest('[data-page]').dataset.page];let record=selectedRecord||Object.values(recordsByPage).flat()[0];if(!record){{record={{__id:'legacy-detail',__status:'待处理'}};for(const field of detailPage.fields)record[field.id]=`${{field.label}}示例 1`;selectedRecord=record}}const labels=Object.fromEntries(prototypeSpec.pages.flatMap(p=>p.table?.columns||[]).map(c=>[c.field,c.label])),dl=document.createElement('dl');if(!Object.entries(record).some(([k,v])=>!k.startsWith('__')&&v===record.__status)){{const wrap=document.createElement('div'),dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent='当前状态';dd.append(badge(record.__status));wrap.append(dt,dd);dl.append(wrap)}}for(const [key,value]of Object.entries(record).filter(([k])=>!k.startsWith('__'))){{const wrap=document.createElement('div'),dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=labels[key]||key;if(value===record.__status)dd.append(badge(value));else dd.textContent=value;wrap.append(dt,dd);dl.append(wrap)}}container.append(dl)}})}}function renderPage(id){{const page=pageById[id];if(page?.table)renderTable(page);if(page?.page_type==='detail')renderDetails();updateActionVisibility()}}
function openPanel(id,action=null){{closePanel();pendingAction=action;const overlay=id&&panelById[id]?document.querySelector(`[data-panel-overlay="${{CSS.escape(id)}}"]`):document.getElementById('prototype-modal');if(!overlay)return;activePanel=id&&panelById[id]?id:'__generic__';overlay.classList.add('is-open');overlay.setAttribute('aria-hidden','false');updateActionVisibility()}}function openModal(action){{openPanel(action?.target,action||null)}}function closePanel(){{document.querySelectorAll('.panel-overlay.is-open').forEach(x=>{{x.classList.remove('is-open');x.setAttribute('aria-hidden','true')}});activePanel=null;pendingAction=null}}function closeModal(){{closePanel()}}
function transition(actionId){{const rules=prototypeSpec.status_transitions,rule=rules.find(x=>x.action_id===actionId&&selectedRecord?.__status===x.from_status),has=rules.some(x=>x.action_id===actionId);if(!rule){{if(has)showToast('当前状态无法执行此操作');return !has}}selectedRecord.__status=rule.to_status;for(const page of prototypeSpec.pages)for(const c of page.table?.columns.filter(x=>x.column_type==='status')||[])if(c.field in selectedRecord)selectedRecord[c.field]=rule.to_status;for(const id of Object.keys(recordsByPage))renderTable(pageById[id]);renderDetails();showToast(`状态已更新：${{rule.to_status}}`);return true}}
function createRecord(form,target){{const page=pageById[target];if(!page?.table)return null;const data=Object.fromEntries(new FormData(form).entries()),index=(recordsByPage[target]?.length||0)+1,record={{__id:`${{target}}-${{Date.now()}}`}};for(const c of page.table.columns){{if(c.column_type==='status')record[c.field]=prototypeSpec.statuses[0]||'待处理';else if(data[c.field]!=null)record[c.field]=data[c.field];else if(/id|no|code/i.test(c.field))record[c.field]=`REC-${{String(index).padStart(3,'0')}}`;else record[c.field]=data[Object.keys(data)[0]]||`${{c.label}} ${{index}}`}}const status=page.table.columns.find(x=>x.column_type==='status');record.__status=status?record[status.field]:prototypeSpec.statuses[0]||null;(recordsByPage[target]||=[]).push(record);selectedRecord=record;return record}}
function dispatchAction(actionId,button=null){{const action=actions[actionId];if(!action||!allowed(action.roles))return;if(action.type==='navigate'){{showPage(action.target);return}}if(action.type==='open_modal'){{openModal(action);return}}if(action.type==='open_drawer'){{openPanel(action.target,action);return}}if(action.type==='close_modal'){{closePanel();return}}if(action.type==='switch_role'){{switchRole(action.target);return}}if(action.type==='switch_tab'){{activeTabs[currentPage]=action.target;syncTabs(currentPage);renderTable(pageById[currentPage]);return}}if(action.type==='filter'||action.type==='search'){{renderTable(pageById[currentPage]);return}}const form=button?.closest('.prototype-page,.prototype-panel')?.querySelector('form');if(form&&!form.checkValidity()){{form.reportValidity();return}}if(!transition(actionId))return;const hasTransition=prototypeSpec.status_transitions.some(x=>x.action_id===actionId);if(action.type==='submit_form'){{if(!hasTransition&&form&&action.target)createRecord(form,action.target);showToast('提交成功');form?.reset();if(action.target)showPage(action.target)}}else if(action.type==='update_status'&&!hasTransition){{selectedRecord||={{__id:'legacy-detail',__status:'待处理'}};selectedRecord.__status=button?.textContent||'已更新';renderDetails();showToast('状态已更新')}}if(action.panel||activePanel)closePanel()}}
function syncTabs(id){{document.querySelector(`[data-page="${{CSS.escape(id)}}"]`)?.querySelectorAll('[data-tab]').forEach(x=>x.classList.toggle('active',x.dataset.tab===activeTabs[id]))}}function confirmModal(){{closePanel();showToast('操作已确认')}}
document.addEventListener('DOMContentLoaded',()=>{{for(const p of prototypeSpec.pages)if(p.tabs.length)activeTabs[p.id]=p.tabs[0].id;navButtons.forEach(x=>x.addEventListener('click',()=>showPage(x.dataset.navPage)));document.querySelectorAll('[data-action]').forEach(x=>x.addEventListener('click',()=>dispatchAction(x.dataset.action,x)));document.querySelectorAll('[data-table-search],[data-table-filter]').forEach(x=>x.addEventListener('input',()=>renderTable(pageById[x.closest('[data-page]').dataset.page])));document.querySelectorAll('[data-tab]').forEach(x=>x.addEventListener('click',()=>{{const id=x.closest('[data-page]').dataset.page;activeTabs[id]=x.dataset.tab;syncTabs(id);renderTable(pageById[id])}}));document.querySelectorAll('[data-close-panel]').forEach(x=>x.addEventListener('click',closePanel));document.querySelector('[data-modal-confirm]').addEventListener('click',confirmModal);document.querySelectorAll('.panel-overlay').forEach(x=>x.addEventListener('click',e=>{{if(e.target===x)closePanel()}}));document.getElementById('prototype-role')?.addEventListener('change',e=>switchRole(e.target.value));document.addEventListener('keydown',e=>{{if(e.key==='Escape'&&activePanel)closePanel()}});closePanel();if(prototypeSpec.roles.length)switchRole(currentRole);for(const p of prototypeSpec.pages)syncTabs(p.id);const initial=pageVisible(prototypeSpec.default_page)?prototypeSpec.default_page:prototypeSpec.pages.find(x=>pageVisible(x.id))?.id;if(initial)showPage(initial)}});
</script></body></html>"""
