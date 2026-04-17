export function getDashboardConfig(env = process.env) {
  const presets = [];

  if (env.gemma4) {
    presets.push({
      label: "Gemma 4 IT (Secure)",
      id: "google/gemma-4-31b-it",
      url: "https://integrate.api.nvidia.com/v1",
      token: env.gemma4,
      internal: true,
    });
  }

  if (env.nemotron3) {
    presets.push({
      label: "Nemotron 3 (Secure)",
      id: "nvidia/nemotron-3-super-120b-a12b",
      url: "https://integrate.api.nvidia.com/v1",
      token: env.nemotron3,
      internal: true,
    });
  }

  presets.push(
    {
      label: "GPT OSS 120B (HF Router)",
      id: "openai/gpt-oss-120b:fastest",
      url: "https://router.huggingface.co/v1",
      token: "",
      internal: false,
    },
    {
      label: "Llama 3.3 70B (Groq)",
      id: "llama-3.3-70b-versatile",
      url: "https://api.groq.com/openai/v1",
      token: "",
      internal: false,
    },
    {
      label: "Custom Endpoint",
      id: "custom",
      url: "",
      token: "",
      internal: false,
    },
  );

  return {
    presets,
    defaultHfToken: env.HF_TOKEN || "",
  };
}
