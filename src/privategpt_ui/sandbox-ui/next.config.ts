import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable standalone mode for Docker production builds (future)
  output: process.env.NODE_ENV === 'production' ? 'standalone' : undefined,
  
  // Development proxy to avoid CORS issues
  async rewrites() {
    // Disable rewrites - we'll use absolute URLs
    return []
  },

  // Experimental features for better performance
  experimental: {
    optimizePackageImports: ['lucide-react', 'framer-motion']
  }
};

export default nextConfig;
