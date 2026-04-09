"use client";
import { useState, useCallback, useEffect } from "react";
import Sidebar from "@/components/Sidebar";
import TopBar from "@/components/TopBar";
import MetricCards from "@/components/MetricCards";
import DiffView from "@/components/DiffView";
import Timeline from "@/components/Timeline";
import LogBox from "@/components/LogBox";
import { resetEnv, stepEnv, callAgent, configCustom } from "@/lib/api";

export default function Dashboard({ presets, defaultHfToken }) {
  // ── Config state ──
  const [selectedPreset, setSelectedPreset] = useState(0);
  const [customModelId, setCustomModelId] = useState("");
  const [customApiUrl, setCustomApiUrl] = useState("");
  const [customApiKey, setCustomApiKey] = useState(defaultHfToken || "");
  const [taskName, setTaskName] = useState("single-pass-review");
  const [customTitle, setCustomTitle] = useState("Custom Review Session");
  const [customDesc, setCustomDesc] = useState("User-provided code snippet for review.");

  const preset = presets[selectedPreset] || presets[0];
  const isInternal = preset.internal;
  const activeModelId = preset.id === "custom" ? customModelId : preset.id;
  const activeApiUrl = isInternal ? preset.url : (preset.url || customApiUrl || "https://router.huggingface.co/v1");
  const activeApiKey = isInternal ? preset.token : (customApiKey || defaultHfToken);

  // ── Environment state ──
  const [initialized, setInitialized] = useState(false);
  const [initStatus, setInitStatus] = useState("idle");
  const [observation, setObservation] = useState({});
  const [originalCode, setOriginalCode] = useState(""); // Track the user's base code
  const [score, setScore] = useState(0);
  const [turn, setTurn] = useState(0);
  const [maxTurns, setMaxTurns] = useState(3);
  const [done, setDone] = useState(false);
  const [decision, setDecision] = useState("IDLE");
  const [rewards, setRewards] = useState([]);
  const [logs, setLogs] = useState([]);
  const [isThinking, setIsThinking] = useState(false);
  const [error, setError] = useState(null);

  const addLog = useCallback((msg) => {
    setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`]);
  }, []);

  // ── Helper: Fetch Diff from Backend ──
  const getVisualDiff = async (oldCode, newCode) => {
    try {
      const resp = await fetch("/api/diff", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ old_code: oldCode, new_code: newCode })
      });
      const data = await resp.json();
      return data.diff;
    } catch (e) {
      console.error("Diff generation failed", e);
      return null;
    }
  };

  // ── Helper: Extract Code Block from AI response ──
  const extractProposedFix = (text) => {
    const match = text.match(/```python\n([\s\S]*?)\n```/);
    return match ? match[1] : null;
  };

  // ── Initialize ──
  const handleInit = useCallback(async () => {
    setError(null);
    setInitStatus("loading");
    try {
      await resetEnv(taskName);
      setInitialized(true);
      setInitStatus("ready");
      addLog(`SYSTEM READY. Waiting for code input...`);
    } catch (e) {
      setError(`Connection Failed: ${e.message}`);
      setInitStatus("idle");
    }
  }, [taskName, addLog]);

  // ── Manual Decision ──
  const handleManual = useCallback(async ({ decision: dec, comment }) => {
    if (done) return;
    setError(null);
    try {
      const result = await stepEnv({ decision: dec, comment: comment || "Manual verdict.", issue_category: "none" });
      setObservation(result.observation);
      setScore(prev => prev + result.reward);
      setRewards(prev => [...prev, result.reward]);
      setDone(result.done);
      setDecision(dec.toUpperCase());
      setTurn(result.observation.turn); 
    } catch (e) { setError(e.message); }
  }, [done]);

  // ── Execute AI Round (with Auto-Diff logic) ──
  const handleExecute = useCallback(async () => {
    if (done || isThinking) return;
    setError(null);
    setIsThinking(true);
    addLog(`AI reviewing current state...`);
    try {
      const action = await callAgent({ observation, modelId: activeModelId, apiUrl: activeApiUrl, apiKey: activeApiKey });
      if (action.decision === "error") throw new Error(action.comment);
      
      const result = await stepEnv(action);
      let updatedObs = result.observation;

      // --- AUTO-DIFF ENHANCEMENT ---
      // If AI requested changes and provided a fix, we generate a visual diff automatically!
      if (action.decision === "request_changes") {
        const fix = extractProposedFix(action.comment);
        if (fix && originalCode) {
          const aiDiff = await getVisualDiff(originalCode, fix);
          if (aiDiff) {
            updatedObs = { ...updatedObs, diff: aiDiff, isAiProposal: true, proposedCode: fix };
            addLog("AI generated a visual proposal. View the 'Code Changes' tab.");
          }
        }
      }

      setObservation(updatedObs);
      setScore(prev => prev + result.reward);
      setRewards(prev => [...prev, result.reward]);
      setDone(result.done);
      setDecision(action.decision.toUpperCase());
      setTurn(result.observation.turn);
    } catch (e) { setError(e.message); }
    finally { setIsThinking(false); }
  }, [done, isThinking, observation, originalCode, activeModelId, activeApiUrl, activeApiKey, addLog]);

  // ── Apply AI Suggestion (Zero-effort update) ──
  const handleApplyFix = useCallback(async () => {
    if (!observation.proposedCode) return;
    addLog("Applying AI fix to working code...");
    try {
      // Re-configure the scenario with the new code
      await configCustom({ diff: observation.proposedCode, pr_title: customTitle, pr_description: customDesc });
      // Reset the current view to show the 'Clean' version of the fix
      setOriginalCode(observation.proposedCode);
      setObservation(prev => ({ ...prev, diff: observation.proposedCode, isAiProposal: false }));
      addLog("Fix applied. You can now start another review round if needed.");
    } catch (e) { setError(e.message); }
  }, [observation, customTitle, customDesc, addLog]);

  // ── One-Push Implementation ──
  const handleCodeSubmit = useCallback(async (code) => {
    setError(null);
    setIsThinking(true);
    setOriginalCode(code); // Store the base code
    try {
      await configCustom({ diff: code, pr_title: customTitle, pr_description: customDesc });
      const obs = await resetEnv("custom-review");
      
      const action = await callAgent({ observation: obs, modelId: activeModelId, apiUrl: activeApiUrl, apiKey: activeApiKey });
      
      // --- CRITICAL FIX: Check for error BEFORE submitting to stepEnv ---
      if (action.decision === "error") throw new Error(action.comment);
      
      const result = await stepEnv({
        decision: action.decision,
        comment: action.comment,
        issue_category: action.issue_category || "none"
      });
      
      let finalObs = result.observation;

      // Generate Auto-Diff if first round identifies issues
      if (action.decision === "request_changes") {
        const fix = extractProposedFix(action.comment);
        if (fix) {
          const aiDiff = await getVisualDiff(code, fix);
          if (aiDiff) finalObs = { ...finalObs, diff: aiDiff, isAiProposal: true, proposedCode: fix };
        }
      }

      setObservation(finalObs);
      setInitialized(true); setInitStatus("ready");
      setScore(result.reward); setTurn(result.observation.turn);
      setMaxTurns(obs.max_turns || 3); setDone(false);
      setDecision(action.decision.toUpperCase()); setRewards([result.reward]);
      setTaskName("custom-review");
    } catch (e) { setError(e.message); }
    finally { setIsThinking(false); }
  }, [customTitle, customDesc, activeModelId, activeApiUrl, activeApiKey, addLog]);

  return (
    <div className="dash">
      <Sidebar 
        taskName={taskName} setTaskName={setTaskName} presets={presets}
        selectedPreset={selectedPreset} setSelectedPreset={setSelectedPreset}
        customApiUrl={customApiUrl} setCustomApiUrl={setCustomApiUrl}
        customModelId={customModelId} setCustomModelId={setCustomModelId}
        customApiKey={customApiKey} setCustomApiKey={setCustomApiKey}
        isInternal={isInternal} onInit={handleInit} initStatus={initStatus}
        rewards={rewards} customTitle={customTitle} setCustomTitle={setCustomTitle}
        customDesc={customDesc} setCustomDesc={setCustomDesc}
      />
      <div className="main">
        <TopBar title={observation.pr_title || "PR Review Command Center"} subtitle={initialized ? `${taskName} · Session Progress` : "Connect to begin"} decision={decision} />
        <MetricCards score={score} turn={turn} maxTurns={maxTurns} status={!initialized ? "Offline" : done ? "Reviewed" : "Active"} statusSub={done ? "History saved" : isThinking ? "Reviewer processing..." : "Awaiting decision"} />
        <div className="content unified-workspace">
          {error && <div className="status-msg error">{error}</div>}
          <div className="workspace-layout">
            {(!observation.diff || !initialized) ? (
              <div className="full-width-input">
                <DiffView diff={null} onCodeSubmit={handleCodeSubmit} isProcessing={isThinking} />
              </div>
            ) : (
              <div className="split-view">
                <div className="split-left">
                  <div className="pane-header">CODE CHANGES</div>
                  <DiffView 
                    diff={observation.diff} 
                    isAccepted={done && decision === 'APPROVE'}
                    isAiProposal={observation.isAiProposal}
                    onApplyFix={handleApplyFix}
                  />
                </div>
                <div className="split-right">
                  <div className="pane-header">NEGOTIATION TIMELINE</div>
                  <Timeline history={observation.review_history || []} isThinking={isThinking} onExecute={handleExecute} onManual={handleManual} done={done} />
                </div>
              </div>
            )}
          </div>
          <LogBox logs={logs} />
        </div>
      </div>
    </div>
  );
}
