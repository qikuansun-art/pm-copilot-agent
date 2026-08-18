import { useState } from "react";

const API_BASE_URL = "http://127.0.0.1:8000";

const workspaceTabs = [
  "Evidence",
  "Problem",
  "Scenario",
  "Requirements",
  "Solution",
  "MVP Scope",
  "Final Plan",
];

function App() {
  const [activeTab, setActiveTab] = useState("Evidence");
  const [request, setRequest] = useState("帮我规划一个 CNC 刀具管理功能");
  const [reply, setReply] = useState("");
  const [task, setTask] = useState(null);
  const [submittedRequest, setSubmittedRequest] = useState("");
  const [submittedAnswer, setSubmittedAnswer] = useState("");
  const [generatedPlan, setGeneratedPlan] = useState(null);
  const [toolCalls, setToolCalls] = useState([]);
  const [evidence, setEvidence] = useState([]);
  const [analysis, setAnalysis] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmittingAnswer, setIsSubmittingAnswer] = useState(false);
  const [isPlanning, setIsPlanning] = useState(false);
  const [automationStage, setAutomationStage] = useState("");
  const [error, setError] = useState("");

  const sourceTypeCount = new Set(evidence.map((item) => item.source_type)).size;
  const isBusy = isLoading || isSubmittingAnswer || isPlanning || Boolean(automationStage);

  async function parseResponse(response, stageName) {
    if (response.ok) return response.json();
    const payload = await response.json().catch(() => null);
    const detail = payload?.detail || `HTTP ${response.status}`;
    throw new Error(`${stageName}失败：${detail}`);
  }

  async function handleStartAnalysis() {
    const normalizedRequest = request.trim();
    if (!normalizedRequest) {
      setError("请先输入需要规划的产品需求。");
      return;
    }

    setIsLoading(true);
    setError("");
    setTask(null);
    setSubmittedAnswer("");
    setGeneratedPlan(null);
    setToolCalls([]);
    setEvidence([]);
    setAnalysis(null);
    setReply("");
    try {
      const response = await fetch(`${API_BASE_URL}/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: "产品规划任务",
          request: normalizedRequest,
        }),
      });
      const payload = await parseResponse(response, "需求理解");
      setTask({
        task_id: payload.task_id,
        current_stage: payload.current_stage,
        known_facts: payload.known_facts || [],
        missing_information: payload.missing_information || [],
        questions: payload.questions || [],
      });
      setSubmittedRequest(normalizedRequest);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "需求理解失败。");
    } finally {
      setIsLoading(false);
    }
  }

  async function runAutomatedWorkflow(taskId) {
    setAutomationStage("internal");
    const internalResponse = await fetch(
      `${API_BASE_URL}/tasks/${taskId}/research/internal`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: "刀具 自动换刀 寿命 工艺" }),
      },
    );
    const internal = await parseResponse(internalResponse, "内部资料检索");
    setToolCalls(internal.tool_calls || []);
    setEvidence(internal.evidence || []);
    setTask((current) => ({ ...current, current_stage: internal.current_stage }));

    setAutomationStage("external");
    const externalResponse = await fetch(
      `${API_BASE_URL}/tasks/${taskId}/research/external`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: "CNC 刀具管理 tool life" }),
      },
    );
    const external = await parseResponse(externalResponse, "外部行业调研");
    setToolCalls(external.tool_calls || []);
    setEvidence(external.evidence || []);
    setTask((current) => ({ ...current, current_stage: external.current_stage }));

    setAutomationStage("analysis");
    const analysisResponse = await fetch(
      `${API_BASE_URL}/tasks/${taskId}/analysis`,
      { method: "POST" },
    );
    const analysisPayload = await parseResponse(analysisResponse, "产品分析");
    setAnalysis(analysisPayload.analysis);
    setTask((current) => ({
      ...current,
      current_stage: analysisPayload.current_stage,
    }));
    setAutomationStage("");
  }

  async function handleClarificationSubmit() {
    const answer = reply.trim();
    if (!answer) {
      setError("请先补充当前业务信息。");
      return;
    }
    if (!task?.task_id) {
      setError("当前任务不存在，请重新开始分析。");
      return;
    }

    setIsSubmittingAnswer(true);
    setError("");
    try {
      const clarificationResponse = await fetch(
        `${API_BASE_URL}/tasks/${task.task_id}/clarification`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ answer }),
        },
      );
      const clarification = await parseResponse(clarificationResponse, "提交补充信息");
      setSubmittedAnswer(answer);
      setReply("");
      setTask((current) => ({
        ...current,
        current_stage: clarification.current_stage,
        known_facts: clarification.known_facts || [],
        missing_information: clarification.missing_information || [],
      }));

      setIsPlanning(true);
      const planResponse = await fetch(
        `${API_BASE_URL}/tasks/${task.task_id}/plan`,
        { method: "POST" },
      );
      const planPayload = await parseResponse(planResponse, "生成产品计划");
      setGeneratedPlan(planPayload.plan);
      setTask((current) => ({ ...current, current_stage: planPayload.current_stage }));
      setIsPlanning(false);

      await runAutomatedWorkflow(task.task_id);
    } catch (requestError) {
      setAutomationStage("");
      setError(requestError instanceof Error ? requestError.message : "自动执行流程失败。");
    } finally {
      setIsSubmittingAnswer(false);
      setIsPlanning(false);
    }
  }

  function renderList(items, emptyText) {
    if (!items?.length) return <div className="workspace-empty">{emptyText}</div>;
    return (
      <ul className="analysis-list">
        {items.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
      </ul>
    );
  }

  function renderWorkspace() {
    if (activeTab === "Evidence") {
      if (!evidence.length) return <div className="workspace-empty">资料调研后将在这里展示 Evidence。</div>;
      return (
        <div className="evidence-grid">
          {evidence.map((item, index) => (
            <article className="evidence-card" key={`${item.source}-${index}`}>
              <div className="evidence-meta">
                <span className={`source-tag ${item.source_type}`}>{item.source_type}</span>
                <span className={`confidence-tag ${item.confidence}`}>{item.confidence}</span>
              </div>
              <p>{item.content}</p>
              <small>{item.source}</small>
            </article>
          ))}
        </div>
      );
    }
    if (activeTab === "Problem") return renderList(analysis?.problems, "产品分析后将在这里展示核心问题。");
    if (activeTab === "Scenario") return renderList(analysis?.scenarios, "产品分析后将在这里展示业务场景。");
    if (activeTab === "Requirements") return renderList(analysis?.requirements, "产品分析后将在这里展示产品需求。");
    if (activeTab === "Solution") return renderList(analysis?.solution, "产品分析后将在这里展示解决方案。");
    if (activeTab === "MVP Scope") {
      return (
        <div className="scope-layout">
          <section><h3>MVP Scope</h3>{renderList(analysis?.mvp_scope, "等待产品分析结果。")}</section>
          <section><h3>Future Scope</h3>{renderList(analysis?.future_scope, "等待产品分析结果。")}</section>
          <section className="risks-section"><h3>Risks</h3>{renderList(analysis?.risks, "等待产品分析结果。")}</section>
        </div>
      );
    }
    return <div className="workspace-empty">完成 Human Review 后将在这里生成最终方案。</div>;
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-mark">PM</div>
        <div><h1>PM Copilot Agent</h1><p>从模糊需求到可评审产品方案</p></div>
        <div className="status-pill"><span /> {task?.current_stage || "READY"}</div>
      </header>

      <main>
        <section className="dashboard-grid">
          <aside className="card context-panel">
            <div className="section-heading"><span>PROJECT CONTEXT</span><h2>项目上下文</h2></div>
            <div className="context-block">
              <label>当前任务</label>
              <strong>{task ? "产品规划任务" : "尚未创建任务"}</strong>
              <p>{task ? `${task.current_stage} · ${task.task_id}` : "输入需求后开始分析"}</p>
            </div>
            <div className="context-block">
              <label>已知事实</label>
              <ul className="fact-list">
                {task?.known_facts.length
                  ? task.known_facts.map((fact) => <li key={fact}>{fact}</li>)
                  : <li className="empty-item">等待 Agent 分析需求</li>}
              </ul>
            </div>
            {task?.missing_information.length > 0 && (
              <div className="context-block">
                <label>待澄清信息</label>
                <ul className="fact-list missing-list">
                  {task.missing_information.map((item) => <li key={item}>{item}</li>)}
                </ul>
              </div>
            )}
            <div className="evidence-count">
              <div><strong>{evidence.length}</strong><span>Evidence</span></div>
              <div><strong>{sourceTypeCount}</strong><span>来源类型</span></div>
            </div>
          </aside>

          <section className="card agent-panel">
            <div className="section-heading horizontal">
              <div><span>AGENT WORKSPACE</span><h2>Agent 工作区</h2></div>
              <span className="stage-badge">{task?.current_stage || "READY"}</span>
            </div>
            <label className="field-label" htmlFor="request">用户需求</label>
            <textarea id="request" value={request} onChange={(event) => setRequest(event.target.value)} />
            <div className="conversation">
              {!task && !isLoading && <div className="conversation-empty">输入产品需求，Agent 将从需求理解和澄清开始工作。</div>}
              {isLoading && <div className="conversation-empty">正在理解你的产品需求…</div>}
              {task && (
                <>
                  <div className="message user"><span>你</span><p>{submittedRequest}</p></div>
                  <div className="message assistant intro-message"><span>PM</span><p>为了更准确地规划这个产品，我需要先确认几个问题：</p></div>
                  <div className="question-list">
                    {task.questions.map((item, index) => (
                      <div className="question-card" key={`${item.question}-${index}`}>
                        <div className="question-number">{index + 1}</div>
                        <div><strong>{item.question}</strong><p><span>原因</span>{item.reason}</p></div>
                      </div>
                    ))}
                  </div>
                  {!submittedAnswer && (
                    <div className="clarification-form">
                      <textarea value={reply} onChange={(event) => setReply(event.target.value)} placeholder="请补充当前业务现状、核心问题和主要使用者……" disabled={isBusy} />
                      <button type="button" onClick={handleClarificationSubmit} disabled={isBusy}>{isSubmittingAnswer ? "提交中..." : "提交补充信息"}</button>
                    </div>
                  )}
                  {submittedAnswer && <div className="message user clarification-answer"><span>你</span><p>{submittedAnswer}</p></div>}
                  {isPlanning && <div className="message assistant progress-message"><span>PM</span><p>Agent 正在制定产品分析计划...</p></div>}
                  {generatedPlan && <div className="message assistant progress-message"><span>PM</span><p>需求已澄清，我已经生成产品分析计划。</p></div>}
                  {automationStage === "internal" && <div className="message assistant progress-message"><span>PM</span><p>正在检索内部知识...</p></div>}
                  {(automationStage === "external" || evidence.some((item) => item.source_type === "web")) && <div className="message assistant progress-message"><span>PM</span><p>内部资料检索完成，正在进行外部行业调研...</p></div>}
                  {(automationStage === "analysis" || analysis) && <div className="message assistant progress-message"><span>PM</span><p>资料调研完成，正在进行产品分析...</p></div>}
                  {analysis && <div className="message assistant success-message"><span>PM</span><p>产品分析完成，请 Review 当前方案。</p></div>}
                </>
              )}
            </div>
            {error && <div className="error-message" role="alert">{error}</div>}
            {!task && <div className="composer start-composer"><button type="button" onClick={handleStartAnalysis} disabled={isLoading}>{isLoading ? "分析中..." : "开始分析"}{!isLoading && <span>→</span>}</button></div>}
          </section>

          <aside className="card plan-panel">
            <div className="section-heading"><span>EXECUTION PLAN</span><h2>Agent Plan</h2></div>
            {generatedPlan ? (
              <>
                <p className="plan-goal">{generatedPlan.goal}</p>
                <div className="plan-list">
                  {generatedPlan.steps.map((step, index) => (
                    <div className={`plan-step ${step.status}`} key={step.id}>
                      <div className="step-marker">{step.status === "completed" ? "✓" : index + 1}</div>
                      <div><strong>{step.title}</strong><span>{step.status}</span></div>
                    </div>
                  ))}
                </div>
                <div className="legend"><span><i className="completed" /> completed</span><span><i className="running" /> running</span><span><i className="pending" /> pending</span></div>
              </>
            ) : (
              <div className="plan-empty"><div className="plan-empty-icon" aria-hidden="true">◇</div><p>任务开始后，Agent 会在这里生成执行计划。</p></div>
            )}
          </aside>
        </section>

        {analysis && (
          <section className="review-banner">
            <div><span>HUMAN REVIEW</span><h2>方案已生成，等待你的 Review</h2></div>
            <button type="button">Review 方案</button>
          </section>
        )}

        <section className="card workspace">
          <div className="workspace-header">
            <div className="section-heading"><span>OUTPUT</span><h2>Workspace</h2></div>
            <span className="autosave">{toolCalls.length} 次工具调用</span>
          </div>
          <div className="tabs" role="tablist">
            {workspaceTabs.map((tab) => (
              <button type="button" role="tab" aria-selected={activeTab === tab} className={activeTab === tab ? "active" : ""} onClick={() => setActiveTab(tab)} key={tab}>{tab}</button>
            ))}
          </div>
          <div className="workspace-content">{renderWorkspace()}</div>
        </section>
      </main>
    </div>
  );
}

export default App;
