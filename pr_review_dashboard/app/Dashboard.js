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

  // ── Initialize (System Check) ──
  const handleInit = useCallback(async () => {
    setError(null);
    setInitStatus("loading");
    addLog(`System Connection Test: ${activeModelId}`);
    try {
      await resetEnv(taskName);
      setInitialized(true);
      setInitStatus("ready");
      addLog(`SYSTEM READY. Waiting for code input...`);
    } catch (e) {
      setError(`Connection Failed: ${e.message}`);
      setInitStatus("idle");
      addLog(`CONNECTION ERROR: ${e.message}`);
    }
  }, [taskName, activeModelId, addLog]);

  // ── Manual Decision ──
  const handleManual = useCallback(async ({ decision: dec, comment }) => {
    if (done) return;
    setError(null);
    addLog(`User Decision: ${dec}`);
    try {
      const result = await stepEnv({ decision: dec, comment: comment || "Manual verdict." });
      setObservation(result.observation);
      setScore(prev => prev + result.reward);
      setRewards(prev => [...prev, result.reward]);
      setDone(result.done);
      setDecision(dec.toUpperCase());
      if (!result.done) setTurn(prev => prev + 1);
      addLog(`VERDICT APPLIED: reward=${result.reward.toFixed(2)} done=${result.done}`);
    } catch (e) {
      setError(e.message);
      addLog(`VERDICT ERROR: ${e.message}`);
    }
  }, [done, addLog]);

  // ── Execute AI Round ──
  const handleExecute = useCallback(async () => {
    if (done || isThinking) return;
    setError(null);
    setIsThinking(true);
    addLog(`Requesting AI Analysis (${activeModelId})...`);
    try {
      const action = await callAgent({
        observation, modelId: activeModelId, apiUrl: activeApiUrl, apiKey: activeApiKey,
      });
      if (action.decision === "error") throw new Error(action.comment);
      
      addLog(`AI Feedback Received: ${action.decision}`);
      const result = await stepEnv(action);
      setObservation(result.observation);
      setScore(prev => prev + result.reward);
      setRewards(prev => [...prev, result.reward]);
      setDone(result.done);
      setDecision(action.decision.toUpperCase());
      if (!result.done) setTurn(prev => prev + 1);
      addLog(`STEP SUCCESS: reward=${result.reward.toFixed(2)}`);
    } catch (e) {
      setError(e.message);
      addLog(`AI ERROR: ${e.message}`);
    } finally {
      setIsThinking(false);
    }
  }, [done, isThinking, observation, activeModelId, activeApiUrl, activeApiKey, addLog]);

  // ── Handle Code Submission (The One-Push Trigger) ──
  const handleCodeSubmit = useCallback(async (code) => {
    setError(null);
    setIsThinking(true);
    addLog("PHASE 2: Parsing submitted code...");
    try {
      // 1. Configure the scenario
      await configCustom({ diff: code, pr_title: customTitle, pr_description: customDesc });
      
      // 2. Initialize the specific environment
      const obs = await resetEnv("custom-review");
      
      // 3. Reset state for new session
      setObservation(obs);
      setInitialized(true);
      setInitStatus("ready");
      setScore(0);
      setTurn(1);
      setMaxTurns(obs.max_turns || 3);
      setDone(false);
      setDecision("IDLE");
      setRewards([]);
      setTaskName("custom-review");
      
      addLog("CODE LOADED. Auto-triggering AI Review round...");
      
      // 4. AUTO-START THE REVIEW (The real "One-Push")
      const action = await callAgent({
        observation: obs, modelId: activeModelId, apiUrl: activeApiUrl, apiKey: activeApiKey,
      });
      if (action.decision === "error") throw new Error(action.comment);
      
      const result = await stepEnv(action);
      setObservation(result.observation);
      setScore(result.reward);
      setRewards([result.reward]);
      setDone(result.done);
      setDecision(action.decision.toUpperCase());
      addLog(`AI REVIEW COMPLETE. Check results below.`);
    } catch (e) {
      setError(e.message);
      addLog(`SESSION ERROR: ${e.message}`);
    } finally {
      setIsThinking(false);
    }
  }, [customTitle, customDesc, activeModelId, activeApiUrl, activeApiKey, addLog]);

  const epStatus = !initialized ? "Offline" : done ? "Reviewed" : "Active";
  const epSub = !initialized ? "Waiting for system check" : done ? "History saved" : isThinking ? "Reviewer processing..." : "Awaiting decision";
  const prSub = initialized ? `${taskName} · Session Progress` : "Connect to begin";

  // Decision state for TopBar
  const currentDecision = decision;

  return (
    <div className="dash">
      <Sidebar
        taskName={taskName} setTaskName={setTaskName}
        presets={presets}
        selectedPreset={selectedPreset} setSelectedPreset={setSelectedPreset}
        customApiUrl={customApiUrl} setCustomApiUrl={setCustomApiUrl}
        customModelId={customModelId} setCustomModelId={setCustomModelId}
        customApiKey={customApiKey} setCustomApiKey={setCustomApiKey}
        isInternal={isInternal}
        onInit={handleInit}
        initStatus={initStatus}
        rewards={rewards}
        customTitle={customTitle} setCustomTitle={setCustomTitle}
        customDesc={customDesc} setCustomDesc={setCustomDesc}
      />
      <div className="main">
        <TopBar
          title={observation.pr_title || "PR Review Command Center"}
          subtitle={prSub}
          decision={currentDecision}
        />
        <MetricCards score={score} turn={turn} maxTurns={maxTurns} status={epStatus} statusSub={epSub} />
        
        <div className="content unified-workspace">
          {error && <div className="status-msg error">{error}</div>}
          
          <div className="workspace-layout">
            {/* Stage 1: The Input Panel (Visible when no code loaded) */}
            {(!observation.diff || !initialized) ? (
              <div className="full-width-input">
                <DiffView 
                  diff={null} 
                  onCodeSubmit={handleCodeSubmit}
                  isProcessing={isThinking} 
                />
              </div>
            ) : (
              /* Stage 2 & 3: Parallel Review View */
              <div className="split-view">
                <div className="split-left">
                  <div className="pane-header">CODE CHANGES</div>
                  <DiffView 
                    diff={observation.diff} 
                    isAccepted={done && decision === 'APPROVE'}
                  />
                </div>
                <div className="split-right">
                  <div className="pane-header">NEGOTIATION TIMELINE</div>
                  <Timeline 
                    history={observation.review_history || []} 
                    isThinking={isThinking} 
                    onExecute={handleExecute} 
                    onManual={handleManual}
                    done={done} 
                  />
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
