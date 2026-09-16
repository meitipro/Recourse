import dns from "node:dns";

// GitHub's raw host answers on IPv6 and some networks route it nowhere, which
// fails the fetch outright; the MCP server in recourse-skill does the same.
dns.setDefaultResultOrder("ipv4first");

export const runtime = "nodejs";
export const revalidate = 3600;

/**
 * /skill.md: the recourse skill at one URL, so an agent can be handed the
 * address instead of a plugin install. No copy lives here. It is the skill
 * repository's own SKILL.md, fetched from its main branch and cached for an
 * hour, so the two can never say different things.
 */

const SOURCE = "https://raw.githubusercontent.com/meitipro/recourse-skill/main/SKILL.md";

export async function GET() {
  try {
    const response = await fetch(SOURCE, { next: { revalidate: 3600 } });
    if (!response.ok) throw new Error(String(response.status));
    return new Response(await response.text(), {
      headers: { "Content-Type": "text/markdown; charset=utf-8", "Cache-Control": "public, max-age=300, s-maxage=3600" },
    });
  } catch {
    return new Response(
      "# Recourse skill\n\nThe skill could not be fetched from its repository just now. It lives at https://github.com/meitipro/recourse-skill/blob/main/SKILL.md\n",
      { status: 503, headers: { "Content-Type": "text/markdown; charset=utf-8" } },
    );
  }
}
