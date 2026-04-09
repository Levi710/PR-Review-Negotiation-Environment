export async function POST(req) {
  try {
    const body = await req.json();
    const backendUrl = process.env.API_BASE_URL || "http://localhost:8000";
    
    const response = await fetch(`${backendUrl}/diff`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    
    const data = await response.json();
    return Response.json(data);
  } catch (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }
}
