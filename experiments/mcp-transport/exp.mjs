// How the MCP TypeScript SDK carries HTTP status and JSON-RPC errors for a
// policy enforcement point. See README.md. Exits 1 on any unexpected outcome.
import http from 'node:http';
import { readFileSync } from 'node:fs';
import { Client, InsufficientScopeError, ProtocolError, StreamableHTTPClientTransport } from '@modelcontextprotocol/client';
import { McpServer, ProtocolError as ServerProtocolError, ProtocolErrorCode, createMcpHandler } from '@modelcontextprotocol/server';

const PDP_DELAY = 300;
const pdp = () => new Promise((_, reject) => setTimeout(() => reject(new Error('PDP unreachable')), PDP_DELAY));

// Per-case settings: what the tool does, what its scope hook does, and what
// the middleware in front of the SDK answers.
let toolMode = 'ok';
let scopeMode = 'none';
let wireCase = null;
let responseMode = 'auto';

function factory() {
    const server = new McpServer({ name: 'exp', version: '0' });
    server.registerTool(
        't',
        {
            description: 'test tool',
            scopeChallenge: async () => {
                if (scopeMode === 'throws') await pdp();
                if (scopeMode === 'challenge') return { scopes: ['tools.write'] };
                return undefined;
            }
        },
        async () => {
            if (toolMode === 'pdp-in-handler') {
                try {
                    await pdp();
                } catch {
                    throw new ServerProtocolError(ProtocolErrorCode.InternalError, 'Authorization service unavailable');
                }
            }
            if (toolMode === 'iserror') return { content: [{ type: 'text', text: 'Access denied' }], isError: true };
            return { content: [{ type: 'text', text: 'ok' }] };
        }
    );
    return server;
}

const handlers = {};
const handlerFor = mode => (handlers[mode] ??= createMcpHandler(factory, { responseMode: mode, keepAliveMs: 0 }));
// Token validation is fixture data: no token is sent, and the SDK receives
// this as if validation had passed.
const authInfo = { token: 'fixture', clientId: 'client-1', scopes: ['tools.invoke'], expiresAt: Math.floor(Date.now() / 1000) + 3600 };

async function rpcMessage(response) {
    const text = await response.text();
    if ((response.headers.get('content-type') || '').includes('text/event-stream')) {
        const data = text.split('\n').filter(l => l.startsWith('data:')).map(l => l.slice(5).trim()).filter(Boolean);
        return JSON.parse(data[data.length - 1]);
    }
    return JSON.parse(text);
}

const server = http.createServer(async (req, res) => {
    const chunks = [];
    for await (const c of req) chunks.push(c);
    const body = Buffer.concat(chunks);
    const headers = new Headers();
    for (const [k, v] of Object.entries(req.headers)) if (k !== 'host' && k !== 'connection') headers.set(k, String(v));
    const make = () =>
        new Request(`http://127.0.0.1:${port}${req.url}`, {
            method: req.method,
            headers,
            body: ['GET', 'HEAD', 'DELETE'].includes(req.method) ? undefined : body
        });
    let parsed;
    try {
        parsed = JSON.parse(body.toString() || 'null');
    } catch {}

    // Middleware enforcement point: runs before the SDK and sets the status.
    if (wireCase && parsed?.method === 'tools/call') {
        if (wireCase.delay) await pdp().catch(() => {});
        let message;
        if (wireCase.error) {
            // Written directly: McpServer turns a thrown error into an isError result.
            message = { jsonrpc: '2.0', id: parsed.id, error: wireCase.error };
        } else {
            toolMode = 'iserror';
            message = await rpcMessage(await handlerFor('json').fetch(make(), { authInfo }));
            toolMode = 'ok';
        }
        res.writeHead(wireCase.status, { 'content-type': 'application/json', ...wireCase.headers });
        res.end(JSON.stringify(message));
        return;
    }

    const response = await handlerFor(responseMode).fetch(make(), { authInfo });
    res.writeHead(response.status, Object.fromEntries(response.headers));
    res.flushHeaders(); // send the status line now, as a streaming server does
    if (response.body) for await (const chunk of response.body) res.write(chunk);
    res.end();
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const port = server.address().port;
const url = new URL(`http://127.0.0.1:${port}/mcp`);

// A host-supplied fetch that records what crossed the wire for tools/call.
let wire = [];
const recordingFetch = async (input, init) => {
    const started = Date.now();
    let method;
    try {
        method = JSON.parse(init?.body ?? 'null')?.method;
    } catch {}
    const response = await fetch(input, init);
    if (method === 'tools/call')
        wire.push({
            version: new Headers(init?.headers).get('mcp-protocol-version'),
            status: response.status,
            type: (response.headers.get('content-type') || '').split(';')[0],
            retryAfter: response.headers.get('retry-after'),
            challenge: response.headers.get('www-authenticate'),
            ms: Date.now() - started
        });
    return response;
};

function callerOutcome(result, error) {
    if (!error) return { caller: `result isError=${!!result.isError}`, body: 'parsed', headers: 'no' };
    if (error instanceof ProtocolError) return { caller: `ProtocolError ${error.code}`, body: 'parsed', headers: 'no' };
    if (error instanceof InsufficientScopeError) {
        const fields = ['requiredScope', 'resourceMetadataUrl', 'errorDescription'].filter(k => error[k] !== undefined);
        return { caller: 'InsufficientScopeError', body: 'no', headers: fields.join(', ') };
    }
    const carried = JSON.stringify({ ...error, data: error.data }) + error.message;
    return {
        caller: `${error.constructor.name} ${error.status ?? ''}`.trim(),
        body: /"jsonrpc"/.test(carried) ? 'text' : 'no',
        headers: /retry-after|www-authenticate|realm=/i.test(carried) ? 'yes' : 'no'
    };
}

const challenge = extra => ({ 'www-authenticate': `Bearer realm="exp"${extra}` });
const unavailable = { code: -32603, message: 'Authorization service unavailable' };
const denied = { code: -32001, message: 'Access denied' };
const mapping = { code: -32602, message: 'COAZ mapping error' };

// id, description, eras, setup, and whether a PDP call precedes the answer.
const cases = [
    ['A', 'middleware: 503, Retry-After, -32603 body', 'both', () => (wireCase = { status: 503, headers: { 'retry-after': '30' }, error: unavailable, delay: true }), true],
    ['B', 'middleware: 200, -32603 body', 'both', () => (wireCase = { status: 200, headers: {}, error: unavailable, delay: true }), true],
    ['C', 'middleware: 403 actor_unauthorized, -32001 body', 'both', () => (wireCase = { status: 403, headers: challenge(', error="actor_unauthorized"'), error: denied }), false],
    ['D', 'middleware: 403 without error attribute, -32001 body', 'both', () => (wireCase = { status: 403, headers: challenge(''), error: denied }), false],
    ['E', 'middleware: 403 without error attribute, isError body', 'both', () => (wireCase = { status: 403, headers: challenge('') }), false],
    ['F', 'SDK: tool returns an isError result', 'both', () => (toolMode = 'iserror'), false],
    ['G', 'middleware: 400, -32602 body', 'both', () => (wireCase = { status: 400, headers: {}, error: mapping }), false],
    ['H', 'middleware: 403 insufficient_scope, no auth provider', 'both', () => (wireCase = { status: 403, headers: challenge(', error="insufficient_scope", scope="tools.write"'), error: denied }), false],
    ['S1', 'SDK: PDP in tool handler, default response mode', 'both', () => (toolMode = 'pdp-in-handler'), true],
    ['S2', 'SDK: PDP in tool handler, responseMode sse', 'modern', () => ((toolMode = 'pdp-in-handler'), (responseMode = 'sse')), true],
    ['S3', 'SDK: PDP in tool handler, responseMode json', 'modern', () => ((toolMode = 'pdp-in-handler'), (responseMode = 'json')), true],
    ['S4', 'SDK: PDP in scopeChallenge hook, fails', 'both', () => (scopeMode = 'throws'), true],
    ['S5', 'SDK: scopeChallenge hook returns a challenge', 'both', () => (scopeMode = 'challenge'), false]
];

// Expected outcome per case. A `legacy` or `modern` member overrides fields
// for that era, and a field can map each era to its own value. `early`: the
// status was sent before the PDP answered (only for cases with a PDP call).
const versions = { legacy: '2025-11-25', modern: '2026-07-28' };
const sdkError = s => ({ caller: `SdkHttpError ${s}`, body: 'text', headers: 'no' });
const json = 'application/json';
const expected = {
    A: { status: 503, type: json, retryAfter: '30', challenge: false, ...sdkError(503), early: false },
    B: { status: 200, type: json, challenge: false, caller: 'ProtocolError -32603', body: 'parsed', headers: 'no', early: false },
    C: { status: 403, type: json, challenge: 'actor_unauthorized', ...sdkError(403) },
    D: { status: 403, type: json, challenge: 'no error', ...sdkError(403) },
    E: { status: 403, type: json, challenge: 'no error', ...sdkError(403) },
    F: { status: 200, type: { legacy: 'text/event-stream', modern: json }, challenge: false, caller: 'result isError=true', body: 'parsed', headers: 'no' },
    G: { status: 400, type: json, challenge: false, legacy: sdkError(400), modern: { caller: 'ProtocolError -32602', body: 'parsed', headers: 'no' } },
    H: { status: 403, type: json, challenge: 'insufficient_scope', caller: 'InsufficientScopeError', body: 'no', headers: 'requiredScope' },
    S1: { status: 200, type: { legacy: 'text/event-stream', modern: json }, challenge: false, caller: 'result isError=true', body: 'parsed', headers: 'no', early: { legacy: true, modern: false } },
    S2: { status: 200, type: 'text/event-stream', challenge: false, caller: 'result isError=true', body: 'parsed', headers: 'no', early: true },
    S3: { status: 200, type: json, challenge: false, caller: 'result isError=true', body: 'parsed', headers: 'no', early: false },
    S4: { status: 500, type: json, challenge: false, ...sdkError(500), early: false },
    S5: { status: 403, type: json, challenge: 'insufficient_scope', caller: 'InsufficientScopeError', body: 'no', headers: 'requiredScope, errorDescription' }
};

function challengeKind(c) {
    if (!c) return false;
    const m = /error="([^"]+)"/.exec(c);
    return m ? m[1] : 'no error';
}

async function run(era, [id, description, , setup, withPdp]) {
    wire = [];
    toolMode = 'ok';
    scopeMode = 'none';
    wireCase = null;
    responseMode = 'auto';
    setup();
    const client = new Client({ name: 'exp-client', version: '0' }, era === 'modern' ? { versionNegotiation: { mode: { pin: versions.modern } } } : {});
    const transport = new StreamableHTTPClientTransport(url, { fetch: recordingFetch });
    let result, error;
    try {
        await client.connect(transport);
        result = await client.callTool({ name: 't', arguments: {} }, undefined, { timeout: 5000 });
    } catch (e) {
        error = e;
    }
    await client.close().catch(() => {});
    const w = wire[wire.length - 1] || {};
    const observed = {
        version: w.version,
        status: w.status,
        type: w.type,
        retryAfter: w.retryAfter ?? undefined,
        challenge: challengeKind(w.challenge),
        ...callerOutcome(result, error),
        early: withPdp ? w.ms < PDP_DELAY / 2 : undefined
    };
    const { legacy, modern, ...base } = expected[id];
    const e = { version: versions[era], retryAfter: undefined, ...base, ...(era === 'legacy' ? legacy : modern) };
    for (const [k, v] of Object.entries(e)) if (v && typeof v === 'object') e[k] = v[era];
    if (!withPdp) e.early = undefined;
    const mismatches = Object.keys(e).filter(k => e[k] !== observed[k]).map(k => `${k}: expected ${JSON.stringify(e[k])}, observed ${JSON.stringify(observed[k])}`);
    return { era, id, description, observed, mismatches };
}

const rows = [];
for (const era of ['legacy', 'modern'])
    for (const c of cases) if (c[2] === 'both' || c[2] === era) rows.push(await run(era, c));
server.close();

const pkg = name => JSON.parse(readFileSync(new URL(`./node_modules/@modelcontextprotocol/${name}/package.json`, import.meta.url))).version;
console.log(`SDK client ${pkg('client')}, server ${pkg('server')}; Node ${process.version}; PDP delay ${PDP_DELAY} ms\n`);
console.log('| Era | Case | Status | Content type | `Retry-After` | Challenge `error` | Status sent before the PDP answered | SDK caller receives | JSON-RPC body reaches caller | Headers reach caller |');
console.log('|---|---|---|---|---|---|---|---|---|---|');
for (const { era, id, description, observed: o } of rows)
    console.log(
        `| ${era} (${o.version}) | ${id}: ${description} | ${o.status} | ${o.type} | ${o.retryAfter ?? '—'} | ${o.challenge === false ? '—' : o.challenge} | ${o.early === undefined ? '—' : o.early ? 'yes' : 'no'} | ${o.caller} | ${o.body} | ${o.headers} |`
    );
const failed = rows.filter(r => r.mismatches.length);
for (const r of failed) console.log(`\nUNEXPECTED ${r.era} ${r.id}:\n  ${r.mismatches.join('\n  ')}`);
console.log(`\n${rows.length - failed.length} of ${rows.length} outcomes as expected.`);
process.exit(failed.length ? 1 : 0);
