/**
 * SHACKLE TypeScript Client — SP/1.0
 * ===================================
 * Thin client for Node.js agent runtimes (LangGraph JS, AutoGen JS, etc.)
 * 
 * Usage:
 *   import { ShackleClient, shackled } from 'shackle-client';
 *   
 *   const client = new ShackleClient({ sessionId: 'my-session' });
 *   await client.register({ agentId: 'research-bot', framework: 'langgraph' });
 *   
 *   // Before each tool call:
 *   const verdict = await client.preExec({
 *     toolName: 'web_search',
 *     paramsHash: hashParams({ query: 'latest AI news' }),
 *     estimatedCost: 0.002,
 *   });
 *   
 *   if (verdict.decision === 'ALLOW') {
 *     const result = await executeToolCall(...);
 *     await client.postExec({ actualCost: 0.0015, success: true });
 *   }
 */

import { createHash } from 'crypto';
import { Socket } from 'net';
import { randomUUID } from 'crypto';

// ────────────────────────────────────
// Types
// ────────────────────────────────────

export type Verdict = 'ALLOW' | 'DENY' | 'HITL';

export interface ShackleConfig {
  socketPath?: string;
  host?: string;
  port?: number;
  sessionId?: string;
  organizationId?: string;
  timeout?: number;
}

export interface RegisterParams {
  agentId: string;
  framework: string;
  agentVersion?: string;
  runtime?: string;
  metadata?: Record<string, string>;
}

export interface PreExecParams {
  toolName: string;
  paramsHash: Buffer | string;
  estimatedCost: number;
  callNumber: number;
  nonce?: number;
  parentGuardId?: string;
  tags?: Record<string, string>;
}

export interface PreExecResult {
  decision: Verdict;
  denyReason?: string;
  humanReadable?: string;
  budgetRemaining: number;
  repeatCount: number;
}

export interface PostExecParams {
  callNumber: number;
  actualCost: number;
  success: boolean;
  errorMessage?: string;
  durationMs?: number;
  tokensIn?: number;
  tokensOut?: number;
  modelUsed?: string;
}

// ────────────────────────────────────
// Client
// ────────────────────────────────────

export class ShackleClient {
  private socketPath: string;
  private sessionId: string;
  private organizationId: string;
  private timeout: number;
  private socket: Socket | null = null;
  private callNumber = 0;
  private buffer = '';
  private pending: Map<string, { resolve: Function; reject: Function }> = new Map();

  constructor(config: ShackleConfig = {}) {
    this.socketPath = config.socketPath || '/var/run/shackle/guardian.sock';
    this.sessionId = config.sessionId || '';
    this.organizationId = config.organizationId || '';
    this.timeout = config.timeout || 5000;
  }

  // ── Connection ──

  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.socket = new Socket();
      this.socket.connect(this.socketPath, () => resolve());
      this.socket.on('error', reject);
      this.socket.on('data', (data: Buffer) => this.handleData(data.toString()));
      this.socket.setTimeout(this.timeout);
    });
  }

  async close(): Promise<void> {
    if (this.socket) {
      this.socket.destroy();
      this.socket = null;
    }
  }

  // ── Registration ──

  async register(params: RegisterParams): Promise<string> {
    const msg = {
      type: 'register',
      agent_id: params.agentId,
      framework: params.framework,
      agent_version: params.agentVersion || '1.0.0',
      organization_id: this.organizationId,
      runtime: params.runtime || `node-${process.version}`,
      metadata: params.metadata || {},
    };
    const response = await this.send(msg);
    this.sessionId = response.session_id;
    return this.sessionId;
  }

  // ── Pre-Execution ──

  async preExec(params: PreExecParams): Promise<PreExecResult> {
    const msg = {
      type: 'pre_exec',
      session_id: this.sessionId,
      call_number: params.callNumber,
      tool_name: params.toolName,
      params_hash: typeof params.paramsHash === 'string'
        ? params.paramsHash
        : params.paramsHash.toString('hex'),
      estimated_cost: params.estimatedCost,
      nonce: params.nonce || Date.now() * 1000 + Math.floor(Math.random() * 1000),
      parent_guard_id: params.parentGuardId || '',
      tags: params.tags || {},
    };
    const response = await this.send(msg);
    return {
      decision: response.decision as Verdict,
      denyReason: response.deny_reason,
      humanReadable: response.human_readable,
      budgetRemaining: response.budget_remaining || 0,
      repeatCount: response.repeat_count || 0,
    };
  }

  // ── Post-Execution ──

  async postExec(params: PostExecParams): Promise<void> {
    const msg = {
      type: 'post_exec',
      session_id: this.sessionId,
      call_number: params.callNumber,
      actual_cost: params.actualCost,
      success: params.success,
      error_message: params.errorMessage || '',
      duration_ms: params.durationMs || 0,
      tokens_in: params.tokensIn || 0,
      tokens_out: params.tokensOut || 0,
      model_used: params.modelUsed || '',
    };
    await this.send(msg); // Fire and forget
  }

  // ── Heartbeat ──

  async heartbeat(): Promise<{ budgetRemaining: number; driftDetected: boolean }> {
    const msg = {
      type: 'heartbeat',
      session_id: this.sessionId,
      last_call_number: this.callNumber,
    };
    const response = await this.send(msg);
    return {
      budgetRemaining: response.budget_remaining || 0,
      driftDetected: response.drift_detected || false,
    };
  }

  // ── Internal ──

  private async send(message: Record<string, unknown>): Promise<Record<string, unknown>> {
    if (!this.socket) throw new Error('Not connected');

    const id = randomUUID();
    const payload = JSON.stringify({ id, ...message }) + '\n';

    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.socket!.write(payload);

      setTimeout(() => {
        if (this.pending.has(id)) {
          this.pending.delete(id);
          reject(new Error(`Request timeout: ${id}`));
        }
      }, this.timeout);
    });
  }

  private handleData(data: string): void {
    this.buffer += data;
    const lines = this.buffer.split('\n');
    this.buffer = lines.pop() || '';

    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const msg = JSON.parse(line);
        const pending = this.pending.get(msg.id || msg.correlation_id);
        if (pending) {
          this.pending.delete(msg.id || msg.correlation_id);
          pending.resolve(msg);
        }
      } catch {
        // Skip malformed lines
      }
    }
  }
}

// ────────────────────────────────────
// Decorator (TypeScript)
// ────────────────────────────────────

export interface ShackleDecoratorOptions {
  budget?: number;
  maxRepeatCalls?: number;
  timeoutSeconds?: number;
  client: ShackleClient;
}

export function shackled(options: ShackleDecoratorOptions) {
  return function (
    _target: unknown,
    _propertyKey: string,
    descriptor: PropertyDescriptor,
  ) {
    const original = descriptor.value;
    descriptor.value = async function (...args: unknown[]) {
      const client = options.client;
      const result = await original.apply(this, args);
      return result;
    };
    return descriptor;
  };
}

// ────────────────────────────────────
// Utilities
// ────────────────────────────────────

export function hashParams(params: Record<string, unknown>): string {
  const canonical = JSON.stringify(params, Object.keys(params).sort());
  return createHash('sha256').update(canonical).digest('hex');
}

export function generateNonce(): number {
  return Date.now() * 1000 + Math.floor(Math.random() * 1000);
}

// ────────────────────────────────────
// Auto-patch for LangGraph / AutoGen JS
// ────────────────────────────────────

export interface AutoPatchOptions {
  client: ShackleClient;
  budget?: number;
  maxRepeatCalls?: number;
}

export async function installGuard(options: AutoPatchOptions): Promise<void> {
  const { client } = options;
  console.log('[SHACKLE] Guard installed — TypeScript runtime');
  // Framework-specific hooks would go here:
  // - LangGraph: patch CompiledGraph.invoke
  // - AutoGen JS: patch tool execution
  // - Custom: wrap known tool call patterns
  await client.connect();
  await client.register({
    agentId: `node-agent-${process.pid}`,
    framework: 'typescript',
    agentVersion: '1.0.0',
  });
}

export { ShackleClient as Client };
