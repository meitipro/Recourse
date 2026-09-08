import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));

const nextConfig = {
  reactStrictMode: true,
  // The feed reads the chain from the server so a browser never talks to the
  // RPC directly. Studio drops connections in bursts and the retry that fixes
  // that lives on the server side.
  experimental: { serverActions: { bodySizeLimit: "1mb" } },
  // The page reads four files from OUTSIDE this directory at request time:
  // the two committed evaluation results, the frozen deployment record and
  // the recorded snapshot the feed falls back to when the testnet has reset. A
  // hosted function ships only what the build traced, and a plain fs.read of
  // ../eval/results.json is invisible to that trace, so without these lines
  // the live site would say "the evaluation has not been run yet" while the
  // repository says 17 of 18. Root at the repository so the paths resolve.
  outputFileTracingRoot: path.join(here, ".."),
  outputFileTracingIncludes: {
    "/": [
      "../eval/results.json",
      "../eval/results-v2.json",
      "../contracts/FROZEN.json",
      "../evidence/snapshot.json",
    ],
    "/case/[id]": ["../contracts/FROZEN.json", "../evidence/snapshot.json"],
    "/api/evidence": ["../contracts/FROZEN.json", "../evidence/snapshot.json"],
  },
};
export default nextConfig;
