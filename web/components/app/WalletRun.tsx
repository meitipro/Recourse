"use client";

/**
 * Tier two: the same cycle, paid and signed by the visitor's own wallet.
 *
 * The wallet layer is Fieldwork's, on raw window.ethereum: eth_accounts on
 * mount, which never opens a prompt; eth_requestAccounts only on a Connect
 * click; accountsChanged and chainChanged listeners, removed on unmount;
 * wallet_switchEthereumChain, falling back to wallet_addEthereumChain when the
 * wallet does not know the chain, including a 4902 MetaMask wraps inside a
 * -32603. The chain parameters come from the deployment the page read from
 * contracts/FROZEN.json.
 */

import { useCallback, useEffect, useState } from "react";

import { GEN, type Where, readJson, readerFor, returnedOf, send, writerFor } from "@/lib/cycle";
import { humanError, type Advice } from "@/lib/human";
import { buildBody, checks as runChecks, serialize, type Check, type Mode } from "@/lib/quote";
import Consensus from "./Consensus";
import { Button, ChecksView, Label, ModePicker, Panel, SettlementNotice, Steps, T, TxLink, short, type StepView } from "./ui";

/* eslint-disable @typescript-eslint/no-explicit-any */

const PAIR = "ETH-USD";

function provider(): any {
  const eth = (globalThis as any).ethereum;
  if (!eth?.request) throw new Error("no_wallet");
  return eth;
}

function codeOf(error: any): number | undefined {
  return error?.code === -32603 ? error?.data?.originalError?.code ?? error?.data?.code : error?.code;
}

export default function WalletRun({ at, seller, chainName, amountGen, bondGen }: { at: Where; seller: string; chainName: string; amountGen: string; bondGen: string }) {
  const chainHex = `0x${at.chainId.toString(16)}`;
  const [address, setAddress] = useState<string | null>(null);
  const [chainId, setChainId] = useState<string | null>(null);
  const [balance, setBalance] = useState<bigint | null>(null);
  const [hasWallet, setHasWallet] = useState(true);
  const [note, setNote] = useState<Advice | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>("stale");
  const [run, setRun] = useState<Record<string, any>>({});
  const [startedAt, setStartedAt] = useState(0);

  const readBalance = useCallback(
    async (who: string) => {
      try {
        const response = await fetch(at.rpc, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "eth_getBalance", params: [who, "latest"] }),
        });
        setBalance(BigInt((await response.json())?.result ?? "0x0"));
      } catch {
        setBalance(null);
      }
    },
    [at.rpc],
  );

  useEffect(() => {
    const eth = (globalThis as any).ethereum;
    if (!eth?.request) {
      setHasWallet(false);
      return;
    }
    let live = true;
    const onAccounts = (accounts: string[]) => live && setAddress(accounts?.[0] ?? null);
    const onChain = (id: string) => live && setChainId(String(id).toLowerCase());
    eth.request({ method: "eth_accounts" }).then(onAccounts).catch(() => {});
    eth.request({ method: "eth_chainId" }).then(onChain).catch(() => {});
    eth.on?.("accountsChanged", onAccounts);
    eth.on?.("chainChanged", onChain);
    return () => {
      live = false;
      eth.removeListener?.("accountsChanged", onAccounts);
      eth.removeListener?.("chainChanged", onChain);
    };
  }, []);

  useEffect(() => {
    if (address) readBalance(address);
  }, [address, readBalance]);

  const onNetwork = chainId === chainHex;

  async function switchNetwork() {
    const eth = provider();
    try {
      await eth.request({ method: "wallet_switchEthereumChain", params: [{ chainId: chainHex }] });
    } catch (error: any) {
      if (codeOf(error) !== 4902) throw error;
      await eth.request({
        method: "wallet_addEthereumChain",
        params: [{ chainId: chainHex, chainName, rpcUrls: [at.rpc], blockExplorerUrls: [`${at.explorer}/`], nativeCurrency: { name: "GEN", symbol: "GEN", decimals: 18 } }],
      });
      await eth.request({ method: "wallet_switchEthereumChain", params: [{ chainId: chainHex }] });
    }
    setChainId(String(await eth.request({ method: "eth_chainId" })).toLowerCase());
  }

  async function act(label: string, fn: () => Promise<void>) {
    setBusy(label);
    setNote(null);
    try {
      await fn();
    } catch (error) {
      setNote(humanError(error));
    } finally {
      setBusy(null);
    }
  }

  const connect = () =>
    act("connect", async () => {
      const accounts: string[] = await provider().request({ method: "eth_requestAccounts" });
      setAddress(accounts?.[0] ?? null);
      await switchNetwork();
    });

  const faucet = () =>
    act("faucet", async () => {
      if (!address) throw new Error("no_wallet");
      const response = await fetch("/api/faucet", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ address }) });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        setNote({ text: body?.message ?? "The faucet did not answer. Try again in a moment.", action: "retry" });
        return;
      }
      setBalance(BigInt(body.after));
      setNote({ text: `100 GEN arrived. Balance before ${Number(BigInt(body.before) / 10n ** 16n) / 100}, after ${Number(BigInt(body.after) / 10n ** 16n) / 100}.` });
    });

  const pay = () =>
    act("run", async () => {
      if (!address) throw new Error("no_wallet");
      if (!onNetwork) throw new Error("wrong_network");
      const reader = readerFor(at);
      const stats = await readJson(at, reader, at.escrow, "stats");
      const bond = BigInt(stats.bond_amount);
      const amount = BigInt(amountGen) * GEN;
      if (balance !== null && balance < amount + bond + GEN / 10n) throw new Error("insufficient_balance");

      setRun({});
      setStartedAt(Date.now());
      const writer = writerFor(at, { address, provider: provider() });
      const promise = String((await readJson(at, reader, at.escrow, "get_seller", [seller])).promise);
      setRun((r) => ({ ...r, promise }));

      const paid = await send(writer, at, { address: at.escrow, functionName: "pay", args: [seller, `GET /quote?pair=${PAIR}`], value: amount }, (hash) =>
        setRun((r) => ({ ...r, payHash: hash })),
      );
      let pid = returnedOf(paid.receipt);
      if (typeof pid !== "string") {
        const rows = await readJson(at, reader, at.escrow, "recent_rows", [10]);
        pid = (Array.isArray(rows) ? rows : []).find((row: any) => String(row.buyer).toLowerCase() === address.toLowerCase())?.pid;
      }
      if (typeof pid !== "string") throw new Error("the payment was accepted but its id could not be read back");
      setRun((r) => ({ ...r, pid }));

      const received = new Date();
      const body = buildBody(PAIR, mode, received);
      const text = serialize(body);
      const results: Check[] = runChecks(body, PAIR, promise, received);
      setRun((r) => ({ ...r, response: text, checks: results, receivedAt: received.toISOString() }));

      await send(writer, at, { address: at.escrow, functionName: "record_response", args: [pid, text, ""] }, (hash) => setRun((r) => ({ ...r, recordHash: hash })));
      setRun((r) => ({ ...r, recorded: true }));

      if (results.every((one) => one.pass)) {
        setRun((r) => ({ ...r, noDispute: true }));
        return;
      }
      const opened = await send(writer, at, { address: at.escrow, functionName: "open_dispute", args: [pid], value: bond }, (hash) =>
        setRun((r) => ({ ...r, disputeHash: hash, disputeAt: Date.now() })),
      );
      const triggered = opened.receipt?.triggered_transactions;
      setRun((r) => ({ ...r, disputed: true, adjudicate: Array.isArray(triggered) ? triggered[0] ?? null : null }));
      readBalance(address);
    });

  const r = run;
  const active = busy === "run";
  const steps: StepView[] = startedAt
    ? [
        { key: "promise", title: "The seller's promise, read from the escrow", state: r.promise ? "done" : active ? "active" : "waiting", summary: r.promise ? short(seller) : undefined, detail: r.promise ? <div style={{ font: `400 15px/1.55 ${T.serif}`, color: T.ink }}>{r.promise}</div> : null },
        { key: "pay", title: `Pay ${amountGen} GEN, signed in your wallet`, state: r.pid ? "done" : r.promise && active ? "active" : "waiting", summary: r.pid ?? (r.payHash ? "submitted" : undefined), detail: r.payHash ? <TxLink explorer={at.explorer} hash={r.payHash} /> : "Confirm in your wallet." },
        { key: "checks", title: "The seller's response, and your checks", state: r.checks ? "done" : r.pid && active ? "active" : "waiting", summary: r.checks ? `${r.checks.filter((one: Check) => !one.pass).length} of 3 failed` : undefined, detail: r.checks ? <ChecksView response={r.response} checks={r.checks} receivedAt={r.receivedAt} /> : null },
        { key: "record", title: "Freeze the response on chain, signed in your wallet", state: r.recorded ? "done" : r.checks && active ? "active" : "waiting", summary: r.recorded ? "recorded, unsigned by the seller" : r.recordHash ? "submitted" : undefined, detail: r.recordHash ? <TxLink explorer={at.explorer} hash={r.recordHash} /> : "Confirm in your wallet." },
        { key: "dispute", title: `Contest it, with a ${bondGen} GEN bond, signed in your wallet`, state: r.noDispute ? "skipped" : r.disputed ? "done" : r.recorded && active ? "active" : "waiting", summary: r.noDispute ? "all three checks passed, nothing to contest" : r.disputed ? "accepted, judgment started" : r.disputeHash ? "submitted" : undefined, detail: r.disputeHash ? <TxLink explorer={at.explorer} hash={r.disputeHash} /> : "Confirm in your wallet." },
      ]
    : [];

  return (
    <div style={{ display: "grid", gap: "12px", minWidth: 0 }}>
      <Panel>
        <div style={{ display: "grid", gap: "12px" }}>
          {!hasWallet ? (
            <p style={{ margin: 0, font: `400 13.5px/1.6 ${T.sans}`, color: T.body }}>
              No wallet was found in this browser. <a href="https://metamask.io/download/" target="_blank" rel="noreferrer" style={{ color: T.accent }}>Install MetaMask</a>, reload this page, and connect.
            </p>
          ) : (
            <div style={{ display: "flex", flexWrap: "wrap", gap: "8px 14px", alignItems: "center" }}>
              <Button kind="quiet" onClick={connect} disabled={busy !== null || Boolean(address && onNetwork)}>
                {address ? short(address) : busy === "connect" ? "Connecting" : "Connect wallet"}
              </Button>
              {address && !onNetwork ? <Button onClick={() => act("switch", switchNetwork)} disabled={busy !== null}>Switch to {chainName}</Button> : null}
              {address ? <Button kind="quiet" onClick={faucet} disabled={busy !== null}>{busy === "faucet" ? "Funding" : "Get 100 test GEN"}</Button> : null}
              {address && balance !== null ? <span style={{ font: `500 12.5px ${T.mono}`, color: T.body }}>{Number(balance / 10n ** 16n) / 100} GEN</span> : null}
            </div>
          )}
          <ModePicker mode={mode} onChange={setMode} disabled={busy !== null} />
          <SettlementNotice amountGen={amountGen} bondGen={bondGen} />
          <Button onClick={pay} disabled={!address || !onNetwork || busy !== null}>
            {active ? "Running" : `Pay ${amountGen} GEN and run it`}
          </Button>
          {note ? (
            <div role="status" style={{ font: `400 13.5px/1.6 ${T.sans}`, color: note.action && note.action !== "retry" ? T.amber : T.body }}>
              {note.text}
              {note.action === "switch" ? <> <Button onClick={() => act("switch", switchNetwork)}>Switch network</Button></> : null}
            </div>
          ) : null}
        </div>
      </Panel>
      {steps.length ? <Steps steps={steps} /> : null}
      {r.disputed && r.pid ? <Consensus pid={r.pid} adjudicate={r.adjudicate} explorer={at.explorer} startedAt={r.disputeAt ?? Date.now()} /> : null}
      {!steps.length ? null : <Label>Every step above is signed by your wallet and paid from its balance.</Label>}
    </div>
  );
}
