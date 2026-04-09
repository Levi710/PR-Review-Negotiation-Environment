"use client";

export default function TabBar({ activeTab, setActiveTab }) {
  const tabs = [
    { id: "diff", label: "Diff view" },
    { id: "timeline", label: "Negotiation timeline" },
    { id: "manual", label: "Manual override" },
  ];

  return (
    <div className="tabs">
      {tabs.map(t => (
        <div
          key={t.id}
          className={`tab ${activeTab === t.id ? "active" : ""}`}
          onClick={() => setActiveTab(t.id)}
        >
          {t.label}
        </div>
      ))}
    </div>
  );
}
