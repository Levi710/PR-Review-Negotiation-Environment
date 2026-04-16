import Dashboard from "../Dashboard";
import { getDashboardConfig } from "@/lib/dashboard-config";

export const dynamic = "force-dynamic";

export default async function CodePage() {
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
