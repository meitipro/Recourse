const nextConfig = {
  reactStrictMode: true,
  // The feed reads the chain from the server so a browser never talks to the
  // RPC directly. Studio drops connections in bursts and the retry that fixes
  // that lives on the server side.
  experimental: { serverActions: { bodySizeLimit: "1mb" } },
};
export default nextConfig;
