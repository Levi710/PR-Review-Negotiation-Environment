import { cookies } from "next/headers";
import Dashboard from "./Dashboard";

/**
 * Server component that reads environment variables and passes them
 * to the client Dashboard as initial props. This way secrets
 * like gemma4/nemotron3 are detected server-side.
 */
export default async function Page() {
  // Detect which internal models are available
  const presets = [];
  if (process.env.gemma4) {
    presets.push({
      label: "Gemma 4 IT (Secure)",
      id: "google/gemma-4-31b-it",
      url: "https://integrate.api.nvidia.com/v1",
      token: process.env.gemma4,
      internal: true,
    });
  }
  if (process.env.nemotron3) {
    presets.push({
      label: "Nemotron 3 (Secure)",
      id: "nvidia/nemotron-3-super-120b-a12b",
      url: "https://integrate.api.nvidia.com/v1",
      token: process.env.nemotron3,
      internal: true,
    });
  }
  // Always available presets
  presets.push(
    { label: "Qwen 2.5 72B (HF)", id: "Qwen/Qwen2.5-72B-Instruct", url: "https://router.huggingface.co/v1", token: "", internal: false },
    { label: "Llama 3 70B (Groq)", id: "llama3-70b-8192", url: "https://api.groq.com/openai/v1", token: "", internal: false },
    { label: "Custom Endpoint", id: "custom", url: "", token: "", internal: false },
  );

  const defaultHfToken = process.env.HF_TOKEN || "";

  return <Dashboard presets={presets} defaultHfToken={defaultHfToken} />;
}
