"""Reference IdP, RAS and API for the mandatory delegated path (EXAMPLES scene 2).

Test-only. State is in memory, keys are generated at start, there is no
TLS, and nothing persists. The servers exist so the conformance suite has
a first implementation to run against; they implement only what scene 2
exercises: a dedicated client using private_key_jwt, an ID Token subject,
bound governed agent access (DPoP at both token endpoints), JWT access
tokens validated at the API, no refresh, no introspection.

Every check the negative cases exercise has a name (see CHECKS). The
runner's vacuity mode switches one off to show that the case that cites
it fails without it.

Each server also exposes POST /_test/<op> for the test-control adapter.
A third-party implementation supplies its own adapter instead.
"""
import json
import threading
import time
import uuid
from urllib.parse import parse_qs
from wsgiref.simple_server import WSGIRequestHandler, make_server

import jws

SKEW = 60          # seconds of clock skew allowed on time claims
DPOP_WINDOW = 60   # seconds a DPoP proof's iat may differ from now
GRANT_LIFETIME = 300
ACCESS_TOKEN_LIFETIME = 600

TOKEN_EXCHANGE = "urn:ietf:params:oauth:grant-type:token-exchange"
JWT_BEARER = "urn:ietf:params:oauth:grant-type:jwt-bearer"
ID_JAG_TYPE = "urn:ietf:params:oauth:token-type:id-jag"
ID_TOKEN_TYPE = "urn:ietf:params:oauth:token-type:id_token"
ASSERTION_TYPE = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"

IDP_ISSUER = "https://idp.example/"
RAS_ISSUER = "https://ras.example/"
API_BASE = "https://api.example"
RESOURCE = "https://api.example/tenants/acme-data/"
OTHER_RESOURCE = "https://api.example/tenants/beta-data/"

CHECKS = {
    "idp.client_assertion_audience": "client assertion aud is the IdP issuer only",
    "idp.client_assertion_replay": "client assertion jti is not reused",
    "idp.require_dpop": "bound profile requires a DPoP proof at issuance",
    "idp.single_resource": "exactly one resource parameter",
    "idp.id_token_audience": "ID Token audience is the authenticated client",
    "idp.binding_enabled": "Identity Binding is enabled",
    "idp.agent_active": "Agent Principal is active",
    "idp.client_association": "Client Association permits delegated use of the binding",
    "idp.delegation": "Delegation Authorization permits the agent for the user",
    "ras.client_id": "grant client_id matches the authenticated client",
    "ras.require_cnf": "bound profile requires cnf.jkt in the grant",
    "ras.require_proof": "a grant with cnf requires a DPoP proof",
    "ras.proof_key_match": "the redemption proof key matches cnf.jkt",
    "ras.resource_match": "the resource parameter equals the grant's resource",
    "ras.agent_eligibility": "the correlated agent record exists and is active",
    "ras.actor_gate": "RAS policy permits the agent to act for the user",
    "ras.actor_preservation": "act is copied unchanged into the access token",
    "api.key_binding": "the DPoP proof key matches the token's cnf.jkt",
    "api.require_act": "a governed delegated token carries a valid act",
    "api.tenant": "the token's tenant matches the requested tenant",
    "api.actor_gate": "API policy permits the agent to act for the user",
}


class OAuthError(Exception):
    def __init__(self, error, status=400, description=None, challenge=None):
        super().__init__(error)
        self.error, self.status = error, status
        self.description, self.challenge = description, challenge


def _respond(start_response, status, body, headers=None, content_type="application/json"):
    reasons = {200: "OK", 400: "Bad Request", 401: "Unauthorized",
               403: "Forbidden", 404: "Not Found", 405: "Method Not Allowed"}
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

    def reset(self):
        self.disabled = set()
        self.assertion_replay, self.proof_replay = {}, {}

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        try:
            with self.lock:
                if path.startswith("/_test/"):
                    body = json.loads(_read_body(environ) or b"{}")
                    return _respond(start_response, 200,
                                    self.control(path[len("/_test/"):], body) or {})
                return self.handle(environ, start_response)
        except OAuthError as err:
            body = {"error": err.error}
            if err.description:
                body["error_description"] = err.description
            headers = [("WWW-Authenticate", err.challenge)] if err.challenge else []
            return _respond(start_response, err.status, body, headers)

    def control(self, op, body):
        if op == "reset":
            self.reset()
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
        now = time.time()
        if claims.get("sub") != client_id:
            raise OAuthError("invalid_client")
        if self.on(f"{check_prefix}.client_assertion_audience") and \
                not _single_audience(claims.get("aud"), audience):
            raise OAuthError("invalid_client", description="aud must be the issuer")
        exp, iat, jti = claims.get("exp"), claims.get("iat"), claims.get("jti")
        if not isinstance(exp, int) or exp + SKEW < now or not jti or \
                (isinstance(iat, int) and iat > now + SKEW):
            raise OAuthError("invalid_client")
        key = (client_id, jti)
        if key in self.assertion_replay and self.assertion_replay[key] > now and \
                self.on(f"{check_prefix}.client_assertion_replay"):
            raise OAuthError("invalid_client", description="assertion reused")
        self.assertion_replay[key] = exp + SKEW
        return client_id

    def validate_dpop(self, environ, method, htu, access_token=None, status=400):
        """RFC 9449 Section 4.3 proof checks; returns the key thumbprint or None."""
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
        now = time.time()
        iat = payload.get("iat")
        if payload.get("htm") != method or payload.get("htu") != htu or \
                not isinstance(iat, int) or abs(iat - now) > DPOP_WINDOW or \
                not payload.get("jti") or payload["jti"] in self.proof_replay:
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
        self.delegations = {("agent-42", "alice", "analysis-client", RESOURCE): {"files.read"}}
        self.targets = {RAS_ISSUER: {"resources": {RESOURCE: "acme-data"},
                                     "registrations": {"analysis-client": "analysis-api"}}}

    def control_op(self, op, body):
        if op == "id_token":
            now = int(time.time())
            claims = {"iss": self.issuer, "sub": body.get("user", "alice"),
                      "aud": body.get("aud", "analysis-client"), "iat": now,
                      "exp": now + int(body.get("lifetime", 3900))}
            return {"id_token": jws.sign({"typ": "JWT", "kid": self.kid}, claims, self.key)}
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
        requested = scope.split()
        granted = [s for s in requested if delegation is None or s in delegation]
        if not granted:
            raise OAuthError("invalid_scope")
        now = int(time.time())
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
        exp = claims.get("exp")
        if claims.get("iss") != self.issuer or not isinstance(exp, int) or \
                exp + SKEW < time.time() or claims.get("sub") not in self.users:
            raise OAuthError("invalid_grant")
        if client_id not in audiences and self.on("idp.id_token_audience"):
            raise OAuthError("invalid_grant")
        return claims["sub"], exp

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


class RAS(Server):
    """Grant Redemption at the RAS for an ID-JAG, issuing DPoP-bound JWT access tokens."""

    def __init__(self, client_keys, idp_public_key):
        self.issuer, self.token_endpoint = RAS_ISSUER, RAS_ISSUER + "token"
        self.key, self.kid = jws.new_rsa_key(), "ras-key-1"
        self.client_keys, self.idp_public_key = client_keys, idp_public_key
        super().__init__()

    def reset(self):
        super().reset()
        self.clients = {cid: {"key": key, "profile": "bound"}
                        for cid, key in self.client_keys.items()}
        self.trusted_idps = {IDP_ISSUER: self.idp_public_key}
        self.resources = {RESOURCE: {"tenant": "acme-data", "protection": "dpop"}}
        self.user_links = {(IDP_ISSUER, "acme-data", "alice-ras"): "user-108"}
        self.agents = {(IDP_ISSUER, "agent-42"): {"local": "service-principal-42", "active": True}}
        self.actor_gate = {("user-108", IDP_ISSUER, "agent-42", "acme-data")}
        self.accepted_grants = {}

    def control_op(self, op, body):
        if op == "set":
            what, value = body["what"], body["value"]
            if what == "agent_active":
                self.agents[(IDP_ISSUER, "agent-42")]["active"] = value
            elif what == "actor_gate":
                entry = ("user-108", IDP_ISSUER, "agent-42", "acme-data")
                (self.actor_gate.add if value else self.actor_gate.discard)(entry)
            else:
                raise OAuthError("invalid_request", 404, "unknown setting")
            return {}
        if op == "mint_access_token":
            now = int(time.time())
            claims = {"iss": self.issuer, "iat": now, "exp": now + ACCESS_TOKEN_LIFETIME,
                      "jti": uuid.uuid4().hex}
            claims.update(body["claims"])
            return {"access_token": jws.sign({"typ": "at+jwt", "kid": self.kid},
                                             claims, self.key)}
        return super().control_op(op, body)

    def handle(self, environ, start_response):
        if environ.get("PATH_INFO") != "/token" or environ["REQUEST_METHOD"] != "POST":
            return _respond(start_response, 404, {"error": "not_found"})
        form = _form(environ)
        if form.get("grant_type") != [JWT_BEARER]:
            raise OAuthError("unsupported_grant_type")
        client_id = self.authenticate_client(form, self.clients, self.issuer, "ras")
        jkt = self.validate_dpop(environ, "POST", self.token_endpoint)
        claims = self.validate_grant(_one(form, "assertion"))
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
        # Replay: this reference accepts each grant once, bound or not, and
        # records a grant as accepted only when it issues an access token.
        grant_key, now = (claims["iss"], claims["jti"]), time.time()
        if self.accepted_grants.get(grant_key, 0) > now:
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
            raise OAuthError("invalid_grant", description="scope claim")
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
        return _respond(start_response, 200, {"access_token": token, "token_type": "DPoP",
                                              "expires_in": ACCESS_TOKEN_LIFETIME,
                                              "scope": scope})

    def validate_grant(self, assertion):
        """ID-JAG validation (ID-JAG Section 4.4.1, RFC 7523 Section 3)."""
        try:
            header, unverified, _, _ = jws.decode(assertion)
            if header.get("typ") != "oauth-id-jag+jwt":
                raise ValueError("typ")
            key = self.trusted_idps.get(unverified.get("iss"))
            if key is None:
                raise ValueError("untrusted issuer")
            _, claims = jws.verify(assertion, key, "RS256")
        except ValueError:
            raise OAuthError("invalid_grant")
        now = time.time()
        exp = claims.get("exp")
        if not _single_audience(claims.get("aud"), self.issuer) or \
                not isinstance(exp, int) or exp + SKEW < now or not claims.get("jti") or \
                (isinstance(claims.get("iat"), int) and claims["iat"] > now + SKEW):
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


class API(Server):
    """Access at the Resource Server for DPoP-bound JWT access tokens (RFC 9068)."""

    def __init__(self, ras_public_key):
        self.ras_public_key = ras_public_key
        super().__init__()

    def reset(self):
        super().reset()
        self.trusted_ras = {RAS_ISSUER: {"key": self.ras_public_key, "namespaces": {IDP_ISSUER}}}
        self.resource_tenants = {RESOURCE: "acme-data", OTHER_RESOURCE: "beta-data"}
        self.populations = {("analysis-api", RESOURCE): "delegated",
                            ("analysis-api", OTHER_RESOURCE): "delegated"}
        self.permissions = {("user-108", "acme-data"): {"read"},
                            ("user-108", "beta-data"): {"read"}}
        self.actor_gate = {(IDP_ISSUER, "agent-42", "user-108", "acme-data"),
                           (IDP_ISSUER, "agent-42", "user-108", "beta-data")}
        self.files = {("acme-data", "report-7"): b"region,revenue\nnorth,1200\nsouth,950\n",
                      ("beta-data", "report-9"): b"region,revenue\neast,700\n"}

    def control_op(self, op, body):
        if op == "set" and body["what"] == "actor_gate":
            entry = (IDP_ISSUER, "agent-42", "user-108", "acme-data")
            (self.actor_gate.add if body["value"] else self.actor_gate.discard)(entry)
            return {}
        return super().control_op(op, body)

    def handle(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        parts = path.strip("/").split("/")
        if environ["REQUEST_METHOD"] != "GET" or len(parts) != 4 or \
                parts[0] != "tenants" or parts[2] != "files":
            return _respond(start_response, 404, {"error": "not_found"})
        tenant, name = parts[1], parts[3]
        invalid = OAuthError("invalid_token", 401,
                             challenge='DPoP error="invalid_token", algs="ES256"')
        scheme, _, token = environ.get("HTTP_AUTHORIZATION", "").partition(" ")
        if scheme != "DPoP" or not token:
            raise OAuthError("invalid_request", 401, challenge='DPoP algs="ES256"')
        # Token validation (RFC 9068) under trusted RAS configuration.
        try:
            header, unverified, _, _ = jws.decode(token)
            ras = self.trusted_ras.get(unverified.get("iss"))
            if header.get("typ") != "at+jwt" or ras is None:
                raise ValueError("typ or issuer")
            _, claims = jws.verify(token, ras["key"], "RS256")
        except ValueError:
            raise invalid
        if not isinstance(claims.get("exp"), int) or claims["exp"] + SKEW < time.time():
            raise invalid
        # Protection: DPoP proof, ath, and key binding.
        jkt = self.validate_dpop(environ, "GET", API_BASE + path, access_token=token, status=401)
        cnf = claims.get("cnf") if isinstance(claims.get("cnf"), dict) else {}
        if jkt is None or (cnf.get("jkt") != jkt and self.on("api.key_binding")):
            raise invalid
        # Applicability: the configured population for this client and audience.
        aud = claims.get("aud")
        aud = aud[0] if isinstance(aud, list) and len(aud) == 1 else aud
        if self.populations.get((claims.get("client_id"), aud)) != "delegated":
            raise invalid
        act = claims.get("act")
        if self.on("api.require_act"):
            if not isinstance(act, dict) or "act" in act or \
                    not isinstance(act.get("iss"), str) or not act["iss"] or \
                    not isinstance(act.get("sub"), str) or not act["sub"] or \
                    act["iss"] not in ras["namespaces"]:
                raise invalid
        # Tenant from token context only.
        token_tenant = self.resource_tenants.get(aud)
        if token_tenant is None or (token_tenant != tenant and self.on("api.tenant")):
            raise invalid
        # Authority: scope, user permission, actor gate.
        if "files.read" not in str(claims.get("scope", "")).split():
            raise OAuthError("insufficient_scope", 403,
                             challenge='DPoP error="insufficient_scope", scope="files.read", algs="ES256"')
        user = claims.get("sub")
        if "read" not in self.permissions.get((user, tenant), set()):
            return _respond(start_response, 403, {"error": "forbidden"})
        if isinstance(act, dict) and self.on("api.actor_gate") and \
                (act.get("iss"), act.get("sub"), user, tenant) not in self.actor_gate:
            raise OAuthError("actor_unauthorized", 403,
                             challenge='DPoP error="actor_unauthorized", algs="ES256"')
        data = self.files.get((tenant, name))
        if data is None:
            return _respond(start_response, 404, {"error": "not_found"})
        return _respond(start_response, 200, data, content_type="text/csv")


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
    ras = RAS({cid: client_keys[cid].public_key() for cid in ("analysis-api", "other-api")},
              idp.key.public_key())
    api = API(ras.key.public_key())
    servers = {name: serve(app) for name, app in (("idp", idp), ("ras", ras), ("api", api))}
    return {name: url for name, (_, url) in servers.items()}, [s for s, _ in servers.values()]
