"use client";
import { useState, useCallback } from "react";
import Sidebar from "@/components/Sidebar";
import TopBar from "@/components/TopBar";
import MetricCards from "@/components/MetricCards";
import TabBar from "@/components/TabBar";
import DiffView from "@/components/DiffView";
import Timeline from "@/components/Timeline";
import ManualOverride from "@/components/ManualOverride";
import LogBox from "@/components/LogBox";
import { resetEnv, stepEnv, callAgent } from "@/lib/api";

export default function Dashboard({ presets, defaultHfToken }) {
  // ── Config state ──
  const [selectedPreset, setSelectedPreset] = useState(0);
  const [customModelId, setCustomModelId] = useState("");
  const [customApiUrl, setCustomApiUrl] = useState("");
  const [customApiKey, setCustomApiKey] = useState(defaultHfToken || "");
  const [taskName, setTaskName] = useState("single-pass-review");

  // Derived from selected preset
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
  const [activeTab, setActiveTab] = useState("diff");

  const addLog = useCallback((msg) => {
    setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`]);
  }, []);

  // ── Initialize ──
  const handleInit = useCallback(async () => {
    setError(null);
    setInitStatus("loading");
    addLog(`Resetting: ${taskName}`);
    try {
      const obs = await resetEnv(taskName);
      setObservation(obs);
      setInitialized(true);
      setScore(0);
      setTurn(1);
      setMaxTurns(obs.max_turns || 3);
      setDone(false);
      setDecision("IDLE");
      setRewards([]);
      setInitStatus("ready");
      addLog(`Ready. PR: ${obs.pr_title}`);
    } catch (e) {
      setError(e.message);
      setInitStatus("idle");
      addLog(`ERROR: ${e.message}`);
    }
  }, [taskName, addLog]);

  // ── Execute AI Round ──
  const handleExecute = useCallback(async () => {
    if (done || isThinking) return;
    setError(null);
    setIsThinking(true);
    addLog(`Calling: ${activeModelId}`);
    try {
      const action = await callAgent({
        observation, modelId: activeModelId, apiUrl: activeApiUrl, apiKey: activeApiKey,
      });
      if (action.decision === "error") {
        setError(action.comment);
        addLog(`AI ERROR: ${action.comment}`);
        setIsThinking(false);
        return;
      }
      addLog(`Decision: ${action.decision}`);
      const result = await stepEnv(action);
      setObservation(result.observation);
      setScore(prev => prev + result.reward);
      setRewards(prev => [...prev, result.reward]);
      setDone(result.done);
      setDecision(action.decision.toUpperCase());
      if (!result.done) setTurn(prev => prev + 1);
      addLog(`Step: reward=${result.reward.toFixed(2)} done=${result.done}`);
    } catch (e) {
      setError(e.message);
      addLog(`ERROR: ${e.message}`);
    } finally {
      setIsThinking(false);
    }
  }, [done, isThinking, observation, activeModelId, activeApiUrl, activeApiKey, addLog]);

  // ── Manual Override ──
  const handleManual = useCallback(async ({ decision: dec, comment }) => {
    if (done) return null;
    setError(null);
    addLog(`Manual: ${dec}`);
    try {
      const result = await stepEnv({ decision: dec, comment: comment || "Manual review." });
      setObservation(result.observation);
      setScore(prev => prev + result.reward);
      setRewards(prev => [...prev, result.reward]);
      setDone(result.done);
      setDecision(dec.toUpperCase());
      if (!result.done) setTurn(prev => prev + 1);
      addLog(`Manual: reward=${result.reward.toFixed(2)} done=${result.done}`);
      return result;
    } catch (e) {
      setError(e.message);
      return null;
    }
  }, [done, addLog]);

  const epStatus = !initialized ? "Waiting" : done ? "Complete" : "Running";
  const epSub = !initialized ? "No episode" : done ? "Episode finished" : isThinking ? "AI turn active" : "Ready for input";
  const prSub = initialized ? `${taskName} · Turn ${turn}/${maxTurns}` : "Select a scenario and initialize";

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
      />
      <div className="main">
        <TopBar
          title={observation.pr_title || "PR Review Command Center"}
          subtitle={prSub}
          decision={decision}
        />
        <MetricCards score={score} turn={turn} maxTurns={maxTurns} status={epStatus} statusSub={epSub} />
        <TabBar activeTab={activeTab} setActiveTab={setActiveTab} />
        <div className="content">
          {error && <div className="status-msg error">{error}</div>}
          {activeTab === "diff" && <DiffView diff={observation.diff} />}
          {activeTab === "timeline" && (
            <Timeline history={observation.review_history || []} isThinking={isThinking} onExecute={handleExecute} done={done} />
          )}
          {activeTab === "manual" && (
            <ManualOverride onSubmit={handleManual} disabled={done || !initialized} />
          )}
          <LogBox logs={logs} />
        </div>
      </div>
    </div>
  );
}
