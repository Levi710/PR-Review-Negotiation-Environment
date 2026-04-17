"use client";
import { useState, useCallback, useEffect, useMemo } from "react";
import Sidebar from "@/components/Sidebar";
import TopBar from "@/components/TopBar";
import MetricCards from "@/components/MetricCards";
import DiffView from "@/components/DiffView";
import Timeline from "@/components/Timeline";
import LogBox from "@/components/LogBox";
import { resetEnv, stepEnv, callAgent, configCustom, listTasks, getEnvState } from "@/lib/api";

const FALLBACK_TASKS = [
  { name: "single-pass-review", pr_title: "Fix pagination offset calculation", max_turns: 1 },
  { name: "iterative-negotiation", pr_title: "Add input sanitization to profile update", max_turns: 3 },
  { name: "escalation-judgment", pr_title: "Refactor auth token generation for readability", max_turns: 2 },
  { name: "custom-review", pr_title: "Custom Review Session", max_turns: 3 },
];

function taskMeta(tasks, name) {
  return (tasks || FALLBACK_TASKS).find(t => t.name === name) || FALLBACK_TASKS[0];
}

function extractProposedFix(text = "") {
  const match = text.match(/```(?:python)?\s*([\s\S]*?)\s*```/i);
  return match ? match[1].trim() : null;
}

function defaultWorkspaceMode(taskName, explicitMode) {
  if (explicitMode) return explicitMode;
  return taskName === "custom-review" ? "compose" : "review";
}

export default function Dashboard({
  presets,
  defaultHfToken,
  initialTaskName = "single-pass-review",
  initialWorkspaceMode,
}) {
  const [tasks, setTasks] = useState(FALLBACK_TASKS);
  const [selectedPreset, setSelectedPreset] = useState(0);
  const [customModelId, setCustomModelId] = useState("");
  const [customApiUrl, setCustomApiUrl] = useState("");
  const [customApiKey, setCustomApiKey] = useState(defaultHfToken || "");
  const [taskName, setTaskName] = useState(initialTaskName);
  const [workspaceMode, setWorkspaceMode] = useState(defaultWorkspaceMode(initialTaskName, initialWorkspaceMode));
  const [customTitle, setCustomTitle] = useState("Custom Review Session");
  const [customDesc, setCustomDesc] = useState("User-provided code snippet for review.");
  const [draftCode, setDraftCode] = useState("");
  const [customFixAccepted, setCustomFixAccepted] = useState(false);
  const [copyState, setCopyState] = useState("idle");

  const preset = presets[selectedPreset] || presets[0];
  const isInternal = preset.internal;
  const usingCustomEndpoint = preset.id === "custom";
  const activeModelId = usingCustomEndpoint ? customModelId.trim() : preset.id;
  const activeApiUrl = isInternal ? preset.url : (usingCustomEndpoint ? customApiUrl.trim() : preset.url);
  const activeApiKey = isInternal ? preset.token : customApiKey.trim();
  const modelBlockedReason = useMemo(() => {
    if (!activeModelId) {
      return usingCustomEndpoint
        ? "Enter a model ID in Step 2."
        : "Select a reviewer model in Step 2.";
    }

    if (!activeApiUrl) {
      return usingCustomEndpoint
        ? "Enter an API base URL in Step 2."
        : "Select a provider in Step 2.";
    }

    if (!isInternal && !usingCustomEndpoint && !activeApiKey) {
      return `Enter the ${preset.label} API key in Step 2.`;
    }

    return "";
  }, [activeApiKey, activeApiUrl, activeModelId, isInternal, preset.label, usingCustomEndpoint]);
  const modelConfigured = !modelBlockedReason;

  const [initialized, setInitialized] = useState(false);
  const [initStatus, setInitStatus] = useState("idle");
  const [observation, setObservation] = useState({});
  const [originalCode, setOriginalCode] = useState("");
  const [score, setScore] = useState(0);
  const [turn, setTurn] = useState(0);
  const [maxTurns, setMaxTurns] = useState(taskMeta(FALLBACK_TASKS, initialTaskName)?.max_turns || 3);
  const [done, setDone] = useState(false);
  const [decision, setDecision] = useState("IDLE");
  const [rewards, setRewards] = useState([]);
  const [logs, setLogs] = useState([]);
  const [isThinking, setIsThinking] = useState(false);
  const [error, setError] = useState(null);

  const addLog = useCallback((msg) => {
    setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`]);
  }, []);

  useEffect(() => {
    let active = true;
    listTasks()
      .then(data => {
        if (active && data?.tasks?.length) setTasks(data.tasks);
      })
      .catch(e => {
        if (active) addLog(`Task metadata unavailable: ${e.message}`);
      });
    return () => { active = false; };
  }, [addLog]);

  useEffect(() => {
    setMaxTurns(taskMeta(tasks, taskName)?.max_turns || 3);
  }, [tasks, taskName]);

  useEffect(() => {
    if (copyState !== "copied") return undefined;
    const timer = setTimeout(() => setCopyState("idle"), 2000);
    return () => clearTimeout(timer);
  }, [copyState]);

  const currentTask = useMemo(() => taskMeta(tasks, taskName), [tasks, taskName]);
  const isCustomTask = taskName === "custom-review";
  const showComposer = workspaceMode === "compose";
  const sessionReady = initStatus === "ready";
  const reviewHistory = observation.review_history || [];
  const reviewStarted = reviewHistory.length > 0;
  const reviewBlockedReason = !modelConfigured
    ? modelBlockedReason
    : !sessionReady
      ? "Complete Step 3 to unlock review actions."
      : "";

  const resetWorkspaceState = useCallback((nextTaskName, nextMode = "review") => {
    setTaskName(nextTaskName);
    setWorkspaceMode(nextMode);
    setObservation({});
    setOriginalCode("");
    setCustomFixAccepted(false);
    setCopyState("idle");
    if (nextTaskName !== "custom-review") {
      setDraftCode("");
    }
    setScore(0);
    setTurn(0);
    setMaxTurns(taskMeta(tasks, nextTaskName)?.max_turns || 3);
    setDone(false);
    setDecision("IDLE");
    setRewards([]);
    setInitStatus("idle");
    setInitialized(false);
    setError(null);
  }, [tasks]);

  const openCustomReview = useCallback(() => {
    resetWorkspaceState("custom-review", "compose");
    addLog("Custom review workspace ready. Paste code or drop a file.");
  }, [resetWorkspaceState, addLog]);

  const handleTaskChange = useCallback((nextTask) => {
    if (nextTask === "custom-review") {
      openCustomReview();
      return;
    }

    resetWorkspaceState(nextTask, "review");
    addLog(`Scenario selected: ${taskMeta(tasks, nextTask)?.pr_title || nextTask}`);
  }, [openCustomReview, resetWorkspaceState, addLog, tasks]);

  const syncFromResult = useCallback(async (result, actionDecision) => {
    const state = await getEnvState().catch(() => null);
    setObservation(result.observation);
    setScore(prev => state?.cumulative_reward ?? prev + result.reward);
    setRewards(prev => [...prev, result.reward]);
    setDone(result.done);
    setDecision((actionDecision || "running").toUpperCase());
    setTurn(result.observation.turn);
    setMaxTurns(state?.max_turns || taskMeta(tasks, taskName)?.max_turns || result.observation.turn || 3);
    if (taskName !== "custom-review") {
      setWorkspaceMode("review");
    }
    setInitialized(true);
  }, [tasks, taskName]);

  const getVisualDiff = async (oldCode, newCode) => {
    try {
      const resp = await fetch("/api/diff", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ old_code: oldCode, new_code: newCode }),
      });
      const data = await resp.json();
      return data.diff;
    } catch (e) {
      console.error("Diff generation failed", e);
      return null;
    }
  };

  const handleInit = useCallback(async () => {
    setError(null);

    if (taskName === "custom-review") {
      setWorkspaceMode("compose");
      setInitialized(false);
      setInitStatus("ready");
      setObservation({});
      addLog("Custom review workspace opened.");
      return;
    }

    setInitStatus("loading");
    try {
      const obs = await resetEnv(taskName);
      const state = await getEnvState().catch(() => null);
      const meta = taskMeta(tasks, taskName);
      setObservation(obs);
      setInitialized(true);
      setWorkspaceMode("review");
      setInitStatus("ready");
      setScore(state?.cumulative_reward ?? 0);
      setTurn(obs.turn ?? state?.turn ?? 0);
      setMaxTurns(state?.max_turns || meta?.max_turns || 3);
      setDone(obs.done || false);
      setDecision("RUNNING");
      setRewards([]);
      addLog(`Session started: ${obs.pr_title || taskName}`);
    } catch (e) {
      setError(`Connection failed: ${e.message}`);
      setInitStatus("idle");
    }
  }, [taskName, tasks, addLog]);

  const handleManual = useCallback(async (action) => {
    if (done) return null;
    setError(null);
    try {
      const result = await stepEnv(action);
      await syncFromResult(result, action.decision);
      addLog(`Manual decision submitted: ${action.decision}`);
      return result;
    } catch (e) {
      setError(e.message);
      return null;
    }
  }, [done, syncFromResult, addLog]);

  const handleExecute = useCallback(async () => {
    if (done || isThinking || !modelConfigured || !sessionReady) return;
    setError(null);
    setIsThinking(true);
    addLog("AI reviewing current state...");
    try {
      const action = await callAgent({
        observation,
        modelId: activeModelId,
        apiUrl: activeApiUrl,
        apiKey: activeApiKey,
        preferProposedFix: taskName === "custom-review",
      });
      if (action.decision === "error") throw new Error(action.comment);

      const result = await stepEnv(action);
      let updatedObs = result.observation;

      const fix = action.proposed_fix || extractProposedFix(action.comment);
      if (action.decision === "request_changes" && fix && originalCode) {
        const aiDiff = await getVisualDiff(originalCode, fix);
        if (aiDiff) {
          updatedObs = { ...updatedObs, diff: aiDiff, isAiProposal: true, proposedCode: fix };
          addLog("AI generated a visual proposal.");
        }
        setCustomFixAccepted(false);
        setCopyState("idle");
      }

      await syncFromResult({ ...result, observation: updatedObs }, action.decision);
    } catch (e) {
      setError(e.message);
    } finally {
      setIsThinking(false);
    }
  }, [done, isThinking, modelConfigured, sessionReady, observation, originalCode, activeModelId, activeApiUrl, activeApiKey, addLog, syncFromResult, taskName]);

  const handleApplyFix = useCallback(async () => {
    if (!observation.proposedCode) return;
    addLog("Applying AI fix to custom review code...");
    try {
      await configCustom({ diff: observation.proposedCode, pr_title: customTitle, pr_description: customDesc });
      setOriginalCode(observation.proposedCode);
      setDraftCode(observation.proposedCode);
      setCustomFixAccepted(true);
      setObservation(prev => ({ ...prev, diff: observation.diff, isAiProposal: false }));
      setTaskName("custom-review");
      setWorkspaceMode("compose");
      addLog("Fix applied. Start another custom review round when ready.");
    } catch (e) {
      setError(e.message);
    }
  }, [observation, customTitle, customDesc, addLog]);

  const handleCopyFix = useCallback(async () => {
    const codeToCopy = observation.proposedCode || draftCode;
    if (!codeToCopy?.trim()) return;

    try {
      await navigator.clipboard.writeText(codeToCopy);
      setCopyState("copied");
      addLog("Fix copied to clipboard.");
    } catch (e) {
      setCopyState("error");
      setError(`Copy failed: ${e.message}`);
    }
  }, [observation.proposedCode, draftCode, addLog]);

  const handleCodeSubmit = useCallback(async (code) => {
    if (!modelConfigured || !sessionReady) return;
    setError(null);
    setIsThinking(true);
    setOriginalCode(code);
    setDraftCode(code);
    try {
      await configCustom({ diff: code, pr_title: customTitle, pr_description: customDesc });
      const obs = await resetEnv("custom-review");
      const state = await getEnvState().catch(() => null);
      setTaskName("custom-review");
      setInitialized(true);
      setInitStatus("ready");
      setWorkspaceMode("compose");
      setMaxTurns(state?.max_turns || 3);

      const action = await callAgent({
        observation: obs,
        modelId: activeModelId,
        apiUrl: activeApiUrl,
        apiKey: activeApiKey,
        preferProposedFix: true,
      });
      if (action.decision === "error") throw new Error(action.comment);

      const result = await stepEnv(action);
      let finalObs = result.observation;
      const fix = action.proposed_fix || extractProposedFix(action.comment);
      if (action.decision === "request_changes" && fix) {
        const aiDiff = await getVisualDiff(code, fix);
        if (aiDiff) finalObs = { ...finalObs, diff: aiDiff, isAiProposal: true, proposedCode: fix };
        setDraftCode(fix);
        setCustomFixAccepted(false);
        setCopyState("idle");
        addLog("Reviewer revision inserted into the code editor.");
      }

      setObservation(finalObs);
      setScore(result.reward);
      setTurn(result.observation.turn);
      setDone(result.done);
      setDecision(action.decision.toUpperCase());
      setRewards([result.reward]);
      addLog("Custom review completed first pass.");
    } catch (e) {
      setError(e.message);
    } finally {
      setIsThinking(false);
    }
  }, [customTitle, customDesc, activeModelId, activeApiUrl, activeApiKey, addLog, modelConfigured, sessionReady]);

  const status = showComposer
    ? isCustomTask && reviewStarted
      ? "Ready"
      : "Compose"
    : !initialized
      ? "Offline"
      : done
        ? "Complete"
        : isThinking
          ? "Running"
          : "Active";

  const statusSub = showComposer
    ? !modelConfigured
      ? "Complete Step 2 to unlock the workspace."
      : !sessionReady
        ? "Run Step 3 to unlock the review button."
        : reviewStarted
          ? "Edit your code and run another pass whenever you are ready."
          : "Paste code or drop a file to start a custom review"
    : done
      ? "History saved"
      : isThinking
        ? "Reviewer processing..."
        : initialized
          ? "Awaiting decision"
          : "Backend not connected";

  const title = showComposer
    ? isCustomTask && reviewStarted
      ? `${customTitle} - Editable Workspace`
      : customTitle
    : observation.pr_title || currentTask.pr_title || "PR Review Command Center";

  const subtitle = showComposer
    ? isCustomTask && reviewStarted
      ? "custom-review - Your editor stays open while feedback updates"
      : "custom-review - Follow Steps 1-4 in order"
    : initialized
      ? `${taskName} - Turn ${turn}/${maxTurns}`
      : "Start a session to begin";

  return (
    <div className="dash">
      <Sidebar
        taskName={taskName}
        setTaskName={handleTaskChange}
        tasks={tasks}
        presets={presets}
        selectedPreset={selectedPreset}
        setSelectedPreset={setSelectedPreset}
        customApiUrl={customApiUrl}
        setCustomApiUrl={setCustomApiUrl}
        customModelId={customModelId}
        setCustomModelId={setCustomModelId}
        customApiKey={customApiKey}
        setCustomApiKey={setCustomApiKey}
        isInternal={isInternal}
        onInit={handleInit}
        initStatus={initStatus}
        rewards={rewards}
        customTitle={customTitle}
        setCustomTitle={setCustomTitle}
        customDesc={customDesc}
        setCustomDesc={setCustomDesc}
        modelConfigured={modelConfigured}
        modelBlockedReason={modelBlockedReason}
        showComposer={showComposer || isCustomTask}
        initialized={initialized}
        done={done}
        reviewStarted={reviewStarted}
      />
      <div className="main">
        <TopBar title={title} subtitle={subtitle} decision={decision} />
        <MetricCards
          score={score}
          turn={turn}
          maxTurns={maxTurns}
          status={status}
          statusSub={statusSub}
        />
        <div className="content unified-workspace">
          {error && <div className="status-msg error">{error}</div>}
          <div className="workspace-layout">
            {isCustomTask ? (
              <div className="split-view custom-workspace">
                <div className="split-left">
                  <div className="composer-header">
                    <div>
                      <div className="composer-title">Step 4: Paste Code For Review</div>
                      <div className="composer-subtitle">Your draft stays editable before and after each review pass.</div>
                    </div>
                  </div>
                  <DiffView
                    diff={null}
                    inputMode
                    inputText={draftCode}
                    onInputTextChange={setDraftCode}
                    onCodeSubmit={handleCodeSubmit}
                    isProcessing={isThinking}
                    reviewReady={sessionReady && modelConfigured}
                    blockedReason={reviewBlockedReason}
                  />
                  {observation.proposedCode && (
                    <div className="custom-fix-actions">
                      <div className="custom-fix-header">Step 5: Finalize Suggested Fix</div>
                      <div className="custom-fix-text">
                        Accept keeps the reviewer revision as your current working copy. Copy puts the fix code on your clipboard.
                      </div>
                      <div className="custom-fix-buttons">
                        <button
                          className={`init-btn ${customFixAccepted ? "success" : "active"}`}
                          style={{ width: "auto", paddingInline: "18px" }}
                          onClick={handleApplyFix}
                          disabled={customFixAccepted}
                        >
                          {customFixAccepted ? "Step 5A: Fix Accepted" : "Step 5A: Accept Suggested Fix"}
                        </button>
                        <button
                          className={`init-btn ${copyState === "copied" ? "success" : "secondary"}`}
                          style={{ width: "auto", paddingInline: "18px" }}
                          onClick={handleCopyFix}
                        >
                          {copyState === "copied" ? "Step 5B: Copied" : "Step 5B: Copy Fix Code"}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
                <div className="split-right">
                  {observation.diff && observation.proposedCode && (
                    <>
                      <div className="pane-header">Suggested revision</div>
                      <DiffView
                        diff={observation.diff}
                        isAiProposal={draftCode !== observation.proposedCode}
                        onApplyFix={draftCode !== observation.proposedCode ? handleApplyFix : undefined}
                      />
                    </>
                  )}
                  <div className="pane-header">Review feedback</div>
                  {reviewStarted ? (
                    <Timeline
                      history={reviewHistory}
                      isThinking={isThinking}
                      onExecute={handleExecute}
                      onManual={handleManual}
                      done
                      reviewReady={false}
                      blockedReason=""
                    />
                  ) : (
                    <div className="empty-pane custom-feedback-empty">
                      <div className="empty-pane-inner">
                        <div className="empty-pane-title">Reviewer feedback will appear here</div>
                        <div className="empty-pane-text">Finish Steps 2 and 3, then use Step 4 on the left to review your own code without loading a benchmark diff.</div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : observation.diff && initialized ? (
              <div className="split-view">
                <div className="split-left">
                  <div className="pane-header">Code changes</div>
                  <DiffView
                    diff={observation.diff}
                    isAccepted={done && decision === "APPROVE"}
                    isAiProposal={observation.isAiProposal}
                    onApplyFix={handleApplyFix}
                  />
                </div>
                <div className="split-right">
                  <div className="pane-header">Negotiation timeline</div>
                  <Timeline
                    history={reviewHistory}
                    isThinking={isThinking}
                    onExecute={handleExecute}
                    onManual={handleManual}
                    done={done}
                    reviewReady={sessionReady && modelConfigured}
                    blockedReason={reviewBlockedReason}
                  />
                </div>
              </div>
            ) : (
              <div className="full-width-input">
                <DiffView
                  diff={null}
                  inputMode={false}
                  emptyStateTitle={currentTask.pr_title || "Start a review"}
                  emptyStateMessage="Complete Steps 1-3, then run a benchmark scenario or open the custom code workspace."
                  onOpenComposer={openCustomReview}
                />
              </div>
            )}
          </div>
          <LogBox logs={logs} />
        </div>
      </div>
    </div>
  );
}
