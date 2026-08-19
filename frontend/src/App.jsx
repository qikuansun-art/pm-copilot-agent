import { useEffect, useRef, useState } from "react";

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
  const [request, setRequest] = useState("");
  const [reply, setReply] = useState("");
  const [task, setTask] = useState(null);
  const [submittedRequest, setSubmittedRequest] = useState("");
  const [submittedAnswer, setSubmittedAnswer] = useState("");
  const [generatedPlan, setGeneratedPlan] = useState(null);
  const [researchPlan, setResearchPlan] = useState(null);
  const [toolCalls, setToolCalls] = useState([]);
  const [evidence, setEvidence] = useState([]);
  const [analysis, setAnalysis] = useState(null);
  const [finalOutput, setFinalOutput] = useState(null);
  const [reviewFeedback, setReviewFeedback] = useState("");
  const [reviewHistory, setReviewHistory] = useState([]);
  const [planVersion, setPlanVersion] = useState(1);
  const [reviewAction, setReviewAction] = useState("");
  const [showAddCondition, setShowAddCondition] = useState(false);
  const [conditionInput, setConditionInput] = useState("");
  const [submittedCondition, setSubmittedCondition] = useState("");
  const [conditionStatus, setConditionStatus] = useState("");
  const [isSubmittingCondition, setIsSubmittingCondition] = useState(false);
  const [isReviewing, setIsReviewing] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmittingAnswer, setIsSubmittingAnswer] = useState(false);
  const [isPlanning, setIsPlanning] = useState(false);
  const [automationStage, setAutomationStage] = useState("");
  const [error, setError] = useState("");
  const [documents, setDocuments] = useState([]);
  const [knowledgeGroups, setKnowledgeGroups] = useState([]);
  const [selectedKnowledgeGroupIds, setSelectedKnowledgeGroupIds] = useState([]);
  const [expandedGroups, setExpandedGroups] = useState(new Set());
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false);
  const [showCreateGroup, setShowCreateGroup] = useState(false);
  const [newGroupName, setNewGroupName] = useState("");
  const [showUploadPanel, setShowUploadPanel] = useState(false);
  const [showUploadCreateGroup, setShowUploadCreateGroup] = useState(false);
  const [uploadGroupName, setUploadGroupName] = useState("");
  const [selectedUploadGroup, setSelectedUploadGroup] = useState("");
  const [selectedUploadFile, setSelectedUploadFile] = useState(null);
  const [movingDocumentId, setMovingDocumentId] = useState(null);
  const [moveTargetGroup, setMoveTargetGroup] = useState("");
  const [isMovingDocument, setIsMovingDocument] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadProgressIndeterminate, setUploadProgressIndeterminate] = useState(false);
  const [uploadFilename, setUploadFilename] = useState("");
  const [uploadError, setUploadError] = useState("");
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [knowledgeError, setKnowledgeError] = useState("");
  const [recentTasks, setRecentTasks] = useState([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const uploadHideTimerRef = useRef(null);
  const uploadFileInputRef = useRef(null);
  const knowledgeInitializedRef = useRef(false);

  const sourceTypeCount = new Set(evidence.map((item) => item.source_type)).size;
  const isBusy = isLoading || isSubmittingAnswer || isPlanning || isReviewing || isSubmittingCondition || Boolean(automationStage);

  useEffect(() => {
    void loadKnowledgeData();
    void loadTaskHistory();
    return () => {
      if (uploadHideTimerRef.current) window.clearTimeout(uploadHideTimerRef.current);
    };
  }, []);

  async function loadKnowledgeData(expandGroupId = null) {
    setIsLoadingDocuments(true);
    setKnowledgeError("");
    try {
      const [documentsResponse, groupsResponse] = await Promise.all([
        fetch(`${API_BASE_URL}/knowledge/documents`),
        fetch(`${API_BASE_URL}/knowledge/groups`),
      ]);
      const [documentsPayload, groupsPayload] = await Promise.all([
        parseResponse(documentsResponse, "加载项目资料"),
        parseResponse(groupsResponse, "加载知识分组"),
      ]);
      const nextDocuments = Array.isArray(documentsPayload) ? documentsPayload : [];
      const nextGroups = Array.isArray(groupsPayload) ? groupsPayload : [];
      setDocuments(nextDocuments);
      setKnowledgeGroups(nextGroups);
      setSelectedKnowledgeGroupIds((current) => current.filter(
        (groupId) => nextGroups.some((group) => group.group_id === groupId),
      ));
      setExpandedGroups((current) => {
        const next = new Set(current);
        if (!knowledgeInitializedRef.current) {
          nextGroups.filter((group) => group.document_count > 0).forEach((group) => next.add(group.group_id));
          if (nextDocuments.some((document) => document.group_id == null)) next.add("ungrouped");
        }
        if (expandGroupId) next.add(expandGroupId);
        return next;
      });
      knowledgeInitializedRef.current = true;
    } catch (requestError) {
      setKnowledgeError(requestError instanceof Error ? requestError.message : "加载项目资料失败。");
    } finally {
      setIsLoadingDocuments(false);
    }
  }

  function toggleKnowledgeGroup(groupId) {
    setExpandedGroups((current) => {
      const next = new Set(current);
      if (next.has(groupId)) next.delete(groupId);
      else next.add(groupId);
      return next;
    });
  }

  function toggleTaskKnowledgeGroup(groupId) {
    setSelectedKnowledgeGroupIds((current) => (
      current.includes(groupId)
        ? current.filter((item) => item !== groupId)
        : [...current, groupId]
    ));
  }

  async function handleCreateGroup() {
    const name = newGroupName.trim();
    if (!name) {
      setKnowledgeError("请填写分组名称。");
      return;
    }
    setKnowledgeError("");
    try {
      const response = await fetch(`${API_BASE_URL}/knowledge/groups`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      await parseResponse(response, "创建知识分组");
      setNewGroupName("");
      setShowCreateGroup(false);
      await loadKnowledgeData();
    } catch (requestError) {
      setKnowledgeError(requestError instanceof Error ? requestError.message : "创建知识分组失败。");
    }
  }

  async function handleCreateUploadGroup() {
    const name = uploadGroupName.trim();
    if (!name) {
      setKnowledgeError("请填写新分组名称。");
      return;
    }
    setKnowledgeError("");
    try {
      const response = await fetch(`${API_BASE_URL}/knowledge/groups`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      const createdGroup = await parseResponse(response, "创建知识分组");
      setSelectedUploadGroup(createdGroup.group_id);
      setUploadGroupName("");
      setShowUploadCreateGroup(false);
      await loadKnowledgeData(createdGroup.group_id);
    } catch (requestError) {
      setKnowledgeError(requestError instanceof Error ? requestError.message : "创建知识分组失败。");
    }
  }

  async function loadTaskHistory() {
    setIsLoadingHistory(true);
    try {
      const response = await fetch(`${API_BASE_URL}/tasks`);
      const payload = await parseResponse(response, "加载历史方案");
      setRecentTasks(Array.isArray(payload) ? payload : []);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "加载历史方案失败。");
    } finally {
      setIsLoadingHistory(false);
    }
  }

  async function handleOpenTask(taskId) {
    if (isBusy) return;
    setError("");
    try {
      const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`);
      const state = await parseResponse(response, "打开历史方案");
      const groupIds = state.task?.knowledge_group_ids || [];
      const groupNames = knowledgeGroups
        .filter((group) => groupIds.includes(group.group_id))
        .map((group) => group.name);
      const questions = (state.messages || [])
        .filter((message) => message.role === "assistant")
        .map((message) => {
          const [question, reason = ""] = message.content.split("\n原因：");
          return { question, reason };
        });
      const userMessages = (state.messages || []).filter((message) => message.role === "user");
      resetTaskState();
      setRequest(state.task.original_request || "");
      setSubmittedRequest(state.task.original_request || "");
      setSubmittedAnswer(userMessages[0]?.content || "");
      setSelectedKnowledgeGroupIds(groupIds);
      setTask({ ...state.task, questions, knowledge_group_names: groupNames });
      setGeneratedPlan(state.plan || null);
      setToolCalls(state.tool_calls || []);
      setEvidence(state.evidence || []);
      setAnalysis(state.analysis || null);
      setFinalOutput(state.final_output || null);
      setReviewHistory(state.review_feedback || []);
      setPlanVersion(state.task?.plan_version || 1);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "打开历史方案失败。");
    }
  }

  function handleUploadFileSelection(event) {
    const file = event.target.files?.[0] || null;
    if (!file) return;
    const normalizedFilename = file.name.toLowerCase();
    if (!normalizedFilename.endsWith(".md") && !normalizedFilename.endsWith(".txt")) {
      setSelectedUploadFile(null);
      setUploadError("仅支持上传 .md 或 .txt 文件。");
      event.target.value = "";
      return;
    }
    setSelectedUploadFile(file);
    setUploadError("");
  }

  function handleDocumentUpload() {
    const file = selectedUploadFile;
    if (!file) return;

    if (uploadHideTimerRef.current) {
      window.clearTimeout(uploadHideTimerRef.current);
      uploadHideTimerRef.current = null;
    }
    setUploadFilename(file.name);
    setUploadProgress(0);
    setUploadProgressIndeterminate(false);
    setUploadError("");
    setUploadSuccess(false);
    setKnowledgeError("");

    const finishWithError = (message) => {
      setUploading(false);
      setUploadProgressIndeterminate(false);
      setUploadSuccess(false);
      setUploadError(message);
    };

    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    if (selectedUploadGroup) formData.append("group_id", selectedUploadGroup);
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE_URL}/knowledge/documents`);
    xhr.timeout = 15000;

    xhr.upload.onprogress = (progressEvent) => {
      if (progressEvent.lengthComputable && progressEvent.total > 0) {
        setUploadProgressIndeterminate(false);
        setUploadProgress(Math.round((progressEvent.loaded / progressEvent.total) * 100));
      } else {
        setUploadProgressIndeterminate(true);
      }
    };

    xhr.upload.onload = () => {
      setUploadProgressIndeterminate(false);
      setUploadProgress(100);
    };

    xhr.onload = () => {
      if (xhr.status < 200 || xhr.status >= 300) {
        let detail = `HTTP ${xhr.status}`;
        try {
          const payload = JSON.parse(xhr.responseText);
          detail = typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail || payload);
        } catch {
          // Keep the HTTP status when the backend did not return JSON.
        }
        finishWithError(detail);
        return;
      }

      let uploadedDocument;
      try {
        uploadedDocument = JSON.parse(xhr.responseText);
      } catch {
        finishWithError("知识库服务返回了无效响应。");
        return;
      }

      setDocuments((current) => [
        ...current.filter((item) => item.document_id !== uploadedDocument.document_id),
        uploadedDocument,
      ]);
      setUploadProgress(100);
      setUploadProgressIndeterminate(false);
      setUploading(false);
      setUploadError("");
      setUploadSuccess(true);
      setSelectedUploadFile(null);
      setShowUploadPanel(false);
      if (uploadFileInputRef.current) uploadFileInputRef.current.value = "";
      void loadKnowledgeData(uploadedDocument.group_id || "ungrouped");
      uploadHideTimerRef.current = window.setTimeout(() => {
        setUploadFilename("");
        setUploadProgress(0);
        setUploadSuccess(false);
        uploadHideTimerRef.current = null;
      }, 1500);
    };

    xhr.onerror = () => {
      finishWithError("无法连接知识库服务，请检查后端是否正常运行。");
    };
    xhr.ontimeout = () => {
      finishWithError("上传超时，请检查后端服务是否正常。");
    };
    xhr.onabort = () => {
      finishWithError("上传已取消。");
    };
    xhr.onloadend = () => {
      setUploading(false);
    };
    xhr.send(formData);
  }

  async function handleDeleteDocument(document) {
    const confirmed = window.confirm(
      `确定删除 ${document.filename} 吗？\n删除后，该文档及其知识片段将无法用于 Agent 分析。`,
    );
    if (!confirmed) return;
    setKnowledgeError("");
    try {
      const response = await fetch(`${API_BASE_URL}/knowledge/documents/${document.document_id}`, { method: "DELETE" });
      await parseResponse(response, "删除文档");
      await loadKnowledgeData();
    } catch (requestError) {
      setKnowledgeError(requestError instanceof Error ? requestError.message : "删除文档失败。");
    }
  }

  async function handleDeleteGroup(group) {
    const confirmed = window.confirm(
      `确定删除分组「${group.name}」吗？\n分组中的文档不会被删除，将移动到未分组。`,
    );
    if (!confirmed) return;
    setKnowledgeError("");
    try {
      const response = await fetch(`${API_BASE_URL}/knowledge/groups/${group.group_id}`, { method: "DELETE" });
      await parseResponse(response, "删除知识分组");
      await loadKnowledgeData("ungrouped");
    } catch (requestError) {
      setKnowledgeError(requestError instanceof Error ? requestError.message : "删除知识分组失败。");
    }
  }

  async function handleMoveDocument(document, targetGroupId) {
    setMoveTargetGroup(targetGroupId);
    setIsMovingDocument(true);
    setKnowledgeError("");
    try {
      const response = await fetch(
        `${API_BASE_URL}/knowledge/documents/${document.document_id}/group`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ group_id: targetGroupId || null }),
        },
      );
      await parseResponse(response, "移动文档");
      setMovingDocumentId(null);
      await loadKnowledgeData(targetGroupId || "ungrouped");
    } catch (requestError) {
      setKnowledgeError(requestError instanceof Error ? requestError.message : "移动文档失败。");
    } finally {
      setIsMovingDocument(false);
    }
  }

  function resetTaskState() {
    setActiveTab("Evidence");
    setReply("");
    setTask(null);
    setSubmittedRequest("");
    setSubmittedAnswer("");
    setGeneratedPlan(null);
    setResearchPlan(null);
    setToolCalls([]);
    setEvidence([]);
    setAnalysis(null);
    setFinalOutput(null);
    setReviewFeedback("");
    setReviewHistory([]);
    setPlanVersion(1);
    setReviewAction("");
    setShowAddCondition(false);
    setConditionInput("");
    setSubmittedCondition("");
    setConditionStatus("");
    setIsSubmittingCondition(false);
    setIsReviewing(false);
    setIsLoading(false);
    setIsSubmittingAnswer(false);
    setIsPlanning(false);
    setAutomationStage("");
    setError("");
  }

  function handleNewTask() {
    if (isBusy) return;
    resetTaskState();
    setRequest("");
    setSelectedKnowledgeGroupIds([]);
  }

  async function parseResponse(response, stageName) {
    if (response.ok) return response.json();
    const payload = await response.json().catch(() => null);
    const detail = payload?.detail || `HTTP ${response.status}`;
    throw new Error(`${stageName}失败：${detail}`);
  }

  function syncPlanForStage(plan, phase) {
    if (!plan?.steps) return plan;

    if (phase === "completed") {
      return {
        ...plan,
        steps: plan.steps.map((step) => ({ ...step, status: "completed" })),
      };
    }

    return {
      ...plan,
      steps: plan.steps.map((step) => {
        const title = step.title || "";
        const isResearch = /资料|调研/.test(title);
        const isAnalysis = /产品分析/.test(title);
        const isDesign = /方案设计|功能|MVP/i.test(title);
        const isFinal = /最终方案/.test(title);

        if (phase === "internal" && isResearch) return { ...step, status: "running" };
        if (phase === "external") {
          if (isResearch) return { ...step, status: "completed" };
          if (isAnalysis) return { ...step, status: "running" };
        }
        if (phase === "analysis") {
          if (isResearch || isAnalysis || isDesign) return { ...step, status: "completed" };
          if (isFinal) return { ...step, status: "running" };
        }
        if (phase === "revision") {
          if (isFinal) return { ...step, status: "running" };
          return { ...step, status: "completed" };
        }
        return step;
      }),
    };
  }

  function syncWorkflowResponse(payload, fallbackPhase) {
    setTask((current) => ({
      ...current,
      current_stage: payload.current_stage,
    }));
    setGeneratedPlan((current) => {
      const nextPlan = payload.plan || current;
      if (payload.current_stage === "COMPLETED") {
        return syncPlanForStage(nextPlan, "completed");
      }
      return payload.plan || syncPlanForStage(current, fallbackPhase);
    });
  }

  async function handleStartAnalysis() {
    if (isBusy) return;
    const normalizedRequest = request.trim();
    if (!normalizedRequest) {
      setError("请先输入需要规划的产品需求。");
      return;
    }

    const selectedGroupNames = knowledgeGroups
      .filter((group) => selectedKnowledgeGroupIds.includes(group.group_id))
      .map((group) => group.name);
    resetTaskState();
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: "产品规划任务",
          request: normalizedRequest,
          knowledge_group_ids: selectedKnowledgeGroupIds,
        }),
      });
      const payload = await parseResponse(response, "需求理解");
      setTask({
        task_id: payload.task_id,
        current_stage: payload.current_stage,
        known_facts: payload.known_facts || [],
        missing_information: payload.missing_information || [],
        questions: payload.questions || [],
        knowledge_group_ids: payload.knowledge_group_ids || selectedKnowledgeGroupIds,
        knowledge_group_names: selectedGroupNames,
        plan_version: payload.plan_version || 1,
      });
      setPlanVersion(payload.plan_version || 1);
      setSubmittedRequest(normalizedRequest);
      if (payload.current_stage === "PLANNING" && !(payload.questions || []).length) {
        await continueAfterClarification(payload.task_id);
      }
      await loadTaskHistory();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "需求理解失败。");
    } finally {
      setIsLoading(false);
    }
  }

  async function runAutomatedWorkflow(taskId) {
    setAutomationStage("research-plan");
    let researchPlanPayload;
    try {
      const researchPlanResponse = await fetch(
        `${API_BASE_URL}/tasks/${taskId}/research/plan`,
        { method: "POST" },
      );
      researchPlanPayload = await parseResponse(researchPlanResponse, "生成调研计划");
      const nextResearchPlan = researchPlanPayload.research_plan;
      if (!nextResearchPlan?.internal_query || !nextResearchPlan?.external_query) {
        throw new Error("Invalid research plan response");
      }
      setResearchPlan(nextResearchPlan);
      syncWorkflowResponse(researchPlanPayload);
    } catch {
      throw new Error("生成调研计划失败，请重试。");
    }

    setAutomationStage("internal");
    const internalResponse = await fetch(
      `${API_BASE_URL}/tasks/${taskId}/research/internal`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: researchPlanPayload.research_plan.internal_query }),
      },
    );
    const internal = await parseResponse(internalResponse, "内部资料检索");
    setToolCalls(internal.tool_calls || []);
    setEvidence(internal.evidence || []);
    syncWorkflowResponse(internal, "internal");

    setAutomationStage("external");
    const externalResponse = await fetch(
      `${API_BASE_URL}/tasks/${taskId}/research/external`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: researchPlanPayload.research_plan.external_query }),
      },
    );
    const external = await parseResponse(externalResponse, "外部行业调研");
    setToolCalls(external.tool_calls || []);
    setEvidence(external.evidence || []);
    syncWorkflowResponse(external, "external");

    setAutomationStage("analysis");
    const analysisResponse = await fetch(
      `${API_BASE_URL}/tasks/${taskId}/analysis`,
      { method: "POST" },
    );
    const analysisPayload = await parseResponse(analysisResponse, "产品分析");
    setAnalysis(analysisPayload.analysis);
    setFinalOutput(analysisPayload.final_output || null);
    setPlanVersion(analysisPayload.plan_version || 1);
    syncWorkflowResponse(analysisPayload, "analysis");
    await loadTaskHistory();
    setAutomationStage("");
  }

  async function handleReview(approved) {
    const feedback = reviewFeedback.trim();
    if (!approved && !feedback) {
      setError("请先填写修改意见。");
      return;
    }
    if (!task?.task_id) return;

    setIsReviewing(true);
    setReviewAction(approved ? "approving" : "revising");
    setError("");
    try {
      const response = await fetch(`${API_BASE_URL}/tasks/${task.task_id}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved, feedback: feedback || null }),
      });
      const payload = await parseResponse(response, "Review");
      setFinalOutput(payload.final_output || null);
      setPlanVersion(payload.plan_version || planVersion);
      setReviewHistory(payload.review_feedback || []);
      if (!approved) setReviewFeedback("");
      syncWorkflowResponse(payload, payload.current_stage === "COMPLETED" ? "completed" : undefined);
      await loadTaskHistory();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Review 请求失败。");
    } finally {
      setIsReviewing(false);
      setReviewAction("");
    }
  }

  async function handleAddConditionSubmit() {
    const feedback = conditionInput.trim();
    if (!feedback) {
      setError("请先填写需要补充的条件。");
      return;
    }
    if (!task?.task_id || task.current_stage !== "COMPLETED") return;

    setIsSubmittingCondition(true);
    setSubmittedCondition(feedback);
    setConditionStatus("adjusting");
    setError("");
    try {
      const response = await fetch(`${API_BASE_URL}/tasks/${task.task_id}/revision`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ feedback }),
      });
      const payload = await parseResponse(response, "添加条件");
      setFinalOutput(payload.final_output || null);
      setPlanVersion(payload.plan_version || planVersion);
      setReviewHistory(payload.review_feedback || []);
      setConditionInput("");
      setShowAddCondition(false);
      setConditionStatus("updated");
      syncWorkflowResponse(payload, "revision");
      await loadTaskHistory();
    } catch (requestError) {
      setConditionStatus("");
      setError(requestError instanceof Error ? requestError.message : "添加条件失败。");
    } finally {
      setIsSubmittingCondition(false);
    }
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
      if (clarification.plan) setGeneratedPlan(clarification.plan);

      await continueAfterClarification(task.task_id);
    } catch (requestError) {
      setAutomationStage("");
      setError(requestError instanceof Error ? requestError.message : "自动执行流程失败。");
    } finally {
      setIsSubmittingAnswer(false);
      setIsPlanning(false);
    }
  }

  async function continueAfterClarification(taskId) {
    setIsPlanning(true);
    const planResponse = await fetch(
      `${API_BASE_URL}/tasks/${taskId}/plan`,
      { method: "POST" },
    );
    const planPayload = await parseResponse(planResponse, "生成产品计划");
    syncWorkflowResponse(planPayload);
    setIsPlanning(false);
    await runAutomatedWorkflow(taskId);
  }

  function renderList(items, emptyText) {
    if (!items?.length) return <div className="workspace-empty">{emptyText}</div>;
    return (
      <ul className="analysis-list">
        {items.map((item, index) => (
          <li key={`${typeof item === "object" ? JSON.stringify(item) : item}-${index}`}>
            {typeof item === "object" ? JSON.stringify(item, null, 2) : item}
          </li>
        ))}
      </ul>
    );
  }

  function renderFinalValue(value, emptyText = "暂无内容") {
    if (Array.isArray(value)) return renderList(value, emptyText);
    if (value && typeof value === "object") {
      return <pre className="final-object">{JSON.stringify(value, null, 2)}</pre>;
    }
    return value ? <p>{value}</p> : <div className="workspace-empty compact">{emptyText}</div>;
  }

  function renderFinalPlan() {
    if (!finalOutput) return <div className="workspace-empty">完成 Human Review 后将在这里生成最终方案。</div>;
    const fields = [
      ["title", "标题"], ["summary", "摘要"], ["problems", "问题"],
      ["target_users", "目标用户"], ["key_scenarios", "关键场景"],
      ["requirements", "需求"], ["solution", "解决方案"],
      ["mvp_scope", "MVP 范围"], ["future_scope", "未来范围"],
      ["risks", "风险"], ["decisions", "决策"],
    ];
    return <div className="final-plan">{fields.map(([key, label]) => (
      <section key={key}><h3>{label}</h3>{renderFinalValue(finalOutput[key])}</section>
    ))}</div>;
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
    return renderFinalPlan();
  }

  const displayedStage = task?.current_stage === "WAITING_REVIEW" ? "WAITING REVIEW" : task?.current_stage || "READY";
  const ungroupedDocuments = documents.filter((document) => document.group_id == null);
  const knowledgeSections = [
    ...knowledgeGroups.map((group) => ({
      ...group,
      documents: documents.filter((document) => document.group_id === group.group_id),
      isUngrouped: false,
    })),
    {
      group_id: "ungrouped",
      name: "未分组",
      document_count: ungroupedDocuments.length,
      documents: ungroupedDocuments,
      isUngrouped: true,
    },
  ];

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-mark">PM</div>
        <div><h1>PM Copilot Agent</h1><p>从模糊需求到可评审产品方案</p></div>
        <div className="topbar-actions">
          <button className="new-task-button" type="button" onClick={handleNewTask} disabled={isBusy}>新建任务</button>
          <div className="status-pill"><span /> {displayedStage}</div>
        </div>
      </header>

      <main>
        <section className="dashboard-grid">
          <aside className="card context-panel">
            <div className="section-heading"><span>PROJECT CONTEXT</span><h2>项目上下文</h2></div>
            <div className="context-block">
              <label>当前任务</label>
              <strong>{task ? task.title : "尚未创建任务"}</strong>
              <p>{task ? `${task.current_stage} · ${task.task_id}` : "输入需求后开始分析"}</p>
              {task && (
                <div className="task-knowledge-reference">
                  <span>参考资料</span>
                  {task.knowledge_group_names?.length
                    ? task.knowledge_group_names.map((name) => <i key={name}>{name}</i>)
                    : <i>全部内部知识</i>}
                </div>
              )}
            </div>
            <div className="context-block task-history">
              <label>最近方案</label>
              {isLoadingHistory && !recentTasks.length && <p className="history-empty">加载中...</p>}
              {!isLoadingHistory && !recentTasks.length && <p className="history-empty">暂无历史方案</p>}
              <div className="history-list">
                {recentTasks.slice(0, 8).map((historyTask) => (
                  <button
                    type="button"
                    className={task?.task_id === historyTask.task_id ? "active" : ""}
                    onClick={() => handleOpenTask(historyTask.task_id)}
                    disabled={isBusy}
                    key={historyTask.task_id}
                  >
                    <strong>{historyTask.title}</strong>
                    <span>{historyTask.current_stage} · V{historyTask.plan_version || 1}</span>
                    <time>{new Date(historyTask.updated_at).toLocaleString("zh-CN")}</time>
                  </button>
                ))}
              </div>
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
            <div className="context-block knowledge-documents">
              <label>项目资料</label>
              <div className="knowledge-tree">
                {isLoadingDocuments && !documents.length && !knowledgeGroups.length && <p className="document-empty">加载中...</p>}
                {knowledgeSections.map((group) => {
                  const expanded = expandedGroups.has(group.group_id);
                  return (
                    <section className="knowledge-group" key={group.group_id}>
                      <div className="knowledge-group-header">
                        <button type="button" className="group-toggle" onClick={() => toggleKnowledgeGroup(group.group_id)}>
                          <span>{expanded ? "▾" : "▸"}</span>
                          <strong>{group.name}</strong>
                          <i>{group.document_count}</i>
                        </button>
                        {!group.isUngrouped && (
                          <button type="button" className="quiet-delete" onClick={() => handleDeleteGroup(group)}>删除</button>
                        )}
                      </div>
                      {expanded && (
                        <div className="group-documents">
                          {!group.documents.length && <p className="document-empty">暂无文档</p>}
                          {group.documents.map((document) => (
                            <article className="document-item" key={document.document_id}>
                              <strong title={document.filename}>{document.filename}</strong>
                              <div>
                                <span>{document.status} · {document.chunk_count} chunks</span>
                                <span className="document-actions">
                                  <button
                                    type="button"
                                    className="quiet-move"
                                    onClick={() => {
                                      setMovingDocumentId(document.document_id);
                                      setMoveTargetGroup(document.group_id || "");
                                    }}
                                  >移动到分组</button>
                                  <button type="button" className="quiet-delete" onClick={() => handleDeleteDocument(document)}>删除</button>
                                </span>
                              </div>
                              {movingDocumentId === document.document_id && (
                                <div className="move-document-control">
                                  <label htmlFor={`move-document-${document.document_id}`}>移动到：</label>
                                  <select
                                    id={`move-document-${document.document_id}`}
                                    value={moveTargetGroup}
                                    onChange={(event) => handleMoveDocument(document, event.target.value)}
                                    disabled={isMovingDocument}
                                  >
                                    <option value="">未分组</option>
                                    {knowledgeGroups.map((knowledgeGroup) => (
                                      <option value={knowledgeGroup.group_id} key={knowledgeGroup.group_id}>{knowledgeGroup.name}</option>
                                    ))}
                                  </select>
                                  <button type="button" onClick={() => setMovingDocumentId(null)} disabled={isMovingDocument}>取消</button>
                                </div>
                              )}
                            </article>
                          ))}
                        </div>
                      )}
                    </section>
                  );
                })}
              </div>

              {showCreateGroup && (
                <div className="knowledge-form">
                  <label htmlFor="knowledge-group-name">分组名称</label>
                  <input id="knowledge-group-name" value={newGroupName} onChange={(event) => setNewGroupName(event.target.value)} placeholder="例如：荒料加工" />
                  <div className="knowledge-form-actions">
                    <button type="button" className="secondary" onClick={() => { setShowCreateGroup(false); setNewGroupName(""); }}>取消</button>
                    <button type="button" onClick={handleCreateGroup}>创建</button>
                  </div>
                </div>
              )}

              {showUploadPanel && (
                <div className="knowledge-form upload-panel">
                  <label htmlFor="upload-group">所属分组</label>
                  <select
                    id="upload-group"
                    value={selectedUploadGroup}
                    onChange={(event) => {
                      if (event.target.value === "__create__") {
                        setShowUploadCreateGroup(true);
                        return;
                      }
                      setSelectedUploadGroup(event.target.value);
                    }}
                    disabled={uploading}
                  >
                    <option value="">未分组</option>
                    {knowledgeGroups.map((group) => <option value={group.group_id} key={group.group_id}>{group.name}</option>)}
                    <option value="__create__">+ 新建分组</option>
                  </select>
                  {showUploadCreateGroup && (
                    <div className="upload-create-group">
                      <label htmlFor="upload-new-group-name">新分组名称</label>
                      <input id="upload-new-group-name" value={uploadGroupName} onChange={(event) => setUploadGroupName(event.target.value)} placeholder="例如：客户调研" disabled={uploading} />
                      <div className="knowledge-form-actions">
                        <button type="button" className="secondary" onClick={() => { setShowUploadCreateGroup(false); setUploadGroupName(""); }}>取消</button>
                        <button type="button" onClick={handleCreateUploadGroup}>创建</button>
                      </div>
                    </div>
                  )}
                  <label>文件</label>
                  <label className="file-picker">
                    <input ref={uploadFileInputRef} type="file" accept=".md,.txt,text/markdown,text/plain" onChange={handleUploadFileSelection} disabled={uploading} />
                    <span>{selectedUploadFile?.name || "选择文件"}</span>
                  </label>
                  {uploadError && !uploadFilename && <p className="form-error">{uploadError}</p>}
                  <div className="knowledge-form-actions">
                    <button type="button" className="secondary" disabled={uploading} onClick={() => { setShowUploadPanel(false); setShowUploadCreateGroup(false); setUploadGroupName(""); setSelectedUploadFile(null); setUploadError(""); }}>取消</button>
                    <button type="button" disabled={!selectedUploadFile || uploading} onClick={handleDocumentUpload}>{uploading ? "上传中..." : "上传"}</button>
                  </div>
                </div>
              )}

              <div className="knowledge-actions">
                <button type="button" onClick={() => { setShowCreateGroup(true); setShowUploadPanel(false); setKnowledgeError(""); }}>+ 新建分组</button>
                <button type="button" onClick={() => { setShowUploadPanel(true); setShowCreateGroup(false); setKnowledgeError(""); }}>+ 上传内部资料</button>
              </div>
              {uploadFilename && (
                <div className={`upload-progress ${uploadSuccess ? "success" : ""} ${uploadError ? "failed" : ""}`}>
                  <strong>
                    {uploading && `正在上传：${uploadFilename}`}
                    {uploadSuccess && "上传成功"}
                    {uploadError && "上传失败"}
                  </strong>
                  <div className="upload-progress-row">
                    <div className={`upload-progress-track ${uploadProgressIndeterminate && uploading ? "indeterminate" : ""}`} aria-hidden="true">
                      <i style={{ width: `${uploadProgress}%` }} />
                    </div>
                    <span>{uploadProgressIndeterminate && uploading ? "正在上传..." : `${uploadProgress}%`}</span>
                  </div>
                  {uploadError && <p role="alert">{uploadError}</p>}
                </div>
              )}
              {knowledgeError && <div className="knowledge-error" role="alert">{knowledgeError}</div>}
            </div>
            <div className="evidence-count">
              <div><strong>{evidence.length}</strong><span>Evidence</span></div>
              <div><strong>{sourceTypeCount}</strong><span>来源类型</span></div>
            </div>
          </aside>

          <section className="card agent-panel">
            <div className="section-heading horizontal">
              <div><span>AGENT WORKSPACE</span><h2>Agent 工作区</h2></div>
              <span className="stage-badge">{displayedStage}</span>
            </div>
            <label className="field-label" htmlFor="request">用户需求</label>
            <textarea
              id="request"
              value={request}
              onChange={(event) => setRequest(event.target.value)}
              placeholder="例如：帮我规划一个石材荒料加工管理功能"
              disabled={isBusy}
            />
            {(!task || task.current_stage === "COMPLETED") && (
              <div className="task-knowledge-selector">
                <div className="task-knowledge-heading">
                  <span>参考项目资料</span>
                  <div>
                    <button type="button" onClick={() => setSelectedKnowledgeGroupIds(knowledgeGroups.map((group) => group.group_id))} disabled={isBusy || !knowledgeGroups.length}>全选</button>
                    <button type="button" onClick={() => setSelectedKnowledgeGroupIds([])} disabled={isBusy || !selectedKnowledgeGroupIds.length}>清空</button>
                  </div>
                </div>
                <div className="task-group-options">
                  {knowledgeGroups.map((group) => (
                    <label className={selectedKnowledgeGroupIds.includes(group.group_id) ? "selected" : ""} key={group.group_id}>
                      <input
                        type="checkbox"
                        checked={selectedKnowledgeGroupIds.includes(group.group_id)}
                        onChange={() => toggleTaskKnowledgeGroup(group.group_id)}
                        disabled={isBusy}
                      />
                      <span>{group.name}</span>
                      <i>{group.document_count}</i>
                    </label>
                  ))}
                  {!knowledgeGroups.length && <p>暂无可选知识分组</p>}
                </div>
                <small>
                  {selectedKnowledgeGroupIds.length
                    ? `本次任务将优先参考 ${selectedKnowledgeGroupIds.length} 个知识分组。`
                    : "未选择时，Agent 将搜索全部内部知识。"}
                </small>
              </div>
            )}
            <div className="conversation">
              {!task && !isLoading && <div className="conversation-empty">输入产品需求，Agent 将从需求理解和澄清开始工作。</div>}
              {isLoading && <div className="conversation-empty">正在理解你的产品需求…</div>}
              {task && (
                <>
                  <div className="message user"><span>你</span><p>{submittedRequest}</p></div>
                  {task.current_stage === "WAITING_CLARIFICATION" && task.questions.length > 0 && (
                    <>
                      <div className="message assistant intro-message"><span>PM</span><p>为了更准确地规划这个产品，我需要先确认几个问题：</p></div>
                      <div className="question-list">
                        {task.questions.map((item, index) => (
                          <div className="question-card" key={`${item.question}-${index}`}>
                            <div className="question-number">{index + 1}</div>
                            <div><strong>{item.question}</strong><p><span>原因</span>{item.reason}</p></div>
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                  {!submittedAnswer && task.current_stage === "WAITING_CLARIFICATION" && task.questions.length > 0 && (
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
                  {submittedCondition && <div className="message user clarification-answer"><span>你</span><p>{submittedCondition}</p></div>}
                  {conditionStatus === "adjusting" && <div className="message assistant progress-message"><span>PM</span><p>已收到新增条件，正在基于当前方案进行调整……</p></div>}
                  {conditionStatus === "updated" && <div className="message assistant success-message"><span>PM</span><p>方案已更新至 V{planVersion}，请 Review 新版本。</p></div>}
                </>
              )}
            </div>
            {error && <div className="error-message" role="alert">{error}</div>}
            {task?.current_stage === "COMPLETED" && <div className="completion-message">方案已完成</div>}
            {!task && <div className="composer start-composer"><button type="button" onClick={handleStartAnalysis} disabled={isBusy}>{isLoading ? "分析中..." : "开始分析"}{!isLoading && <span>→</span>}</button></div>}
            {task?.current_stage === "COMPLETED" && !showAddCondition && (
              <div className="composer start-composer">
                <button type="button" onClick={() => { setShowAddCondition(true); setError(""); }} disabled={isBusy}>添加条件 <span>→</span></button>
              </div>
            )}
            {task?.current_stage === "COMPLETED" && showAddCondition && (
              <div className="add-condition-form">
                <strong>为当前方案补充条件</strong>
                <textarea
                  value={conditionInput}
                  onChange={(event) => setConditionInput(event.target.value)}
                  placeholder="例如：增加仓库管理员角色；第一期不考虑自动换刀；需要支持多工厂……"
                  disabled={isSubmittingCondition}
                />
                <div>
                  <button type="button" className="secondary" onClick={() => { setShowAddCondition(false); setConditionInput(""); }} disabled={isSubmittingCondition}>取消</button>
                  <button type="button" onClick={handleAddConditionSubmit} disabled={isSubmittingCondition}>{isSubmittingCondition ? "提交中..." : "提交条件"}</button>
                </div>
              </div>
            )}
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

        {task?.current_stage === "WAITING_REVIEW" && (
          <section className="review-banner">
            <div className="review-copy">
              <span>HUMAN REVIEW · V{planVersion}</span>
              <h2>{reviewAction === "revising" ? "Agent 正在根据本轮意见修订方案" : reviewHistory.length ? `V${planVersion} 修订完成，等待你的 Review` : "方案已生成，等待你的 Review"}</h2>
              {reviewHistory.length > 0 && (
                <div className="review-history">
                  <strong>历次修改意见</strong>
                  {reviewHistory.map((item) => {
                    const versionTo = item.version_to || item.version;
                    const versionFrom = item.version_from || Math.max(1, versionTo - 1);
                    return (
                      <article key={`${versionTo}-${item.feedback}`}>
                        <b>V{versionFrom} → V{versionTo}</b>
                        <em>{item.revision_type === "added_condition" ? "类型：新增条件" : "类型：Review 修改意见"}</em>
                        <span>{item.revision_type === "added_condition" ? "用户输入" : "修改意见"}</span>
                        <p>{item.feedback}</p>
                        <span>本次调整</span>
                        {item.revision_summary?.length
                          ? <ul>{item.revision_summary.map((summary, index) => <li key={`${summary}-${index}`}>{summary}</li>)}</ul>
                          : <p>历史版本未记录修订摘要。</p>}
                      </article>
                    );
                  })}
                </div>
              )}
            </div>
            <div className="review-form">
              <label htmlFor="review-feedback">本轮修改意见</label>
              <textarea
                id="review-feedback"
                value={reviewFeedback}
                onChange={(event) => setReviewFeedback(event.target.value)}
                placeholder="可以补充对当前方案的修改意见，也可以直接批准。"
                disabled={isReviewing}
              />
              <div className="review-actions">
                <button type="button" onClick={() => handleReview(true)} disabled={isReviewing}>批准方案</button>
                <button className="secondary" type="button" onClick={() => handleReview(false)} disabled={isReviewing}>{reviewAction === "revising" ? "Agent 修订中..." : "提交修改意见"}</button>
              </div>
            </div>
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
