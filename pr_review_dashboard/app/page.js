import Dashboard from "./Dashboard";
import { getDashboardConfig } from "@/lib/dashboard-config";

// CRITICAL: Must be dynamic so env vars (gemma4, nemotron3, HF_TOKEN)
// are read at RUNTIME, not at Docker build time when secrets don't exist.
export const dynamic = "force-dynamic";

export default async function Page() {
  const { presets, defaultHfToken } = getDashboardConfig(process.env);
  return (
    <Dashboard
      presets={presets}
      defaultHfToken={defaultHfToken}
      initialTaskName="custom-review"
      initialWorkspaceMode="compose"
    />
  );
}
