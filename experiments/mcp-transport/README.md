# MCP Transport Experiment

This experiment records how the MCP TypeScript SDK carries an HTTP status
and a JSON-RPC error when a policy enforcement point refuses a
`tools/call`. It tests SDK behavior, not conformance to the profiles; the
[conformance suite](../../conformance/README.md) does that. The
implementer's guide cites it in [Failures at an MCP enforcement
point](../../IMPLEMENTERS-GUIDE.md#failures-at-an-mcp-enforcement-point).

## Running it

```sh
cd experiments/mcp-transport
npm ci --ignore-scripts
npm start
```

The script prints the table below and exits with status 1 if any
outcome differs from the expectation recorded in `exp.mjs`. It is run
by hand; CI does not run it.

## Environment

* `@modelcontextprotocol/client` and `@modelcontextprotocol/server`
  2.4.0, pinned exactly, with a lockfile. Neither Streamable HTTP
  transport file changes between 2.4.0 and commit `39ae8e6`
  (2026-10-27).
* Node v23.10.0 for the recorded run.
* Protocol versions: 2025-11-25, which the client negotiates with
  `initialize` by default, and 2026-07-28, pinned through the client's
  `versionNegotiation` option.
* A simulated policy decision point (PDP) that fails 300 ms after it is
  called.

## What the harness does

* The server is the SDK's `createMcpHandler`, serving an `McpServer`
  with one tool behind a Node HTTP server.
* Token validation is fixture data. No access token is sent or
  validated: the SDK receives a fixed `authInfo`, as if validation had
  passed.
* In cases A to E, G, and H, middleware in front of the SDK answers the
  `tools/call` itself, as an enforcement point beside token validation
  would. It writes each JSON-RPC error body directly, because
  `McpServer` returns an error that a tool handler throws as an
  `isError` result, unless the error is a URL elicitation request.
  Case E's body is the SDK's own `isError` result.
* Cases F and S1 to S5 go through the SDK.
* The client is the SDK's `Client` over `StreamableHTTPClientTransport`,
  with no auth provider. A host-supplied `fetch` records each
  response's status and headers.
* The HTTP server sends response headers as soon as the SDK returns a
  response, as a streaming server does. "Status sent before the PDP
  answered" compares the time to headers with half the PDP's delay.

## Results

| Era | Case | Status | Content type | `Retry-After` | Challenge `error` | Status sent before the PDP answered | SDK caller receives | JSON-RPC body reaches caller | Headers reach caller |
|---|---|---|---|---|---|---|---|---|---|
| legacy (2025-11-25) | A: middleware: 503, Retry-After, -32603 body | 503 | application/json | 30 | — | no | SdkHttpError 503 | text | no |
| legacy (2025-11-25) | B: middleware: 200, -32603 body | 200 | application/json | — | — | no | ProtocolError -32603 | parsed | no |
| legacy (2025-11-25) | C: middleware: 403 actor_unauthorized, -32001 body | 403 | application/json | — | actor_unauthorized | — | SdkHttpError 403 | text | no |
| legacy (2025-11-25) | D: middleware: 403 without error attribute, -32001 body | 403 | application/json | — | no error | — | SdkHttpError 403 | text | no |
| legacy (2025-11-25) | E: middleware: 403 without error attribute, isError body | 403 | application/json | — | no error | — | SdkHttpError 403 | text | no |
| legacy (2025-11-25) | F: SDK: tool returns an isError result | 200 | text/event-stream | — | — | — | result isError=true | parsed | no |
| legacy (2025-11-25) | G: middleware: 400, -32602 body | 400 | application/json | — | — | — | SdkHttpError 400 | text | no |
| legacy (2025-11-25) | H: middleware: 403 insufficient_scope, no auth provider | 403 | application/json | — | insufficient_scope | — | InsufficientScopeError | no | requiredScope |
| legacy (2025-11-25) | S1: SDK: PDP in tool handler, default response mode | 200 | text/event-stream | — | — | yes | result isError=true | parsed | no |
| legacy (2025-11-25) | S4: SDK: PDP in scopeChallenge hook, fails | 500 | application/json | — | — | no | SdkHttpError 500 | text | no |
| legacy (2025-11-25) | S5: SDK: scopeChallenge hook returns a challenge | 403 | application/json | — | insufficient_scope | — | InsufficientScopeError | no | requiredScope, errorDescription |
| modern (2026-07-28) | A: middleware: 503, Retry-After, -32603 body | 503 | application/json | 30 | — | no | SdkHttpError 503 | text | no |
| modern (2026-07-28) | B: middleware: 200, -32603 body | 200 | application/json | — | — | no | ProtocolError -32603 | parsed | no |
| modern (2026-07-28) | C: middleware: 403 actor_unauthorized, -32001 body | 403 | application/json | — | actor_unauthorized | — | SdkHttpError 403 | text | no |
| modern (2026-07-28) | D: middleware: 403 without error attribute, -32001 body | 403 | application/json | — | no error | — | SdkHttpError 403 | text | no |
| modern (2026-07-28) | E: middleware: 403 without error attribute, isError body | 403 | application/json | — | no error | — | SdkHttpError 403 | text | no |
| modern (2026-07-28) | F: SDK: tool returns an isError result | 200 | application/json | — | — | — | result isError=true | parsed | no |
| modern (2026-07-28) | G: middleware: 400, -32602 body | 400 | application/json | — | — | — | ProtocolError -32602 | parsed | no |
| modern (2026-07-28) | H: middleware: 403 insufficient_scope, no auth provider | 403 | application/json | — | insufficient_scope | — | InsufficientScopeError | no | requiredScope |
| modern (2026-07-28) | S1: SDK: PDP in tool handler, default response mode | 200 | application/json | — | — | no | result isError=true | parsed | no |
| modern (2026-07-28) | S2: SDK: PDP in tool handler, responseMode sse | 200 | text/event-stream | — | — | yes | result isError=true | parsed | no |
| modern (2026-07-28) | S3: SDK: PDP in tool handler, responseMode json | 200 | application/json | — | — | no | result isError=true | parsed | no |
| modern (2026-07-28) | S4: SDK: PDP in scopeChallenge hook, fails | 500 | application/json | — | — | no | SdkHttpError 500 | text | no |
| modern (2026-07-28) | S5: SDK: scopeChallenge hook returns a challenge | 403 | application/json | — | insufficient_scope | — | InsufficientScopeError | no | requiredScope, errorDescription |

Repeated runs print the same table.

## What the results show

* Middleware ahead of the SDK can answer 503 with `Retry-After` and a
  `-32603` body (A). The SDK caller receives an `SdkHttpError` with the
  status, and the body as text. The headers are not on that error; only
  the host's `fetch` saw them.
* Inside the SDK, a tool handler cannot set the status:
  * with a streamed response, the 200 was sent before the PDP answered
    (S1 at 2025-11-25, and S2);
  * with a JSON response, the headers waited for the result, but the
    status was still 200 (S1 at 2026-07-28, and S3);
  * the thrown `-32603` became an `isError` result every time.
* The per-tool `scopeChallenge` hook runs before the status is sent. It
  can answer 403 `insufficient_scope` (S5), but when it fails, the SDK
  answers 500 with no `Retry-After` (S4).
* A 403 can carry a `-32001` error or an `isError` result (C to E).
  Whether either conforms is not this experiment's question. This SDK's
  caller receives either body only as text in the HTTP error, and
  receives no part of the challenge.
* A 400 with `-32602` reaches the caller as a JSON-RPC error only at
  2026-07-28 (G).

## Limits

These observations apply to SDK 2.4.0. The experiment does not cover:
* other SDKs;
* hosts, and what a model receives;
* gateway products;
* SSE resumption;
* batched requests.
