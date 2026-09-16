/**
 * Writing a dispute cycle to Studio Next from TypeScript, one path for both
 * tiers of /app: the server, signing with a throwaway account that exists for
 * one run, and the browser, signing through the visitor's wallet.
 *
 * Nothing here chooses a network or an address. The caller passes the
 * deployment the page read from contracts/FROZEN.json, so this file holds no
 * second copy of either.
 *
 * It is the TypeScript half of shared/chain.py and keeps that file's measured
 * rules:
 *
 *   - Every write on consensus v0.6 carries a fee deposit, estimated from
 *     Studio's own simulation of the call. What consensus does not spend comes
 *     back at finality.
 *   - open_dispute emits adjudicate, and adjudicate emits settle when it
 *     finishes. Studio's estimate funds the first message and nothing below
 *     it, and a child with no allocation fails "fee no_matching_allocation".
 *     So settle is added as a child of adjudicate's allocation, the parent's
 *     budget grows by the child's, and the estimate is taken again
 *     (chain.py CASCADES and _cascade).
 *   - A decided transaction is not a successful one: a refusal is decided too.
 *     Success is lifecycle outcome accepted and execution FINISHED_WITH_RETURN.
 */

import {
  MESSAGE_ALLOCATION_ROOT_PARENT_INDEX,
  createClient,
  deriveInternalMessageCallKey,
} from "genlayer-js";
import { studioDevnet } from "genlayer-js/chains";

/* eslint-disable @typescript-eslint/no-explicit-any */

export type Where = { chainId: number; rpc: string; explorer: string; escrow: string; dispute: string };

export const GEN = 10n ** 18n;

/** Internal messages in genlayer-js's MessageType enum: External 0, Internal 1. */
const INTERNAL = 1;

/** The chain object genlayer-js signs against, built from the deployment, never from the SDK's default RPC. */
export function chainOf(where: Where): any {
  return { ...studioDevnet, id: where.chainId, rpcUrls: { default: { http: [where.rpc] } } };
}

/** A client that signs with an in-memory account (server) or through a provider (browser). */
export function writerFor(where: Where, signer: { account: any } | { address: string; provider: any }): any {
  if ("account" in signer) return createClient({ chain: chainOf(where), account: signer.account });
  return createClient({ chain: chainOf(where), account: signer.address as `0x${string}`, provider: signer.provider });
}

export function readerFor(where: Where): any {
  return createClient({ chain: chainOf(where) });
}

/**
 * Studio drops connections in bursts, and genlayer-js retries nothing. A read
 * or a wait retried is safe; a write is never retried here, because a write
 * resent after a lost answer is a second payment.
 */
export function isTransient(error: unknown): boolean {
  const text = String((error as Error)?.message ?? error);
  return /fetch failed|ECONNRESET|socket|network|timed out|timeout|Server busy|-32006|rate limit|429|502|503|504/i.test(text);
}

export async function retried<T>(what: string, fn: () => Promise<T>, attempts = 6): Promise<T> {
  let wait = 1200;
  for (let i = 1; ; i++) {
    try {
      return await fn();
    } catch (error) {
      if (i >= attempts || !isTransient(error)) throw error;
      await new Promise((r) => setTimeout(r, wait));
      wait = Math.min(Math.round(wait * 1.8), 12000);
    }
  }
}

export async function readJson(where: Where, reader: any, address: string, method: string, args: unknown[] = []): Promise<any> {
  const raw = await retried(`read ${method}`, () => reader.readContract({ address, functionName: method, args }));
  return typeof raw === "string" ? JSON.parse(raw) : raw;
}

/** The flat allocation for a write Studio cannot simulate, such as one it expects the contract to refuse. */
const FLAT = { leaderTimeunitsAllocation: 600n, validatorTimeunitsAllocation: 600n, rotations: [1n] };

function withoutMessageTotal(distribution: Record<string, unknown>): Record<string, unknown> {
  const { totalMessageFees: _dropped, ...rest } = distribution;
  return rest;
}

/**
 * The fee options for one write: Studio's estimate of the call, with settle
 * allocated beneath adjudicate for open_dispute.
 */
export async function feesFor(
  client: any,
  where: Where,
  call: { address: string; functionName: string; args: unknown[]; value: bigint; account?: any },
): Promise<any> {
  let estimate: any;
  try {
    estimate = await retried<any>(`fee estimate for ${call.functionName}`, () =>
      client.estimateTransactionFeesForWrite({
        address: call.address,
        functionName: call.functionName,
        args: call.args,
        value: call.value,
        ...(call.account ? { account: call.account } : {}),
      }),
    );
  } catch (error) {
    if (isTransient(error)) throw error;
    const flat: any = await retried<any>("flat fee estimate", () => client.estimateTransactionFees({ ...FLAT, totalMessageFees: 0n }));
    return { distribution: flat.distribution, feeValue: flat.feeValue };
  }

  if (call.functionName === "open_dispute") {
    const wanted = String(deriveInternalMessageCallKey("adjudicate")).toLowerCase();
    const nodes: any[] = (estimate.messageAllocations ?? []).map((node: any) => ({ ...node }));
    const parent = nodes.findIndex((node) => String(node.callKey).toLowerCase() === wanted);
    if (parent >= 0) {
      const own = BigInt(nodes[parent].budget);
      nodes.push({
        messageType: INTERNAL,
        onAcceptance: false,
        parentIndex: BigInt(parent),
        recipient: where.escrow,
        callKey: deriveInternalMessageCallKey("settle"),
        budget: own,
        feeParams: nodes[parent].feeParams,
      });
      nodes[parent].budget = own + own;
      estimate = await retried<any>("cascade fee estimate", () =>
        client.estimateTransactionFees({ ...withoutMessageTotal(estimate.distribution), messageAllocations: nodes }),
      );
    }
  }

  return {
    distribution: estimate.distribution,
    feeValue: estimate.feeValue,
    ...(estimate.messageAllocations?.length ? { messageAllocations: estimate.messageAllocations } : {}),
  };
}

/** The sentence a contract refused with, out of either shape Studio sends it in. */
export function refusalOf(receipt: any): string {
  const rounds = receipt?.consensus_data?.leader_receipt;
  const leader = Array.isArray(rounds) ? rounds.find((r: any) => String(r?.mode ?? "").toLowerCase() === "leader") ?? rounds[0] : rounds;
  const result = leader?.result;
  if (!result) return "";
  if (typeof result === "object") {
    const payload = result.payload;
    if (typeof payload === "string") return payload;
    if (payload && typeof payload === "object" && "readable" in payload) return String(payload.readable);
    return "";
  }
  try {
    return atob(String(result)).slice(1).replace(/[^\x20-\x7e\n]/g, "").trim();
  } catch {
    return "";
  }
}

/** The value a successful write returned, as JSON, or undefined when the receipt does not carry it. */
export function returnedOf(receipt: any): unknown {
  const rounds = receipt?.consensus_data?.leader_receipt;
  const leader = Array.isArray(rounds) ? rounds.find((r: any) => String(r?.mode ?? "").toLowerCase() === "leader") ?? rounds[0] : rounds;
  const result = leader?.result;
  if (result && typeof result === "object" && String(result.status).toLowerCase() === "return") {
    const readable = result.payload?.readable;
    if (typeof readable === "string") {
      try {
        return JSON.parse(readable);
      } catch {
        return readable;
      }
    }
  }
  return undefined;
}

export class Refused extends Error {
  constructor(
    message: string,
    readonly hash: string,
    readonly outcome: string,
  ) {
    super(message);
  }
}

/**
 * Write, report the hash the moment it exists, wait for the committee's
 * decision, and throw a Refused carrying the contract's own sentence when the
 * decision is not a success.
 */
export async function send(
  client: any,
  where: Where,
  call: { address: string; functionName: string; args: unknown[]; value?: bigint; account?: any },
  onHash?: (hash: string) => void,
): Promise<{ hash: string; receipt: any }> {
  const value = call.value ?? 0n;
  const fees = await feesFor(client, where, { ...call, value });
  const hash: string = await client.writeContract({
    address: call.address,
    functionName: call.functionName,
    args: call.args,
    value,
    fees,
  });
  onHash?.(hash);
  const receipt: any = await retried<any>(
    `wait for ${call.functionName}`,
    () => client.waitForTransactionReceipt({ hash, waitUntil: "decided", interval: 3000, retries: 100, fullTransaction: true }),
    4,
  );
  const outcome = String(receipt?.lifecycle?.outcome ?? receipt?.statusName ?? "");
  const execution = String(receipt?.txExecutionResultName ?? "");
  if (outcome !== "accepted" || execution !== "FINISHED_WITH_RETURN") {
    throw new Refused(refusalOf(receipt) || `${call.functionName} was not accepted: ${outcome || "?"} ${execution || ""}`.trim(), hash, outcome);
  }
  return { hash, receipt };
}

/**
 * Studio's faucet. The amount goes as a decimal string and the RPC's answer is
 * ignored: measured on Studio, a number is answered with a hash and credits
 * nothing, and a string is answered with an error after the credit has already
 * landed. Success is the balance moving, read back.
 */
export async function fund(where: Where, address: string, wei: bigint): Promise<{ before: bigint; after: bigint }> {
  const rpc = async (method: string, params: unknown[]) => {
    const response = await fetch(where.rpc, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }),
      cache: "no-store",
    });
    return response.json();
  };
  const balance = async () => {
    try {
      return BigInt((await rpc("eth_getBalance", [address, "latest"]))?.result ?? "0x0");
    } catch {
      return 0n;
    }
  };
  const before = await balance();
  await rpc("sim_fundAccount", [address, wei.toString()]).catch(() => null);
  let after = before;
  for (let i = 0; i < 16 && after <= before; i++) {
    await new Promise((r) => setTimeout(r, 1500));
    after = await balance();
  }
  return { before, after };
}

export { MESSAGE_ALLOCATION_ROOT_PARENT_INDEX };
