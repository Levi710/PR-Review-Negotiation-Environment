/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      // Proxy all /api/env/* requests to the FastAPI backend on port 8000
      { source: "/api/env/:path*", destination: "http://localhost:8000/:path*" },
    ];
  },
};

export default nextConfig;
