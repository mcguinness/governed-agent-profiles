"""Reference IdP, RAS and API for the mandatory delegated path (EXAMPLES, first transaction).

Test-only. State is in memory, keys are generated at start, there is no
TLS, and nothing persists. The servers exist so the conformance suite has
a first implementation to run against; they implement only what that transaction
exercises: a dedicated client using private_key_jwt, an ID Token subject,
bound governed agent access (DPoP at both token endpoints), and JWT access
tokens validated at the API.

The RAS also implements the oversight companion's Deferred Redemption for
an ID-JAG: when its policy requires approval for a scope, a redemption
that opts in with completion_mode=deferred and a DPoP proof is held for an
approver's decision (DTR), and completed from a test-controlled Access
Request Service. Only that path issues refresh tokens, and only when
test control permits them. No WAG, no CAI, and no mutual TLS.

For the core's Optional Policy Services, the API can hand its
authorization decision to a test-controlled policy service, in place of
its own user-permission and actor-gate evaluation. Either way, it reports
a valid token's denial under the core's Error Responses: the actor gate
first, then token authority, then any other denial, and HTTP 503 for an
evaluation that could not complete. It also accepts
self-acting tokens for a separate client registration, which the RAS
mints only through test control, and opaque tokens, which it introspects
at the RAS over HTTP with its own credential. The RAS mints opaque
tokens only through test control. Nothing caches an introspection
response.

Every check the negative cases exercise has a name (see CHECKS). The
runner's vacuity mode switches one off to show that the case that cites
it fails without it.

Each server also exposes POST /_test/<op> for the test-control adapter.
A third-party implementation supplies its own adapter instead. Each
server's clock can be advanced by test control, so time-dependent cases
never sleep; with no advance, it is the system clock.
"""
import base64
import copy
import hashlib
import http.client
import json
import secrets
import threading
import time
import urllib.error
import urllib.request
import uuid
from urllib.parse import parse_qs, quote_plus, unquote_plus, urlencode
from wsgiref.simple_server import WSGIRequestHandler, make_server

import jws

SKEW = 60          # seconds of clock skew allowed on time claims
DPOP_WINDOW = 60   # seconds a DPoP proof's iat may differ from now
GRANT_LIFETIME = 300
ACCESS_TOKEN_LIFETIME = 600
MAX_PENDING_LIFETIME = 3600         # a deferred redemption's longest pending time
AUTHORIZATION_LIFETIME = 8 * 3600   # absolute authorization expiration, from receipt
POLL_INTERVAL = 5

TOKEN_EXCHANGE = "urn:ietf:params:oauth:grant-type:token-exchange"
JWT_BEARER = "urn:ietf:params:oauth:grant-type:jwt-bearer"
DEFERRED_GRANT = "urn:ietf:params:oauth:grant-type:deferred"
REFRESH_GRANT = "refresh_token"
ID_JAG_TYPE = "urn:ietf:params:oauth:token-type:id-jag"
ID_TOKEN_TYPE = "urn:ietf:params:oauth:token-type:id_token"
ASSERTION_TYPE = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"

IDP_ISSUER = "https://idp.example/"
RAS_ISSUER = "https://ras.example/"
API_BASE = "https://api.example"
RESOURCE = "https://api.example/tenants/acme-data/"
OTHER_RESOURCE = "https://api.example/tenants/beta-data/"
SELF_ACTING_CLIENT = "analysis-agent-client"   # the self-acting population's registration
INTROSPECTION_CLIENT = "api-introspector"      # the API's credential at the RAS

# Query parameters on GET /tenants/{t}/files/{name}. They stand in for a tool
# call's arguments; the drafts define no such parameters. A conforming API
# passes them to its policy service only in context.request.
REQUEST_ATTRIBUTES = ("agent", "user", "client_id", "tenant", "scope")

CHECKS = {
    "idp.client_assertion_audience": "client assertion aud is the IdP issuer only",
    "idp.client_assertion_replay": "client assertion jti is not reused",
    "idp.client_assertion_time": "client assertion iat and nbf are not in the future",
    "idp.require_dpop": "bound profile requires a DPoP proof at issuance",
    "idp.single_resource": "exactly one resource parameter",
    "idp.id_token_audience": "ID Token audience is the authenticated client",
    "idp.id_token_time": "ID Token iat and nbf are not in the future",
    "idp.binding_enabled": "Identity Binding is enabled",
    "idp.agent_active": "Agent Principal is active",
    "idp.client_association": "Client Association permits delegated use of the binding",
    "idp.delegation": "Delegation Authorization permits the agent for the user",
    "idp.categorical_prohibition": "policy's categorical prohibition of the agent for a requested "
                                   "scope is enforced",
    "idp.scope_ceiling": "the issued scope stays within the Delegation Authorization's scope set",
    "ras.client_id": "grant client_id matches the authenticated client",
    "ras.grant_time": "grant iat and nbf are not in the future",
    "ras.require_cnf": "bound profile requires cnf.jkt in the grant",
    "ras.require_proof": "a grant with cnf requires a DPoP proof",
    "ras.proof_key_match": "the redemption proof key matches cnf.jkt",
    "ras.resource_match": "the resource parameter equals the grant's resource",
    "ras.scope_claim": "the grant's scope claim is a non-empty string",
    "ras.agent_eligibility": "the correlated agent record exists and is active",
    "ras.actor_gate": "RAS policy permits the agent to act for the user",
    "ras.actor_preservation": "act is copied unchanged into the access token",
    "ras.proof_replay": "a DPoP proof jti is not reused at the RAS",
    "ras.approval_gate": "a redemption RAS policy requires approval for issues nothing without one",
    "ras.absolute_expiration": "the absolute authorization expiration set at receipt bounds "
                               "expires_in and every token",
    "ras.deferral_key_binding": "a poll proves the key the deferral code is bound to",
    "ras.code_single_use": "a deferral code is redeemed by at most one token response",
    "ras.grant_consumed": "a deferred redemption consumes the grant; another presentation "
                          "fails with invalid_grant",
    "ras.single_pending": "identical deferred redemptions share one pending redemption and task",
    "ras.recovery_match": "recovery needs the same client, key, opt-in and request parameters",
    "ras.recovery_window": "recovery ends when the pending redemption is redeemed or ends",
    "ras.recovery_no_extension": "recovery never resets the pending deadline",
    "ras.task_per_redemption": "each pending redemption opens its own access request",
    "ras.approval_binding": "an approval completes only the task opened for that redemption",
    "ras.approval_narrowing": "the issued scope is the approved, possibly narrowed, scope",
    "ras.approval_deadline": "no token outlives approved_until; a later refresh fails",
    "ras.approval_reevaluation": "resolution and every refresh re-evaluate the kept approval",
    "ras.enforcement_deadline": "a shorter approved_until from re-evaluation bounds later tokens",
    "ras.resolution_recheck": "resolution and refresh re-check the agent, actor gate and user",
    "ras.correlation_continuity": "resolution and refresh require the agent's correlation to the "
                                  "same local principal",
    "ras.refresh_profile": "refresh enforces the current minimum profile against the accepted one",
    "ras.refresh_ends": "a refresh rejected on re-evaluation ends the refresh authorization",
    "api.key_binding": "the DPoP proof key matches the token's cnf.jkt",
    "api.token_time": "access token iat and nbf are not in the future",
    "api.require_act": "a governed delegated token carries a valid act",
    "api.tenant": "the token's tenant matches the requested tenant",
    "api.actor_gate": "API policy permits the agent to act for the user",
    "api.policy_source": "the policy evaluation takes the user, agent, client, tenant and token "
                         "constraints from the token or introspection and trusted configuration, "
                         "never from request attributes",
    "api.agent_from_token": "the API takes the agent from act, not from the client registration",
    "api.introspection_active": "an introspection response with active false is rejected",
    "api.introspection_act": "a delegated-population introspection response carries a valid act",
    "api.introspection_unavailable": "an introspection call that cannot complete gets HTTP 503, "
                                     "not invalid_token",
    "api.error_order": "of several failing conditions, the API reports the actor gate first, then "
                       "token authority, then any other denial",
    "api.denial_codes": "a denial carries actor_unauthorized only for the actor gate, "
                        "insufficient_scope only for token authority, and no error code otherwise",
    "api.evaluation_unavailable": "an evaluation that cannot complete gets HTTP 503, not a denial",
    "api.established_failure": "a failure no unfinished check outranks is reported, not HTTP 503",
    "api.incomplete_outranks": "an unfinished check that could outrank every established failure "
                               "gets HTTP 503",
}


class OAuthError(Exception):
    """An error response. With error None, the body is an empty JSON object."""

    def __init__(self, error, status=400, description=None, challenge=None, headers=None):
        super().__init__(error)
        self.error, self.status = error, status
        self.description, self.challenge = description, challenge
        self.headers = list(headers or [])


class Deferred(Exception):
    """A DTR deferred or pending response, sent as HTTP 400 with these members."""

    def __init__(self, body):
        super().__init__(body.get("error"))
        self.body = body


def _respond(start_response, status, body, headers=None, content_type="application/json"):
    reasons = {200: "OK", 400: "Bad Request", 401: "Unauthorized",
               403: "Forbidden", 404: "Not Found", 405: "Method Not Allowed",
               503: "Service Unavailable"}
    data = body if isinstance(body, bytes) else json.dumps(body).encode()
    hdrs = [("Content-Type", content_type), ("Cache-Control", "no-store"),
            ("Content-Length", str(len(data)))] + (headers or [])
    start_response(f"{status} {reasons.get(status, 'Error')}", hdrs)
    return [data]


def _read_body(environ):
    length = int(environ.get("CONTENT_LENGTH") or 0)
    return environ["wsgi.input"].read(length) if length else b""


def _form(environ):
    return parse_qs(_read_body(environ).decode("utf-8"), keep_blank_values=True)


def _one(form, name, error="invalid_request"):
    values = form.get(name, [])
    if len(values) != 1 or not values[0]:
        raise OAuthError(error, description=f"exactly one {name} required")
    return values[0]


def _time_valid(claims, require_iat, check_future=True, now=None):
    """exp not passed; iat, where required or present, and nbf not after now plus skew.

    RFC 7519 Section 4.1.5 for nbf, RFC 7523 Section 3 for assertions and grants,
    and the core's Time, Replay, and Key Validation for iat.
    """
    now = time.time() if now is None else now
    exp, iat, nbf = claims.get("exp"), claims.get("iat"), claims.get("nbf")
    if not isinstance(exp, int) or exp + SKEW < now:
        return False
    if require_iat and not isinstance(iat, int):
        return False
    if not check_future:
        return True
    for value in (iat, nbf):
        if value is not None and (not isinstance(value, int) or value > now + SKEW):
            return False
    return True


def _typ_is(header, media_type):
    """typ names the media type, with or without "application/" (RFC 7515 Section 4.1.9)."""
    value = header.get("typ")
    return isinstance(value, str) and value.lower() in (media_type, "application/" + media_type)


def _single_audience(aud, expected):
    """aud is the expected value as a string or a single-element array."""
    if isinstance(aud, list):
        return len(aud) == 1 and aud[0] == expected
    return aud == expected


class Server:
    """Shared plumbing: WSGI dispatch, test control, client and proof checks."""

    def __init__(self):
        self.lock = threading.Lock()
        self.disabled = set()
        self.assertion_replay = {}
        self.proof_replay = {}
        self.reset()

    def on(self, check):
        return check not in self.disabled

    def now(self):
        """The server's clock: the system clock plus any test-control advance."""
        return time.time() + self.offset

    def reset(self):
        self.disabled = set()
        self.offset = 0
        self.assertion_replay, self.proof_replay = {}, {}

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        # One request at a time: every check-then-record sequence in a
        # handler, such as accepting a grant and recording its pending
        # redemption, runs in this critical section.
        try:
            with self.lock:
                if path.startswith("/_test/"):
                    body = json.loads(_read_body(environ) or b"{}")
                    return _respond(start_response, 200,
                                    self.control(path[len("/_test/"):], body) or {})
                return self.handle(environ, start_response)
        except Deferred as deferred:
            return _respond(start_response, 400, deferred.body)
        except OAuthError as err:
            body = {"error": err.error} if err.error else {}
            if err.error and err.description:
                body["error_description"] = err.description
            headers = [("WWW-Authenticate", err.challenge)] if err.challenge else []
            return _respond(start_response, err.status, body, headers + err.headers)

    def control(self, op, body):
        if op == "reset":
            self.reset()
        elif op == "clock":
            self.offset += int(body["advance"])
            return {"offset": self.offset}
        elif op == "disable_check":
            if body["name"] not in CHECKS:
                raise OAuthError("invalid_request", description="unknown check")
            self.disabled.add(body["name"])
        else:
            return self.control_op(op, body)

    def control_op(self, op, body):
        raise OAuthError("invalid_request", 404, "unknown test-control op")

    def authenticate_client(self, form, clients, audience, check_prefix):
        """RFC 7523 private_key_jwt as the core's Dedicated Client Identity narrows it."""
        if form.get("client_assertion_type") != [ASSERTION_TYPE]:
            raise OAuthError("invalid_client")
        assertion = _one(form, "client_assertion", "invalid_client")
        try:
            _, unverified, _, _ = jws.decode(assertion)
        except ValueError:
            raise OAuthError("invalid_client")
        client_id = unverified.get("iss")
        if client_id not in clients or form.get("client_id", [client_id]) != [client_id]:
            raise OAuthError("invalid_client")
        try:
            _, claims = jws.verify(assertion, clients[client_id]["key"], "RS256")
        except ValueError:
            raise OAuthError("invalid_client")
        now = self.now()
        if claims.get("sub") != client_id:
            raise OAuthError("invalid_client")
        if self.on(f"{check_prefix}.client_assertion_audience") and \
                not _single_audience(claims.get("aud"), audience):
            raise OAuthError("invalid_client", description="aud must be the issuer")
        jti = claims.get("jti")
        if not jti or not _time_valid(claims, require_iat=False, check_future=self.on(
                f"{check_prefix}.client_assertion_time"), now=now):
            raise OAuthError("invalid_client")
        exp, key = claims["exp"], (client_id, jti)
        if key in self.assertion_replay and self.assertion_replay[key] > now and \
                self.on(f"{check_prefix}.client_assertion_replay"):
            raise OAuthError("invalid_client", description="assertion reused")
        self.assertion_replay[key] = exp + SKEW
        return client_id

    def validate_dpop(self, environ, method, htu, access_token=None, status=400,
                      check_prefix=None):
        """RFC 9449 Section 4.3 proof checks; returns the key thumbprint or None.

        With check_prefix, vacuity mode can switch off the replay check as
        "<prefix>.proof_replay"; without it, the replay check always applies.
        """
        proof = environ.get("HTTP_DPOP")
        if proof is None:
            return None
        bad = OAuthError("invalid_dpop_proof", status,
                         challenge='DPoP error="invalid_dpop_proof", algs="ES256"'
                         if status == 401 else None)
        try:
            header, payload, _, _ = jws.decode(proof)
            if header.get("typ") != "dpop+jwt" or header.get("alg") != "ES256":
                raise ValueError("typ or alg")
            key = jws.key_from_jwk(header.get("jwk") or {})
            jws.verify(proof, key, "ES256")
        except (ValueError, KeyError):
            raise bad
        now = self.now()
        iat = payload.get("iat")
        replay_on = check_prefix is None or self.on(f"{check_prefix}.proof_replay")
        if payload.get("htm") != method or payload.get("htu") != htu or \
                not isinstance(iat, int) or abs(iat - now) > DPOP_WINDOW or \
                not payload.get("jti") or (payload["jti"] in self.proof_replay and replay_on):
            raise bad
        if access_token is not None and payload.get("ath") != jws.ath(access_token):
            raise bad
        self.proof_replay[payload["jti"]] = now + DPOP_WINDOW
        return jws.thumbprint(header["jwk"])


class IdP(Server):
    """Grant Issuance at the IdP, delegated access with a dedicated client."""

    def __init__(self, client_keys):
        self.issuer, self.token_endpoint = IDP_ISSUER, IDP_ISSUER + "token"
        self.key, self.kid = jws.new_rsa_key(), "idp-key-1"
        self.client_keys = client_keys
        super().__init__()

    def reset(self):
        super().reset()
        self.clients = {"analysis-client": {"key": self.client_keys["analysis-client"],
                                            "profile": "bound"}}
        self.users = {"alice": {"active": True}}
        self.ras_subjects = {("alice", RAS_ISSUER): "alice-ras"}
        self.agents = {"agent-42": {"active": True}}
        self.bindings = {"b12": {"source": ("analysis-client", "analysis-client"),
                                 "agent": "agent-42", "enabled": True}}
        self.client_associations = {("analysis-client", "b12", "delegated")}
        # A Delegation Authorization's scope set is its scope ceiling.
        self.delegations = {("agent-42", "alice", "analysis-client", RESOURCE): {"files.read"}}
        # Policy's categorical prohibitions: (agent, resource) -> scopes the
        # agent may never be issued there, whatever a delegation permits.
        self.prohibitions = {}
        self.targets = {RAS_ISSUER: {"resources": {RESOURCE: "acme-data"},
                                     "registrations": {"analysis-client": "analysis-api"}}}

    def control_op(self, op, body):
        if op == "id_token":
            now = int(self.now())
            claims = {"iss": self.issuer, "sub": body.get("user", "alice"),
                      "aud": body.get("aud", "analysis-client"), "iat": now,
                      "exp": now + int(body.get("lifetime", 3900))}
            claims.update(body.get("claims", {}))
            return {"id_token": jws.sign({"typ": "JWT", "kid": self.kid}, claims, self.key)}
        if op == "mint_grant":
            now = int(self.now())
            claims = {"iss": self.issuer, "aud": RAS_ISSUER, "iat": now,
                      "exp": now + GRANT_LIFETIME, "jti": uuid.uuid4().hex}
            claims.update(body["claims"])
            return {"grant": jws.sign({"typ": "oauth-id-jag+jwt", "kid": self.kid},
                                      claims, self.key)}
        if op == "set":
            what, value = body["what"], body["value"]
            if what == "binding_enabled":
                self.bindings["b12"]["enabled"] = value
            elif what == "client_association":
                fn = self.client_associations.add if value else self.client_associations.discard
                fn(("analysis-client", "b12", "delegated"))
            elif what == "delegation":
                key = ("agent-42", "alice", "analysis-client", RESOURCE)
                if value:
                    self.delegations[key] = {"files.read"}
                else:
                    self.delegations.pop(key, None)
            elif what == "delegation_scope":
                # The delegation's scope set, creating the delegation.
                key = ("agent-42", "alice", "analysis-client", RESOURCE)
                self.delegations[key] = set(value or ())
            elif what == "prohibited_scope":
                self.prohibitions[("agent-42", RESOURCE)] = set(value or ())
            elif what == "agent_active":
                self.agents["agent-42"]["active"] = value
            elif what == "client_profile":
                self.clients["analysis-client"]["profile"] = value
            else:
                raise OAuthError("invalid_request", 404, "unknown setting")
            return {}
        return super().control_op(op, body)

    def handle(self, environ, start_response):
        if environ.get("PATH_INFO") != "/token" or environ["REQUEST_METHOD"] != "POST":
            return _respond(start_response, 404, {"error": "not_found"})
        form = _form(environ)
        if form.get("grant_type") != [TOKEN_EXCHANGE]:
            raise OAuthError("unsupported_grant_type")
        # Client authentication and proofs come before authorization (core, Token Endpoint Errors).
        client_id = self.authenticate_client(form, self.clients, self.issuer, "idp")
        jkt = self.validate_dpop(environ, "POST", self.token_endpoint)
        if jkt is None and self.clients[client_id]["profile"] == "bound" and \
                self.on("idp.require_dpop"):
            raise OAuthError("invalid_request", description="DPoP proof required")
        # Request parameters (core, Token Exchange Request; ID-JAG Request).
        if form.get("requested_token_type") != [ID_JAG_TYPE]:
            raise OAuthError("invalid_request")
        if "actor_token" in form or "actor_token_type" in form:
            raise OAuthError("invalid_request", description="authentication-context mode")
        audience = _one(form, "audience")
        resources = form.get("resource", [])
        if not resources:
            raise OAuthError("invalid_request", description="resource required")
        if len(resources) > 1 and self.on("idp.single_resource"):
            raise OAuthError("invalid_target")
        resource, scope = resources[0], _one(form, "scope")
        if form.get("subject_token_type") != [ID_TOKEN_TYPE]:
            raise OAuthError("invalid_request")
        # Subject token validation.
        user, id_token_exp = self.validate_id_token(_one(form, "subject_token"), client_id)
        # Agent resolution through an enabled Identity Binding.
        binding_id, agent = self.resolve_agent(client_id)
        # Subject resolution in the target RAS's namespace.
        if audience not in self.targets:
            raise OAuthError("invalid_target")
        ras_sub = self.ras_subjects.get((user, audience))
        if ras_sub is None or not self.users[user]["active"]:
            raise OAuthError("invalid_grant")
        target = self.targets[audience]
        if resource not in target["resources"]:
            raise OAuthError("invalid_target")
        downstream_client = target["registrations"].get(client_id)
        if downstream_client is None:
            raise OAuthError("invalid_target")
        # Client Association, then Delegation Authorization.
        if (client_id, binding_id, "delegated") not in self.client_associations and \
                self.on("idp.client_association"):
            raise OAuthError("actor_unauthorized")
        delegation = self.delegations.get((agent, user, client_id, resource))
        if delegation is None and self.on("idp.delegation"):
            raise OAuthError("actor_unauthorized")
        # Issuance Authorization: the request is narrowed by policy's
        # categorical prohibitions and by the delegation's scope ceiling.
        # If nothing remains, a prohibition of a requested scope is
        # actor_unauthorized, and otherwise the ceiling is invalid_scope.
        requested = scope.split()
        prohibited = self.prohibitions.get((agent, resource), set()) \
            if self.on("idp.categorical_prohibition") else set()
        ceiling = delegation if self.on("idp.scope_ceiling") else None
        granted = [s for s in requested if s not in prohibited and
                   (ceiling is None or s in ceiling)]
        if not granted:
            if prohibited & set(requested):
                raise OAuthError("actor_unauthorized", description="agent prohibited for the scope")
            raise OAuthError("invalid_scope")
        now = int(self.now())
        exp = min(now + GRANT_LIFETIME, id_token_exp)
        claims = {"iss": self.issuer, "sub": ras_sub, "aud": audience, "iat": now,
                  "exp": exp, "jti": uuid.uuid4().hex, "client_id": downstream_client,
                  "resource": resource, "scope": " ".join(granted),
                  "act": {"iss": self.issuer, "sub": agent}}
        if jkt is not None:
            claims["cnf"] = {"jkt": jkt}
        grant = jws.sign({"typ": "oauth-id-jag+jwt", "kid": self.kid}, claims, self.key)
        return _respond(start_response, 200, {
            "access_token": grant, "issued_token_type": ID_JAG_TYPE,
            "token_type": "N_A", "expires_in": exp - now, "scope": claims["scope"]})

    def validate_id_token(self, token, client_id):
        try:
            _, claims = jws.verify(token, self.key.public_key(), "RS256")
        except ValueError:
            raise OAuthError("invalid_grant")
        aud = claims.get("aud")
        audiences = aud if isinstance(aud, list) else [aud]
        if claims.get("iss") != self.issuer or claims.get("sub") not in self.users or \
                not _time_valid(claims, require_iat=True,
                                check_future=self.on("idp.id_token_time"), now=self.now()):
            raise OAuthError("invalid_grant")
        if client_id not in audiences and self.on("idp.id_token_audience"):
            raise OAuthError("invalid_grant")
        return claims["sub"], claims["exp"]

    def resolve_agent(self, client_id):
        matches = [(bid, b) for bid, b in self.bindings.items()
                   if b["source"] == (client_id, client_id)]
        if len(matches) != 1:
            raise OAuthError("invalid_grant")
        binding_id, binding = matches[0]
        if not binding["enabled"] and self.on("idp.binding_enabled"):
            raise OAuthError("invalid_grant")
        if not self.agents[binding["agent"]]["active"] and self.on("idp.agent_active"):
            raise OAuthError("invalid_grant")
        return binding_id, binding["agent"]


class AccessRequestService:
    """A test-controlled Access Request Service inside the RAS (ARAP).

    The RAS opens one task per pending redemption and asks for that task's
    result. Test control decides tasks. An approval is a complete object,
    {id, approved_until, approved_at} and an optional state, and is never
    rewritten. Test control can also revoke an approval, have the next
    re-evaluation of an approval return a shorter approved_until, and have
    the service answer one task's status with another task's result.
    """

    def __init__(self):
        self.tasks, self.revoked, self.shorter, self.substitutions = {}, set(), {}, {}

    def open(self, request):
        task_id = "task-" + uuid.uuid4().hex[:12]
        self.tasks[task_id] = {"id": task_id, "status": "pending", "request": request}
        return task_id

    def cancel(self, task_id):
        task = self.tasks.get(task_id)
        if task is not None and task["status"] == "pending":
            task["status"] = "cancelled"

    def status(self, task_id):
        """The result for a task, naming the task it belongs to, as a copy."""
        task = self.tasks.get(self.substitutions.get(task_id, task_id))
        if task is None:
            return {"task": task_id, "status": "pending"}
        result = {"task": task["id"], "status": task["status"]}
        for name in ("approval", "scope"):
            if task.get(name) is not None:
                result[name] = copy.deepcopy(task[name])
        return result

    def reevaluate(self, approval):
        """Re-evaluation with the approval unchanged: (valid, the approved_until it returns)."""
        if approval.get("id") in self.revoked or approval.get("id") not in \
                {t.get("approval", {}).get("id") for t in self.tasks.values()}:
            return False, approval["approved_until"]
        return True, self.shorter.pop(approval["id"], approval["approved_until"])

    def control(self, op, body, now):
        if op == "tasks":
            return {"tasks": [{"id": t["id"], "status": t["status"],
                               "user": t["request"]["user"],
                               "agent_iss": t["request"]["agent"]["iss"],
                               "agent": t["request"]["agent"]["sub"],
                               "client_id": t["request"]["client_id"],
                               "resource": t["request"]["resource"],
                               "scope": t["request"]["scope"]} for t in self.tasks.values()]}
        task = self.tasks.get(body.get("task"))
        if task is None:
            raise OAuthError("invalid_request", 404, "unknown task")
        if op == "approve":
            if task["status"] != "pending":
                return {"status": task["status"]}
            approval = {"id": "approval-" + uuid.uuid4().hex[:12],
                        "approved_until": int(body["approved_until"]), "approved_at": int(now)}
            if "state" in body:
                approval["state"] = body["state"]
            task.update(status="approved", approval=approval, scope=body.get("scope"))
            return {"approval": approval}
        if op == "deny":
            if task["status"] == "pending":
                task["status"] = "denied"
        elif op in ("revoke", "shorten"):
            approval = task.get("approval")
            if approval is None:
                raise OAuthError("invalid_request", 404, "task has no approval")
            if op == "revoke":
                self.revoked.add(approval["id"])
            else:
                self.shorter[approval["id"]] = int(body["approved_until"])
        elif op == "substitute":
            if body.get("with") not in self.tasks:
                raise OAuthError("invalid_request", 404, "unknown task")
            self.substitutions[task["id"]] = body["with"]
        return {}


class RAS(Server):
    """Grant Redemption at the RAS for an ID-JAG, issuing DPoP-bound JWT access tokens.

    With approval required by RAS policy, a redemption that opts in is
    deferred (oversight: Deferred Redemption) and completed by polling;
    refresh tokens issue only from that path.

    The RAS also answers RFC 7662 introspection at /introspect for opaque
    tokens that test control mints, to a caller that authenticates with
    HTTP Basic (RFC 6749 Section 2.3.1).
    """

    ARS_OPS = ("tasks", "approve", "deny", "revoke", "shorten", "substitute")

    def __init__(self, client_keys, idp_public_key, introspection_clients=None):
        self.issuer, self.token_endpoint = RAS_ISSUER, RAS_ISSUER + "token"
        self.key, self.kid = jws.new_rsa_key(), "ras-key-1"
        self.client_keys, self.idp_public_key = client_keys, idp_public_key
        self.introspection_clients = dict(introspection_clients or {})
        super().__init__()

    def reset(self):
        super().reset()
        self.clients = {cid: {"key": key, "profile": "bound"}
                        for cid, key in self.client_keys.items()}
        self.trusted_idps = {IDP_ISSUER: self.idp_public_key}
        # default_scope is used only by a RAS with ras.scope_claim switched off.
        self.resources = {RESOURCE: {"tenant": "acme-data", "protection": "dpop",
                                     "default_scope": "files.read"}}
        self.user_links = {(IDP_ISSUER, "acme-data", "alice-ras"): "user-108"}
        # agent-43 is a second agent for the same user, used by the deferral
        # cases that need two pending redemptions through one client.
        self.agents = {(IDP_ISSUER, "agent-42"): {"local": "service-principal-42", "active": True},
                       (IDP_ISSUER, "agent-43"): {"local": "service-principal-43", "active": True}}
        self.actor_gate = {("user-108", IDP_ISSUER, "agent-42", "acme-data"),
                           ("user-108", IDP_ISSUER, "agent-43", "acme-data")}
        self.accepted_grants = {}
        # Deferred redemption (oversight: Deferred Redemption).
        self.approval_required = set()   # scopes whose redemption RAS policy holds for approval
        self.refresh_permitted = False   # refresh tokens for approved standing access
        self.max_pending_lifetime = MAX_PENDING_LIFETIME
        self.authorization_lifetime = AUTHORIZATION_LIFETIME
        self.authorization_expirations = {}   # (iss, jti) -> absolute authorization expiration
        self.deferred_grants = set()           # (iss, jti) a deferred redemption consumed
        self.pending_by_digest, self.pending_by_code = {}, {}
        self.refresh_tokens = {}
        self.ars = AccessRequestService()
        # Introspection: opaque token -> the stored response members.
        self.opaque_tokens = {}
        self.introspection_omit_act = False   # test control: leave act out of every response
        # Test control: make the endpoint fail ("error": HTTP 503), answer
        # with a body that is not a JSON object ("malformed"), or close the
        # connection before the body it declares ("truncated").
        self.introspection_unavailable = False

    def control_op(self, op, body):
        if op == "set":
            what, value = body["what"], body["value"]
            if what == "agent_active":
                self.agents[(IDP_ISSUER, "agent-42")]["active"] = value
            elif what == "agent_local":
                self.agents[(IDP_ISSUER, "agent-42")]["local"] = value
            elif what == "actor_gate":
                entry = ("user-108", IDP_ISSUER, "agent-42", "acme-data")
                (self.actor_gate.add if value else self.actor_gate.discard)(entry)
            elif what == "client_profile":
                self.clients["analysis-api"]["profile"] = value
            elif what == "approval_required":
                self.approval_required = set(value or ())
            elif what == "refresh_permitted":
                self.refresh_permitted = bool(value)
            elif what == "max_pending_lifetime":
                self.max_pending_lifetime = int(value)
            elif what == "authorization_lifetime":
                self.authorization_lifetime = int(value)
            elif what == "introspection_omit_act":
                self.introspection_omit_act = bool(value)
            elif what == "introspection_unavailable":
                if value not in (False, None, "error", "malformed", "truncated"):
                    raise OAuthError("invalid_request", 400,
                                     "error, malformed, truncated or false")
                self.introspection_unavailable = value or False
            else:
                raise OAuthError("invalid_request", 404, "unknown setting")
            return {}
        if op == "mint_opaque_token":
            # An opaque access token and the members introspection returns for
            # it. A record minted with active false is returned as stored, with
            # its members (see introspect).
            now = int(self.now())
            record = {"active": True, "iss": self.issuer, "iat": now,
                      "exp": now + ACCESS_TOKEN_LIFETIME, "token_type": "DPoP"}
            record.update(body["claims"])
            token = secrets.token_urlsafe(32)
            self.opaque_tokens[token] = record
            return {"access_token": token}
        if op == "mint_access_token":
            now = int(self.now())
            claims = {"iss": self.issuer, "iat": now, "exp": now + ACCESS_TOKEN_LIFETIME,
                      "jti": uuid.uuid4().hex}
            claims.update(body["claims"])
            return {"access_token": jws.sign({"typ": body.get("typ", "at+jwt"),
                                              "kid": self.kid}, claims, self.key)}
        if op in self.ARS_OPS:
            return self.ars.control(op, body, self.now())
        return super().control_op(op, body)

    def handle(self, environ, start_response):
        path = environ.get("PATH_INFO")
        if path not in ("/token", "/introspect") or environ["REQUEST_METHOD"] != "POST":
            return _respond(start_response, 404, {"error": "not_found"})
        if path == "/introspect":
            if self.introspection_unavailable == "error":
                raise OAuthError(None, 503)
            body = self.introspect(environ)
            if self.introspection_unavailable == "malformed":
                return _respond(start_response, 200, b"temporarily unavailable",
                                content_type="text/plain")
            if self.introspection_unavailable == "truncated":
                data = json.dumps(body).encode()
                start_response("200 OK", [("Content-Type", "application/json"),
                                          ("Cache-Control", "no-store"),
                                          ("Content-Length", str(len(data) + 64))])
                return [data[:len(data) // 2]]
            return _respond(start_response, 200, body)
        form = _form(environ)
        grant_type = form.get("grant_type")
        if grant_type == [JWT_BEARER]:
            body = self.redeem(environ, form)
        elif grant_type == [DEFERRED_GRANT]:
            body = self.poll(environ, form)
        elif grant_type == [REFRESH_GRANT]:
            body = self.refresh(environ, form)
        else:
            raise OAuthError("unsupported_grant_type")
        return _respond(start_response, 200, body)

    def redeem(self, environ, form):
        client_id = self.authenticate_client(form, self.clients, self.issuer, "ras")
        jkt = self.validate_dpop(environ, "POST", self.token_endpoint, check_prefix="ras")
        assertion = _one(form, "assertion")
        deferred = form.get("completion_mode") == ["deferred"]
        # Recovery (oversight: Recovery) matches the byte-identical grant
        # before validating it again, so it works after the grant's exp.
        # Client authentication and the DPoP proof, with their replay
        # checks, have already run.
        digest = hashlib.sha256(assertion.encode("utf-8")).hexdigest()
        pending = self.pending_by_digest.get(digest) if self.on("ras.single_pending") else None
        if pending is not None:
            if self.recovers(pending, form, client_id, jkt, deferred):
                raise Deferred(self.deferred_body(pending))
            if self.on("ras.grant_consumed"):
                raise OAuthError("invalid_grant", description="grant consumed by a deferred redemption")
        claims = self.validate_grant(assertion)
        if claims.get("client_id") != client_id and self.on("ras.client_id"):
            raise OAuthError("invalid_grant", description="client_id mismatch")
        act = self.validate_act(claims)
        # Proof and client (core, Grant Protection; Common Grant Validation step 1).
        cnf = claims.get("cnf")
        if cnf is None and self.clients[client_id]["profile"] == "bound" and \
                self.on("ras.require_cnf"):
            raise OAuthError("invalid_grant", description="bound profile requires cnf")
        if cnf is not None:
            if not isinstance(cnf, dict) or not isinstance(cnf.get("jkt"), str) or len(cnf) != 1:
                raise OAuthError("invalid_grant", description="unsupported confirmation")
            if jkt is None and self.on("ras.require_proof"):
                raise OAuthError("invalid_grant", description="proof required")
            if jkt is not None and jkt != cnf["jkt"] and self.on("ras.proof_key_match"):
                raise OAuthError("invalid_grant", description="proof key mismatch")
        # Replay: this reference accepts each grant once, bound or not. It
        # records a grant as accepted when it issues an access token, or
        # when it defers the redemption.
        grant_key, now = (claims["iss"], claims["jti"]), self.now()
        if self.accepted_grants.get(grant_key, 0) > now and self.replay_refused(grant_key):
            raise OAuthError("invalid_grant", description="grant already redeemed")
        # Authority.
        resource = claims.get("resource")
        if isinstance(resource, list) and len(resource) == 1:
            resource = resource[0]
        if not isinstance(resource, str) or not resource:
            raise OAuthError("invalid_grant", description="resource claim")
        requested = form.get("resource", [])
        if len(requested) != 1 or (requested[0] != resource and self.on("ras.resource_match")):
            raise OAuthError("invalid_target")
        grant_scope = claims.get("scope")
        if not isinstance(grant_scope, str) or not grant_scope.split():
            if self.on("ras.scope_claim"):
                raise OAuthError("invalid_grant", description="scope claim")
            # Non-conforming: the resource's default scope stands in.
            grant_scope = (self.resources.get(resource) or {}).get("default_scope", "")
        scope = grant_scope
        if "scope" in form:
            asked = _one(form, "scope", "invalid_scope").split()
            if not asked or not set(asked) <= set(grant_scope.split()):
                raise OAuthError("invalid_scope")
            scope = " ".join(asked)
        config = self.resources.get(resource)
        if config is None:
            raise OAuthError("invalid_target")
        # Local authorization: user, agent correlation, actor gate.
        user = self.user_links.get((claims["iss"], config["tenant"], claims["sub"]))
        if user is None:
            raise OAuthError("invalid_grant", description="user not resolved")
        agent = self.agents.get((act["iss"], act["sub"]))
        if (agent is None or not agent["active"]) and self.on("ras.agent_eligibility"):
            raise OAuthError("invalid_grant", description="agent not eligible")
        if (user, act["iss"], act["sub"], config["tenant"]) not in self.actor_gate and \
                self.on("ras.actor_gate"):
            raise OAuthError("actor_unauthorized")
        # Approval required by RAS policy (oversight: Redemption Opt-In). The
        # RAS defers only with the opt-in, a DPoP proof, and DPoP access-token
        # protection; otherwise it refuses with its refusal error (core:
        # Redemption Errors), before access-token protection is considered.
        if self.on("ras.approval_gate") and set(scope.split()) & self.approval_required:
            if not deferred or jkt is None or config["protection"] != "dpop":
                raise OAuthError("actor_unauthorized", description="RAS policy requires approval")
            raise Deferred(self.defer(form, digest, grant_key, claims, client_id, jkt, act,
                                      user, config, resource, scope, now))
        if config["protection"] == "dpop" and jkt is None:
            raise OAuthError("invalid_request", description="DPoP-bound access token required")
        issued_act = dict(act)
        if not self.on("ras.actor_preservation"):
            issued_act["sub"] = agent["local"] if agent else act["sub"]
        token_claims = {"iss": self.issuer, "sub": user, "aud": resource, "iat": int(now),
                        "exp": int(now) + ACCESS_TOKEN_LIFETIME, "jti": uuid.uuid4().hex,
                        "client_id": client_id, "scope": scope, "act": issued_act,
                        "cnf": {"jkt": jkt}}
        token = jws.sign({"typ": "at+jwt", "kid": self.kid}, token_claims, self.key)
        self.accepted_grants[grant_key] = claims["exp"] + SKEW
        return {"access_token": token, "token_type": "DPoP",
                "expires_in": ACCESS_TOKEN_LIFETIME, "scope": scope}

    def introspect(self, environ):
        """RFC 7662 introspection for an authenticated caller; no caching or freshness."""
        scheme, _, credentials = environ.get("HTTP_AUTHORIZATION", "").partition(" ")
        try:
            client_id, _, secret = base64.b64decode(credentials, validate=True) \
                .decode("utf-8").partition(":")
            client_id, secret = unquote_plus(client_id), unquote_plus(secret)
        except ValueError:
            client_id = secret = None
        expected = self.introspection_clients.get(client_id)
        if scheme.lower() != "basic" or expected is None or \
                not secrets.compare_digest(secret.encode(), expected.encode()):
            raise OAuthError("invalid_client", 401, challenge='Basic realm="introspection"')
        form = _form(environ)
        record = self.opaque_tokens.get(_one(form, "token"))
        if record is None or record.get("exp", 0) + SKEW < self.now():
            # Unknown or expired: no other members (RFC 7662 Section 2.2).
            return {"active": False}
        response = copy.deepcopy(record)
        if self.introspection_omit_act:
            response.pop("act", None)
        return response

    def replay_refused(self, grant_key):
        """Whether an accepted grant is refused; a deferral-consumed one through switchable checks."""
        if grant_key in self.deferred_grants:
            return self.on("ras.grant_consumed") and self.on("ras.single_pending")
        return True

    @staticmethod
    def request_params(form):
        return tuple(tuple(form.get(name, [])) for name in
                     ("resource", "scope", "authorization_details"))

    def defer(self, form, digest, grant_key, claims, client_id, jkt, act, user, config,
              resource, scope, now):
        """Deferring a Redemption: every receipt check has passed.

        The grant's acceptance and the pending redemption are recorded in
        one critical section (Server.__call__ holds the lock), so identical
        requests yield one pending redemption and one task.
        """
        # Absolute authorization expiration, set at receipt. One already set
        # for the grant governs; this reference accepts each grant once, so
        # none exists here unless a vacuity switch lets a consumed grant in.
        abs_exp = self.authorization_expirations.setdefault(
            grant_key, int(now) + self.authorization_lifetime)
        lifetime = self.max_pending_lifetime
        if self.on("ras.absolute_expiration"):
            lifetime = min(lifetime, abs_exp - now)
        if lifetime <= 0:
            raise OAuthError("invalid_grant", description="absolute authorization expiration")
        pending = {"code": secrets.token_urlsafe(24), "digest": digest, "grant_key": grant_key,
                   "grant_sub": claims["sub"], "client_id": client_id, "jkt": jkt,
                   "params": self.request_params(form), "user": user,
                   "agent": (act["iss"], act["sub"]), "act": copy.deepcopy(act),
                   # The local principal the agent correlated to at receipt,
                   # and the profile under which the grant was accepted.
                   "agent_local": (self.agents.get((act["iss"], act["sub"])) or {}).get("local"),
                   "profile": "bound" if claims.get("cnf") is not None else "governed",
                   "tenant": config["tenant"], "resource": resource, "scope": scope,
                   "abs_exp": abs_exp, "deadline": now + lifetime, "state": "pending"}
        # The replay record lasts until the later of the request's end and
        # the grant's acceptance window plus skew.
        self.accepted_grants[grant_key] = max(claims["exp"] + SKEW, pending["deadline"])
        self.deferred_grants.add(grant_key)
        pending["task"] = self.open_task(pending)
        self.pending_by_digest[digest] = self.pending_by_code[pending["code"]] = pending
        return self.deferred_body(pending)

    def open_task(self, pending):
        """One access request per pending redemption, from its bound values (Approval Binding)."""
        ad = pending["params"][2]
        if not self.on("ras.task_per_redemption"):
            # AROP's idempotent submission applied across redemptions: the
            # same client, resource, scope and authorization_details reuse a
            # task, whichever agent asks.
            for other in self.pending_by_code.values():
                if other["state"] == "pending" and other["params"][2] == ad and \
                        (other["client_id"], other["resource"], other["scope"]) == \
                        (pending["client_id"], pending["resource"], pending["scope"]):
                    return other["task"]
        return self.ars.open({"user": pending["user"], "agent": pending["act"],
                              "client_id": pending["client_id"], "tenant": pending["tenant"],
                              "resource": pending["resource"], "scope": pending["scope"],
                              "authorization_details": list(ad)})

    def deferred_body(self, pending):
        return {"error": "authorization_pending", "deferral_code": pending["code"],
                "expires_in": max(0, int(pending["deadline"] - self.now())),
                "interval": POLL_INTERVAL}

    def expire_if_due(self, pending):
        if pending["state"] == "pending" and self.now() >= pending["deadline"]:
            pending["state"] = "expired"
            self.ars.cancel(pending["task"])

    def recovers(self, pending, form, client_id, jkt, deferred):
        """Recovery: the same client, a fresh proof of the same key, the opt-in, the same parameters."""
        self.expire_if_due(pending)
        if pending["state"] != "pending" and self.on("ras.recovery_window"):
            return False
        if pending["client_id"] != client_id:
            return False
        if self.on("ras.recovery_match") and (
                jkt != pending["jkt"] or not deferred or
                self.request_params(form) != pending["params"]):
            return False
        if not self.on("ras.recovery_no_extension"):
            now = self.now()
            pending["deadline"] = now + min(self.max_pending_lifetime, pending["abs_exp"] - now)
        return True

    def poll(self, environ, form):
        """A poll with a deferral code (DTR), resolved under Redemption Resolution."""
        client_id = self.authenticate_client(form, self.clients, self.issuer, "ras")
        jkt = self.validate_dpop(environ, "POST", self.token_endpoint, check_prefix="ras")
        pending = self.pending_by_code.get(_one(form, "deferral_code"))
        if pending is None or pending["client_id"] != client_id:
            raise OAuthError("invalid_grant", description="unknown deferral code")
        if jkt is None or (jkt != pending["jkt"] and self.on("ras.deferral_key_binding")):
            raise OAuthError("invalid_dpop_proof", description="not the deferral code's key")
        if pending["state"] == "redeemed" and self.on("ras.code_single_use"):
            raise OAuthError("invalid_grant", description="deferral code already redeemed")
        if pending["state"] == "denied":
            raise OAuthError("access_denied")
        self.expire_if_due(pending)
        if pending["state"] == "expired":
            raise OAuthError("expired_token")
        result = self.ars.status(pending["task"])
        # Approval Binding: a result for another task completes nothing, and
        # the redemption stays pending.
        if result["task"] != pending["task"] and self.on("ras.approval_binding"):
            raise Deferred({"error": "authorization_pending"})
        if result["status"] == "pending":
            raise Deferred({"error": "authorization_pending"})
        if result["status"] != "approved":
            pending["state"] = "denied"
            raise OAuthError("access_denied")
        approval, now = result["approval"], self.now()
        failure, enforcement = self.reevaluate(pending, approval, None, now)
        scope = pending["scope"].split()
        if result.get("scope") and self.on("ras.approval_narrowing"):
            # An approval narrows the request and never widens it.
            scope = [s for s in scope if s in result["scope"].split()]
            failure = failure or (None if scope else "approval covers no requested scope")
        if failure:
            pending["state"] = "denied"
            raise OAuthError("access_denied", description=failure)
        auth = {name: pending[name] for name in
                ("client_id", "jkt", "user", "grant_key", "grant_sub", "agent", "act",
                 "agent_local", "profile", "tenant", "resource", "abs_exp")}
        auth.update(scope=" ".join(scope), approval=copy.deepcopy(approval),
                    enforcement=enforcement)
        token, exp = self.authorized_token(auth, now)
        pending["state"] = "redeemed"
        body = {"access_token": token, "token_type": "DPoP",
                "expires_in": exp - int(now),
                "scope": auth["scope"]}
        if self.refresh_permitted:
            # DPoP-bound to the redemption key and bound to the client; it
            # keeps the complete approval object and the absolute expiration.
            refresh_token = secrets.token_urlsafe(32)
            self.refresh_tokens[refresh_token] = auth
            body["refresh_token"] = refresh_token
        return body

    def reevaluate(self, auth, approval, enforcement, now):
        """Re-evaluate with the kept approval; return (failure or None, enforcement deadline)."""
        valid, returned_until = self.ars.reevaluate(approval)
        if not valid and self.on("ras.approval_reevaluation"):
            return "approval revoked", enforcement
        if approval["approved_until"] <= now and self.on("ras.approval_deadline"):
            return "approval expired", enforcement
        if returned_until < approval["approved_until"] and self.on("ras.enforcement_deadline"):
            # Kept apart from the approval object, which is never rewritten.
            enforcement = returned_until if enforcement is None else min(enforcement,
                                                                         returned_until)
        if enforcement is not None and enforcement <= now:
            return "enforcement deadline passed", enforcement
        if self.on("ras.resolution_recheck"):
            agent = self.agents.get(auth["agent"])
            if agent is None or not agent["active"]:
                return "agent not eligible", enforcement
            if agent["local"] != auth["agent_local"] and \
                    self.on("ras.correlation_continuity"):
                # A changed link does not transfer the delegation.
                return "agent correlation changed", enforcement
            if (auth["user"], *auth["agent"], auth["tenant"]) not in self.actor_gate:
                return "actor gate", enforcement
            if self.user_links.get((auth["grant_key"][0], auth["tenant"],
                                    auth["grant_sub"])) != auth["user"]:
                return "user resolution changed", enforcement
        return None, enforcement

    def authorized_token(self, auth, now):
        """An access token for an approved authorization, within every deadline."""
        exp = now + ACCESS_TOKEN_LIFETIME
        if self.on("ras.approval_deadline"):
            exp = min(exp, auth["approval"]["approved_until"])
        if auth["enforcement"] is not None:
            exp = min(exp, auth["enforcement"])
        if self.on("ras.absolute_expiration"):
            exp = min(exp, auth["abs_exp"])
        exp = int(exp)
        claims = {"iss": self.issuer, "sub": auth["user"], "aud": auth["resource"],
                  "iat": int(now), "exp": exp, "jti": uuid.uuid4().hex,
                  "client_id": auth["client_id"], "scope": auth["scope"],
                  "act": copy.deepcopy(auth["act"]), "cnf": {"jkt": auth["jkt"]}}
        return jws.sign({"typ": "at+jwt", "kid": self.kid}, claims, self.key), exp

    def refresh(self, environ, form):
        """Refresh after a deferred redemption (Refresh and Continuation; core ras-refresh)."""
        client_id = self.authenticate_client(form, self.clients, self.issuer, "ras")
        jkt = self.validate_dpop(environ, "POST", self.token_endpoint, check_prefix="ras")
        auth = self.refresh_tokens.get(_one(form, "refresh_token"))
        if auth is None or auth["client_id"] != client_id:
            raise OAuthError("invalid_grant", description="unknown refresh token")
        if jkt is None or jkt != auth["jkt"]:
            raise OAuthError("invalid_grant", description="refresh token bound to another key")
        if "resource" in form and form["resource"] != [auth["resource"]]:
            raise OAuthError("invalid_target")
        # The client and its key are authenticated; a rejection from here on
        # ends the refresh authorization (Refresh and Continuation), so a
        # later change back cannot revive it. A failed client
        # authentication or proof above never ends it.
        now, failure = self.now(), None
        if self.clients[client_id]["profile"] == "bound" and auth["profile"] != "bound" and \
                self.on("ras.refresh_profile"):
            # core ras-refresh step 3: a proof at redemption does not upgrade
            # an authorization accepted under governed agent access.
            failure = "minimum profile no longer met"
        elif now >= auth["abs_exp"] and self.on("ras.absolute_expiration"):
            failure = "absolute authorization expiration"
        else:
            failure, auth["enforcement"] = self.reevaluate(auth, auth["approval"],
                                                           auth["enforcement"], now)
        if failure:
            if self.on("ras.refresh_ends"):
                self.refresh_tokens.pop(_one(form, "refresh_token"), None)
            raise OAuthError("invalid_grant", description=failure)
        token, exp = self.authorized_token(auth, now)
        return {"access_token": token, "token_type": "DPoP", "expires_in": exp - int(now),
                "scope": auth["scope"]}

    def validate_grant(self, assertion):
        """ID-JAG validation (ID-JAG Section 4.4.1, RFC 7523 Section 3)."""
        try:
            header, unverified, _, _ = jws.decode(assertion)
            if not _typ_is(header, "oauth-id-jag+jwt"):
                raise ValueError("typ")
            key = self.trusted_idps.get(unverified.get("iss"))
            if key is None:
                raise ValueError("untrusted issuer")
            _, claims = jws.verify(assertion, key, "RS256")
        except ValueError:
            raise OAuthError("invalid_grant")
        if not _single_audience(claims.get("aud"), self.issuer) or not claims.get("jti") or \
                not _time_valid(claims, require_iat=True, check_future=self.on("ras.grant_time"),
                                now=self.now()):
            raise OAuthError("invalid_grant")
        return claims

    def validate_act(self, claims):
        act = claims.get("act")
        if not isinstance(act, dict) or "act" in act or \
                not isinstance(act.get("iss"), str) or not act["iss"] or \
                not isinstance(act.get("sub"), str) or not act["sub"] or \
                act["iss"] != claims["iss"] or act["iss"] not in self.trusted_idps:
            raise OAuthError("invalid_grant", description="act")
        return act


# The reporting order of the core's Error Responses for the denial of a
# valid token: the actor gate, then token authority, then any other
# denial. Token and proof failures, and token-context failures, are
# reported before all three, by token validation. WRONG_ORDER is used only
# with api.error_order switched off.
ERROR_ORDER = ("actor", "authority", "other")
WRONG_ORDER = ("other", "authority", "actor")
RETRY_AFTER = 5   # seconds, on a 503 for an evaluation that could not complete


def default_policy():
    """The policy service's policy when test control enables it, as the API's own
    configuration has it: the positive path in both tenants, and its self-acting
    equivalent."""
    agent = {"iss": IDP_ISSUER, "sub": "agent-42"}
    tenants = ("acme-data", "beta-data")
    return {
        "actor_gate": [{"user": "user-108", "agent": agent, "tenant": t} for t in tenants],
        "prohibited": [],
        "required_scope": {"read": "files.read"},
        "user_permissions": [{"user": "user-108", "tenant": t, "action": "read"}
                             for t in tenants],
        "agent_permissions": [{"agent": "service-principal-42", "tenant": "acme-data",
                               "action": "read"}],
        "allowed_clients": ["analysis-api", SELF_ACTING_CLIENT],
        "allowed_tenants": list(tenants),
    }


class IntrospectionUnavailable(Exception):
    """An introspection call that did not complete token validation (core: Optional
    Opaque Access Tokens and Introspection): no JSON object with a boolean active."""


class PolicyUnavailable(Exception):
    """The policy service cannot be reached."""


class PolicyService:
    """A test-controlled policy decision service, called by the API in-process.

    The API's evaluation request follows the implementer's guide's
    illustrative AuthZEN requests: subject, action and resource, with the
    agent, client, tenant, token constraints and the request's own
    attributes in context. The drafts define no AuthZEN mapping; this
    shape is the reference's.

        {"subject": {"type": "user" or "agent", "id": ...},
         "action": {"name": "read"},
         "resource": {"type": "file", "id": ...},
         "context": {"agent": {"iss": ..., "sub": ...},   delegated access only
                     "client": ..., "tenant": ...,
                     "constraints": {"scope": ..., "aud": ...},
                     "request": {...}}}                    request attributes, verbatim

    The policy is a document whose members each list what policy permits:

        actor_gate         [{user, agent: {iss, sub}, tenant}]  the actor gate
        prohibited         [{agent: {iss, sub}, action}]        categorical prohibitions
                                                                of an agent
        required_scope     {action: scope}                      the scope an action needs
        user_permissions   [{user, tenant, action}]             the user's own permissions
        agent_permissions  [{agent, tenant, action}]            a self-acting agent's own
                                                                permissions, by local
                                                                principal
        allowed_clients    [client]
        allowed_tenants    [tenant]

    It evaluates three conditions in the order the API asks for, and
    returns the first that fails as the decision's reason:

        actor       delegated access only: the agent is categorically
                    prohibited for the action, or the actor gate has no
                    entry for the user, agent and tenant;
        authority   the token constraints' scope lacks the action's
                    required scope, which the decision names;
        other       the client or tenant is not allowed, or the user, or
                    for self-acting access the agent, lacks the permission.

        {"decision": true}
        {"decision": false, "reason": "actor" | "authority" | "other",
         "scope": ...}                                     authority only
        {"incomplete": "actor" | "authority" | "other"}    a condition it could not
                                                           evaluate, before any failure

    The service records every request it receives. When test control makes
    it unavailable, it receives nothing and raises PolicyUnavailable. Test
    control can instead make one condition's evaluation fail: the service
    stops there, unless an earlier condition already failed. Two
    non-conforming modes exist for vacuity: skip_unavailable passes over
    that condition and reports a later failure instead, and complete_all
    evaluates every condition and reports any it could not evaluate, even
    after an earlier failure.
    """

    def __init__(self, policy):
        self.policy, self.evaluations, self.available = copy.deepcopy(policy), [], True
        self.unavailable = set()

    def evaluate(self, request, order=ERROR_ORDER, skip_unavailable=False, complete_all=False):
        if not self.available:
            raise PolicyUnavailable()
        self.evaluations.append(copy.deepcopy(request))
        policy, context = self.policy, request["context"]
        subject, action = request["subject"].get("id"), request["action"].get("name")
        delegated = request["subject"].get("type") == "user"
        agent, tenant = context.get("agent"), context.get("tenant")
        scope = str((context.get("constraints") or {}).get("scope") or "").split()
        required = (policy.get("required_scope") or {}).get(action)

        def actor():
            if not delegated:   # self-acting access: no actor gate
                return True
            if any(p.get("agent") == agent and p.get("action", action) == action
                   for p in policy.get("prohibited", [])):
                return False
            return any(p.get("user") == subject and p.get("agent") == agent and
                       p.get("tenant") == tenant for p in policy.get("actor_gate", []))

        def authority():
            return required is None or required in scope

        def other():
            if context.get("client") not in policy.get("allowed_clients", []) or \
                    tenant not in policy.get("allowed_tenants", []):
                return False
            key = "user" if delegated else "agent"
            return any(p.get(key) == subject and p.get("tenant") == tenant and
                       p.get("action") == action
                       for p in policy.get(f"{key}_permissions", []))

        conditions = {"actor": actor, "authority": authority, "other": other}
        incomplete, failure = None, None
        for reason in order:
            if reason in self.unavailable and (delegated or reason != "actor"):
                if not (skip_unavailable or complete_all):
                    return {"incomplete": reason}
                incomplete = incomplete or reason
                continue
            if failure is None and not conditions[reason]():
                failure = reason
                if not complete_all:
                    break
        if complete_all and incomplete:
            return {"incomplete": incomplete}
        if failure:
            decision = {"decision": False, "reason": failure}
            if failure == "authority":
                decision["scope"] = required
            return decision
        return {"incomplete": incomplete} if incomplete else {"decision": True}


def _valid_act(act, namespaces):
    """One act object with non-empty iss and sub, no nesting, in a trusted namespace."""
    return isinstance(act, dict) and "act" not in act and \
        isinstance(act.get("iss"), str) and bool(act["iss"]) and \
        isinstance(act.get("sub"), str) and bool(act["sub"]) and act["iss"] in namespaces


class API(Server):
    """Access at the Resource Server for DPoP-bound access tokens.

    JWT access tokens are validated under RFC 9068. An opaque token is
    introspected at the RAS (RFC 7662) with the API's own credential, and
    the response is treated as validated claims. Applicability comes from
    trusted client and resource configuration: a delegated population and,
    for a separate registration, a self-acting one.
    """

    def __init__(self, ras_public_key):
        self.ras_public_key = ras_public_key
        # Set by start(): (endpoint, client_id, secret) for introspection at the RAS.
        self.introspection = None
        super().__init__()

    def reset(self):
        super().reset()
        self.trusted_ras = {RAS_ISSUER: {"key": self.ras_public_key, "namespaces": {IDP_ISSUER}}}
        self.resource_tenants = {RESOURCE: "acme-data", OTHER_RESOURCE: "beta-data"}
        # A separate client registration distinguishes the self-acting
        # population (core: Profile Applicability).
        self.populations = {("analysis-api", RESOURCE): "delegated",
                            ("analysis-api", OTHER_RESOURCE): "delegated",
                            (SELF_ACTING_CLIENT, RESOURCE): "self-acting"}
        self.permissions = {("user-108", "acme-data"): {"read"},
                            ("user-108", "beta-data"): {"read"}}
        self.actor_gate = {(IDP_ISSUER, "agent-42", "user-108", "acme-data"),
                           (IDP_ISSUER, "agent-42", "user-108", "beta-data")}
        # Self-acting access: the agent's own permissions, by local principal.
        self.agent_permissions = {("service-principal-42", "acme-data"): {"read"}}
        # The agent a client registration usually acts as. Only an API with
        # api.agent_from_token switched off uses it, in place of act: the
        # dedicated-client assumption that a shared client breaks.
        self.client_agents = {"analysis-api": {"iss": IDP_ISSUER, "sub": "agent-42"}}
        self.files = {("acme-data", "report-7"): b"region,revenue\nnorth,1200\nsouth,950\n",
                      ("beta-data", "report-9"): b"region,revenue\neast,700\n"}
        # Optional Policy Services: off unless test control enables it.
        self.policy_service = False
        self.policy = PolicyService(default_policy())

    def control_op(self, op, body):
        if op == "set" and body["what"] == "actor_gate":
            entry = (IDP_ISSUER, "agent-42", "user-108", "acme-data")
            (self.actor_gate.add if body["value"] else self.actor_gate.discard)(entry)
            return {}
        if op == "set" and body["what"] == "policy_service":
            self.policy_service = bool(body["value"])
            return {}
        if op == "set" and body["what"] == "policy_unavailable":
            self.policy.available = not body["value"]
            return {}
        if op == "set" and body["what"] == "condition_unavailable":
            # One condition's evaluation cannot complete: actor, authority, or other.
            self.policy.unavailable = set(body["value"] or ())
            return {}
        if op == "policy":
            self.policy.policy = copy.deepcopy(body["policy"])
            return {}
        if op == "evaluations":
            return {"evaluations": copy.deepcopy(self.policy.evaluations)}
        return super().control_op(op, body)

    def handle(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        parts = path.strip("/").split("/")
        if environ["REQUEST_METHOD"] != "GET" or len(parts) != 4 or \
                parts[0] != "tenants" or parts[2] != "files":
            return _respond(start_response, 404, {"error": "not_found"})
        tenant, name = parts[1], parts[3]
        # Request-derived attributes, standing in for a tool call's arguments.
        attributes = {k: v[0] if len(v) == 1 else v for k, v in
                      parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=True).items()}
        invalid = OAuthError("invalid_token", 401,
                             challenge='DPoP error="invalid_token", algs="ES256"')
        scheme, _, token = environ.get("HTTP_AUTHORIZATION", "").partition(" ")
        if scheme != "DPoP" or not token:
            raise OAuthError("invalid_request", 401, challenge='DPoP algs="ES256"')
        # Token validation (RFC 9068), or introspection for an opaque token.
        introspected = token.count(".") != 2
        try:
            claims, ras = self.introspect(token, invalid) if introspected else \
                self.validate_jwt(token, invalid)
        except IntrospectionUnavailable:
            if not self.on("api.introspection_unavailable"):
                raise invalid   # non-conforming: an outage read as an invalid token
            if self.on("api.established_failure"):
                # Token validation is unfinished, but a proof failure in the
                # same row is established without the response (core: Error
                # Responses); the key binding needs cnf, so it stays unchecked.
                if self.validate_dpop(environ, "GET", API_BASE + path, access_token=token,
                                      status=401) is None:
                    raise invalid
            raise OAuthError(None, 503, headers=[("Retry-After", str(RETRY_AFTER))])
        # Protection: DPoP proof, ath, and key binding.
        jkt = self.validate_dpop(environ, "GET", API_BASE + path, access_token=token, status=401)
        cnf = claims.get("cnf") if isinstance(claims.get("cnf"), dict) else {}
        if jkt is None or (cnf.get("jkt") != jkt and self.on("api.key_binding")):
            raise invalid
        # Applicability: the configured population for this client and
        # audience, never the presence or absence of act.
        aud = claims.get("aud")
        aud = aud[0] if isinstance(aud, list) and len(aud) == 1 else aud
        population = self.populations.get((claims.get("client_id"), aud))
        act = claims.get("act")
        if population == "delegated":
            if self.on("api.introspection_act" if introspected else "api.require_act") and \
                    not _valid_act(act, ras["namespaces"]):
                raise invalid
        elif population == "self-acting":
            if act is not None:   # a governed self-acting token has no act
                raise invalid
        else:
            raise invalid
        # Tenant from token context only.
        token_tenant = self.resource_tenants.get(aud)
        if token_tenant is None or (token_tenant != tenant and self.on("api.tenant")):
            raise invalid
        # Authorization of a valid token (core: Error Responses). Every
        # failing condition is recorded, and the first in the reporting
        # order is reported: the actor gate, then token authority, then any
        # other denial. failures maps each reason to the scope it lacks.
        order = self.order()
        failures = {}
        if "files.read" not in str(claims.get("scope", "")).split():
            # The token's scope, which no policy permit overrides.
            failures["authority"] = ["files.read"]
        agent = self.agent_identity(population, claims, act)
        incomplete = None
        if self.policy_service:
            # The policy service replaces the local evaluation below. Its
            # decision names the first failing condition in the API's order.
            request = self.evaluation_request(population, claims, agent, aud, token_tenant,
                                              name, attributes)
            # The first condition the service would evaluate, for an
            # evaluation that did not complete at all.
            first = next(r for r in order if population == "delegated" or r != "actor")
            try:
                decision = self.policy.evaluate(
                    request, order, skip_unavailable=not self.on("api.incomplete_outranks"),
                    complete_all=not self.on("api.established_failure"))
            except PolicyUnavailable:
                decision = {"incomplete": first}
            if isinstance(decision, dict) and decision.get("incomplete") in ERROR_ORDER:
                incomplete, decision = decision["incomplete"], {"decision": True}
            elif not self.interpretable(decision):
                incomplete, decision = first, {"decision": True}
            if decision["decision"] is not True:
                failures.setdefault(decision["reason"], [])
                if decision.get("scope"):
                    failures[decision["reason"]].append(decision["scope"])
        elif population == "delegated":
            user = claims.get("sub")
            if agent is not None and self.on("api.actor_gate") and \
                    (agent["iss"], agent["sub"], user, tenant) not in self.actor_gate:
                failures["actor"] = []
            if "read" not in self.permissions.get((user, tenant), set()):
                failures["other"] = []
        elif "read" not in self.agent_permissions.get((claims.get("sub"), tenant), set()):
            # Self-acting access: the agent's own permissions; no actor gate.
            failures["other"] = []
        if incomplete is not None:
            # An evaluation that could not complete is not a denial. A failure
            # is still reported when no unfinished check comes before it in
            # the reporting order; otherwise the response is HTTP 503.
            established = [r for r in order if r in failures]
            if not (established and self.on("api.established_failure") and
                    order.index(established[0]) <= order.index(incomplete)):
                if self.on("api.evaluation_unavailable"):
                    raise OAuthError(None, 503, headers=[("Retry-After", str(RETRY_AFTER))])
                failures.setdefault("other", [])   # non-conforming: treated as a denial
        if failures:
            reason = next(r for r in order if r in failures)
            raise self.denial(population, reason, failures[reason])
        data = self.files.get((tenant, name))
        if data is None:
            return _respond(start_response, 404, {"error": "not_found"})
        return _respond(start_response, 200, data, content_type="text/csv")

    def validate_jwt(self, token, invalid):
        """RFC 9068 validation under trusted RAS configuration; returns (claims, RAS)."""
        try:
            header, unverified, _, _ = jws.decode(token)
            ras = self.trusted_ras.get(unverified.get("iss"))
            if not _typ_is(header, "at+jwt") or ras is None:
                raise ValueError("typ or issuer")
            _, claims = jws.verify(token, ras["key"], "RS256")
        except ValueError:
            raise invalid
        if not _time_valid(claims, require_iat=True, check_future=self.on("api.token_time"),
                           now=self.now()):
            raise invalid
        return claims, ras

    def introspect(self, token, invalid):
        """Authenticated RFC 7662 introspection at the RAS; returns (response, RAS).

        The core's Optional Opaque Access Tokens and Introspection. The
        response stands in for validated claims; nothing caches it.
        """
        if self.introspection is None:
            raise invalid
        endpoint, client_id, secret = self.introspection
        credentials = base64.b64encode(
            f"{quote_plus(client_id)}:{quote_plus(secret)}".encode()).decode()
        req = urllib.request.Request(endpoint, data=urlencode({"token": token}).encode(),
                                     method="POST",
                                     headers={"Authorization": "Basic " + credentials,
                                              "Content-Type": "application/x-www-form-urlencoded",
                                              "Accept": "application/json"})
        # A call that does not return a JSON object with a boolean active
        # cannot complete validation: a transport failure, a timeout, any
        # error response from the endpoint (HTTPError is a URLError), an
        # HTTP protocol failure such as a truncated body (IncompleteRead),
        # or a body that is not such an object. It says nothing about the token.
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = json.loads(resp.read())
        except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError):
            raise IntrospectionUnavailable()
        if not isinstance(body, dict) or not isinstance(body.get("active"), bool):
            raise IntrospectionUnavailable()
        if body.get("active") is not True and self.on("api.introspection_active"):
            raise invalid
        if body.get("iss", RAS_ISSUER) != RAS_ISSUER:
            raise invalid
        # exp is optional in RFC 7662; where present it is enforced, as are iat and nbf.
        now, exp = self.now(), body.get("exp")
        if exp is not None and (not isinstance(exp, int) or exp + SKEW < now):
            raise invalid
        if self.on("api.token_time"):
            for value in (body.get("iat"), body.get("nbf")):
                if value is not None and (not isinstance(value, int) or value > now + SKEW):
                    raise invalid
        return body, self.trusted_ras[RAS_ISSUER]

    def agent_identity(self, population, claims, act):
        """The issuer-qualified agent for delegated access; None for self-acting access."""
        if population != "delegated":
            return None
        if not self.on("api.agent_from_token"):
            # Non-conforming: the client registration stands in for the agent.
            return copy.deepcopy(self.client_agents.get(claims.get("client_id")))
        return {"iss": act["iss"], "sub": act["sub"]} if isinstance(act, dict) else None

    def evaluation_request(self, population, claims, agent, aud, tenant, name, attributes):
        """The policy evaluation request (see PolicyService).

        The subject, agent, client, tenant and token constraints come from
        the validated token or introspection response and trusted
        configuration (core: Optional Policy Services). The request's own
        attributes go only in context.request.
        """
        # For self-acting access, the local principal stands for the Agent Principal.
        subject = {"type": "user" if population == "delegated" else "agent",
                   "id": claims.get("sub")}
        context = {"client": claims.get("client_id"), "tenant": tenant,
                   "constraints": {"scope": claims.get("scope"), "aud": aud},
                   "request": copy.deepcopy(attributes)}
        if population == "delegated":
            context["agent"] = copy.deepcopy(agent)
        request = {"subject": subject, "action": {"name": "read"},
                   "resource": {"type": "file", "id": name}, "context": context}
        if not self.on("api.policy_source"):
            # Non-conforming: request attributes supply or override the
            # identity, tenant and constraint members.
            given = {k: v for k, v in attributes.items()
                     if k in REQUEST_ATTRIBUTES and isinstance(v, str)}
            if "user" in given and population == "delegated":
                subject["id"] = given["user"]
            if "agent" in given:
                if population == "delegated":
                    context["agent"] = dict(context.get("agent") or {"iss": IDP_ISSUER},
                                            sub=given["agent"])
                else:
                    subject["id"] = given["agent"]
            if "client_id" in given:
                context["client"] = given["client_id"]
            if "tenant" in given:
                context["tenant"] = given["tenant"]
            if "scope" in given:
                context["constraints"]["scope"] = given["scope"]
        return request

    def order(self):
        """The reporting order for a valid token's denials (core: Error Responses)."""
        return ERROR_ORDER if self.on("api.error_order") else WRONG_ORDER

    @staticmethod
    def interpretable(decision):
        """A decision that permits, or denies and names a condition the API can report."""
        return isinstance(decision, dict) and isinstance(decision.get("decision"), bool) and \
            (decision["decision"] or decision.get("reason") in ERROR_ORDER)

    def denial(self, population, reason, scopes):
        """HTTP 403 for a valid token, by the first failing condition (core: Error Responses).

        The actor gate gets actor_unauthorized, and token authority gets
        insufficient_scope with the scope the operation needs. Any other
        denial gets a DPoP challenge without an error attribute, and an
        empty body.
        """
        if not self.on("api.denial_codes"):
            # Non-conforming: one code for every denial, actor_unauthorized
            # for a delegated token and insufficient_scope for a self-acting one.
            code = "actor_unauthorized" if population == "delegated" else "insufficient_scope"
            return OAuthError(code, 403, challenge=f'DPoP error="{code}", algs="ES256"')
        if reason == "actor":
            return OAuthError("actor_unauthorized", 403,
                              challenge='DPoP error="actor_unauthorized", algs="ES256"')
        if reason == "authority":
            scope = " ".join(dict.fromkeys(scopes))
            return OAuthError("insufficient_scope", 403,
                              challenge=f'DPoP error="insufficient_scope", scope="{scope}", '
                                        'algs="ES256"')
        return OAuthError(None, 403, challenge='DPoP algs="ES256"')


class _QuietHandler(WSGIRequestHandler):
    def log_message(self, *args):
        pass


def serve(app):
    """Serve a WSGI app on an ephemeral localhost port in a daemon thread."""
    httpd = make_server("127.0.0.1", 0, app, handler_class=_QuietHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_port}"


def start(client_keys):
    """Start the three reference servers; return their transport base URLs."""
    idp = IdP({"analysis-client": client_keys["analysis-client"].public_key()})
    # The API's introspection credential at the RAS, generated at start.
    secret = secrets.token_urlsafe(32)
    ras = RAS({cid: client_keys[cid].public_key() for cid in ("analysis-api", "other-api")},
              idp.key.public_key(), {INTROSPECTION_CLIENT: secret})
    api = API(ras.key.public_key())
    servers = {name: serve(app) for name, app in (("idp", idp), ("ras", ras), ("api", api))}
    urls = {name: url for name, (_, url) in servers.items()}
    # The API introspects over HTTP at the RAS's transport.
    api.introspection = (urls["ras"] + "/introspect", INTROSPECTION_CLIENT, secret)
    return urls, [s for s, _ in servers.values()]
