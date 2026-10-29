"""Black-box conformance cases for the mandatory delegated path (EXAMPLES scene 2).

The suite plays the client role over HTTP against an IdP, a RAS and an API.
Each case names the role it checks, the draft text it comes from, and any
test-control capability it needs from the deployment's Adapter. Cases that
need no adapter capability beyond an ID Token run against any deployment
with the configured identities.
"""
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from urllib.parse import urlencode, urlsplit

import jws

TOKEN_EXCHANGE = "urn:ietf:params:oauth:grant-type:token-exchange"
JWT_BEARER = "urn:ietf:params:oauth:grant-type:jwt-bearer"
ID_JAG_TYPE = "urn:ietf:params:oauth:token-type:id-jag"
ID_TOKEN_TYPE = "urn:ietf:params:oauth:token-type:id_token"
ASSERTION_TYPE = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"


@dataclass
class Endpoint:
    issuer: str          # issuer identifier; client assertions use it as aud
    token_endpoint: str  # as the server identifies itself; DPoP htu uses it
    transport: str       # base URL the suite connects to


@dataclass
class Config:
    idp: Endpoint
    ras: Endpoint
    api_base: str        # the API's own origin; DPoP htu uses it
    api_transport: str
    resource: str
    other_resource: str  # another tenant's resource where the user and agent also have rights
    read_path: str
    other_tenant_path: str
    idp_client_id: str
    idp_client_key: object
    ras_client_id: str
    ras_client_key: object
    other_ras_client_id: str
    other_ras_client_key: object
    user: str
    scope: str
    expect: dict = field(default_factory=dict)  # agent_iss, agent, grant_sub, token_sub


class Response:
    def __init__(self, status, body, headers):
        self.status, self.body, self.headers = status, body, headers

    def json(self):
        try:
            value = json.loads(self.body)
            return value if isinstance(value, dict) else {}
        except ValueError:
            return {}

    def __repr__(self):
        return f"HTTP {self.status} {self.body[:200]!r}"


def http(method, url, form=None, headers=None):
    data = urlencode(form, doseq=True).encode() if form is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=dict(headers or {}))
    if data is not None:
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return Response(resp.status, resp.read(), resp.headers)
    except urllib.error.HTTPError as err:
        return Response(err.code, err.read(), err.headers)


class Client:
    """The client role of scene 2: one grant proof key K, and a second key for mismatches."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.k, self.k2 = jws.new_ec_key(), jws.new_ec_key()

    def exchange(self, id_token, dpop_key="k", assertion=None, resources=None,
                 assertion_aud=None):
        cfg = self.cfg
        assertion = assertion or jws.client_assertion(
            cfg.idp_client_key, cfg.idp_client_id, assertion_aud or cfg.idp.issuer)
        form = {"grant_type": TOKEN_EXCHANGE, "requested_token_type": ID_JAG_TYPE,
                "client_id": cfg.idp_client_id, "client_assertion_type": ASSERTION_TYPE,
                "client_assertion": assertion, "subject_token": id_token,
                "subject_token_type": ID_TOKEN_TYPE, "audience": cfg.ras.issuer,
                "resource": resources or [cfg.resource], "scope": cfg.scope}
        headers = {}
        if dpop_key:
            headers["DPoP"] = jws.dpop_proof(getattr(self, dpop_key), "POST",
                                             cfg.idp.token_endpoint)
        return http("POST", cfg.idp.transport + urlsplit(cfg.idp.token_endpoint).path,
                    form, headers)

    def redeem(self, grant, dpop_key="k", resource=None, as_other_client=False):
        cfg = self.cfg
        client_id = cfg.other_ras_client_id if as_other_client else cfg.ras_client_id
        key = cfg.other_ras_client_key if as_other_client else cfg.ras_client_key
        form = {"grant_type": JWT_BEARER, "client_id": client_id,
                "client_assertion_type": ASSERTION_TYPE,
                "client_assertion": jws.client_assertion(key, client_id, cfg.ras.issuer),
                "assertion": grant, "resource": resource or cfg.resource}
        headers = {}
        if dpop_key:
            headers["DPoP"] = jws.dpop_proof(getattr(self, dpop_key), "POST",
                                             cfg.ras.token_endpoint)
        return http("POST", cfg.ras.transport + urlsplit(cfg.ras.token_endpoint).path,
                    form, headers)

    def get(self, path, token, dpop_key="k"):
        proof = jws.dpop_proof(getattr(self, dpop_key), "GET", self.cfg.api_base + path,
                               access_token=token)
        return http("GET", self.cfg.api_transport + path,
                    headers={"Authorization": f"DPoP {token}", "DPoP": proof})


class Adapter:
    """Test-control contract. A deployment under test supplies an implementation.

    id_token(user, aud=None)       an ID Token for the user, for the IdP client
                                   unless aud names another audience
    set(role, what, value)         change one relationship or setting:
                                     idp: binding_enabled, agent_active,
                                          client_association, delegation,
                                          client_profile ("bound" or "governed")
                                     ras: agent_active, actor_gate
                                     api: actor_gate
    mint_access_token(claims)      an access token the RAS signs with these claims
    reset()                        restore the scene 1 configuration
    disable_check(role, name)      reference implementation only (vacuity mode)
    """

    def reset(self):
        raise NotImplementedError

    def id_token(self, user, aud=None):
        raise NotImplementedError

    def set(self, role, what, value):
        raise NotImplementedError

    def mint_access_token(self, claims):
        raise NotImplementedError

    def disable_check(self, role, name):
        raise NotImplementedError


class ReferenceAdapter(Adapter):
    """Adapter for the reference servers' POST /_test/<op> endpoints."""

    def __init__(self, transports):
        self.transports = transports

    def _call(self, role, op, body=None):
        req = urllib.request.Request(f"{self.transports[role]}/_test/{op}",
                                     data=json.dumps(body or {}).encode(), method="POST",
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read() or b"{}")
        except urllib.error.HTTPError as err:
            raise RuntimeError(f"test control {role}/{op}: HTTP {err.code} {err.read()!r}")

    def reset(self):
        for role in ("idp", "ras", "api"):
            self._call(role, "reset")

    def id_token(self, user, aud=None):
        body = {"user": user}
        if aud:
            body["aud"] = aud
        return self._call("idp", "id_token", body)["id_token"]

    def set(self, role, what, value):
        self._call(role, "set", {"what": what, "value": value})

    def mint_access_token(self, claims):
        return self._call("ras", "mint_access_token", {"claims": claims})["access_token"]

    def disable_check(self, role, name):
        self._call(role, "disable_check", {"name": name})


@dataclass
class Case:
    id: str
    role: str
    title: str
    source: str
    run: object
    needs: tuple = ()
    defeats: tuple = ()


CASES = []


def case(id, role, title, source, needs=(), defeats=()):
    def register(fn):
        CASES.append(Case(id, role, title, source, fn, tuple(needs), tuple(defeats)))
        return fn
    return register


class Context:
    def __init__(self, cfg, adapter):
        self.cfg, self.adapter, self.client = cfg, adapter, Client(cfg)
        self.notes = []

    def id_token(self, aud=None):
        return self.adapter.id_token(self.cfg.user, aud)

    def grant(self, dpop_key="k"):
        resp = self.client.exchange(self.id_token(), dpop_key=dpop_key)
        check(resp.status == 200, f"exchange failed: {resp}")
        return resp.json()["access_token"]

    def access_token(self):
        resp = self.client.redeem(self.grant())
        check(resp.status == 200, f"redemption failed: {resp}")
        return resp.json()["access_token"]


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def expect_error(resp, status, error):
    body = resp.json()
    check(resp.status == status and body.get("error") == error,
          f"expected HTTP {status} {error}, got {resp}")
    check("access_token" not in body, "an error response carried a token")


def expect_challenge(resp, status, error):
    challenge = resp.headers.get("WWW-Authenticate", "") if resp.headers else ""
    check(resp.status == status and challenge.startswith("DPoP") and
          f'error="{error}"' in challenge,
          f"expected HTTP {status} with a DPoP {error} challenge, got {resp} {challenge!r}")


def expect_rejected(ctx, resp):
    """For a rejection whose error code the drafts do not fix: a 4xx and no token."""
    body = resp.json()
    check(400 <= resp.status < 500 and "access_token" not in body,
          f"expected a rejection with no token, got {resp}")
    ctx.notes.append(f"error code observed: {body.get('error')!r} (the drafts do not fix one)")


# Positive path -------------------------------------------------------------

@case("P1", "IdP", "Issues a DPoP-bound ID-JAG naming the agent as actor",
      "core: Actor Resolution and Construction; Grant Issuance; Common Grant Claims")
def p1(ctx):
    cfg, id_token = ctx.cfg, ctx.id_token()
    resp = ctx.client.exchange(id_token)
    check(resp.status == 200, f"exchange failed: {resp}")
    body = resp.json()
    check(body.get("issued_token_type") == ID_JAG_TYPE, "issued_token_type")
    check(body.get("token_type") == "N_A", "token_type")
    header, grant, _, _ = jws.decode(body["access_token"])
    _, subject, _, _ = jws.decode(id_token)
    check(header.get("typ") == "oauth-id-jag+jwt", "typ")
    check(grant.get("iss") == cfg.idp.issuer, "iss")
    check(grant.get("aud") == cfg.ras.issuer, "aud")
    check(grant.get("sub") == cfg.expect["grant_sub"], "sub is the user in the RAS namespace")
    check(grant.get("client_id") == cfg.ras_client_id, "client_id is the RAS registration")
    check(grant.get("resource") == cfg.resource, "resource")
    check(grant.get("scope") == cfg.scope, "scope")
    check(grant.get("act") == {"iss": cfg.expect["agent_iss"], "sub": cfg.expect["agent"]},
          f"act names the Agent Principal: {grant.get('act')}")
    check(grant.get("cnf") == {"jkt": jws.thumbprint(jws.public_jwk(ctx.client.k))},
          "cnf.jkt is the grant proof key")
    check(grant["exp"] - grant["iat"] <= 300, "grant lifetime at most 300 s")
    check(grant["exp"] <= subject["exp"], "grant does not outlive the ID Token")


@case("P2", "RAS", "Redeems the grant for a DPoP-bound access token that keeps act unchanged",
      "core: Actor Preservation; Access Token Issuance and Response; Access-Token Protection",
      defeats=("ras.actor_preservation",))
def p2(ctx):
    cfg, grant = ctx.cfg, ctx.grant()
    resp = ctx.client.redeem(grant)
    check(resp.status == 200, f"redemption failed: {resp}")
    body = resp.json()
    check(body.get("token_type") == "DPoP", "token_type DPoP")
    check("refresh_token" not in body, "no refresh token")
    header, token, _, _ = jws.decode(body["access_token"])
    _, grant_claims, _, _ = jws.decode(grant)
    check(header.get("typ") == "at+jwt", "typ at+jwt")
    check(token.get("sub") == cfg.expect["token_sub"], "sub is the local user")
    check(token.get("act") == grant_claims["act"], f"act unchanged: {token.get('act')}")
    check(token.get("client_id") == cfg.ras_client_id, "client_id")
    check(token.get("aud") == cfg.resource, "aud is the tenant resource")
    check(token.get("cnf") == {"jkt": jws.thumbprint(jws.public_jwk(ctx.client.k))},
          "access token bound to the same key")


@case("P3", "API", "Serves a read to the bound access token with a fresh proof",
      "core: Token Validation; Delegated Access")
def p3(ctx):
    resp = ctx.client.get(ctx.cfg.read_path, ctx.access_token())
    check(resp.status == 200, f"read failed: {resp}")


# IdP rejections ------------------------------------------------------------

@case("N01", "IdP", "Rejects a reused client assertion as a client-authentication failure",
      "core: Dedicated Client Identity (Replay); Renewal and Negative Tests, nonce-retry row",
      defeats=("idp.client_assertion_replay",))
def n01(ctx):
    cfg = ctx.cfg
    assertion = jws.client_assertion(cfg.idp_client_key, cfg.idp_client_id, cfg.idp.issuer)
    first = ctx.client.exchange(ctx.id_token(), assertion=assertion)
    check(first.status == 200, f"first exchange failed: {first}")
    expect_error(ctx.client.exchange(ctx.id_token(), assertion=assertion), 400, "invalid_client")


@case("N02", "IdP", "Rejects a client assertion addressed to the token endpoint URL",
      "core: Dedicated Client Identity (Audience)",
      defeats=("idp.client_assertion_audience",))
def n02(ctx):
    resp = ctx.client.exchange(ctx.id_token(), assertion_aud=ctx.cfg.idp.token_endpoint)
    expect_error(resp, 400, "invalid_client")


@case("N03", "IdP", "Rejects an exchange without a DPoP proof under the bound profile",
      "core: Grant Protection", defeats=("idp.require_dpop",))
def n03(ctx):
    expect_error(ctx.client.exchange(ctx.id_token(), dpop_key=None), 400, "invalid_request")


@case("N04", "IdP", "Rejects more than one resource parameter",
      "core: Token Exchange Request (Resource)", defeats=("idp.single_resource",))
def n04(ctx):
    resp = ctx.client.exchange(ctx.id_token(),
                               resources=[ctx.cfg.resource, ctx.cfg.other_resource])
    expect_error(resp, 400, "invalid_target")


@case("N05", "IdP", "Rejects an ID Token issued to another client",
      "core: Subject Token Validation; ID-JAG Section 4.3.3",
      defeats=("idp.id_token_audience",))
def n05(ctx):
    expect_error(ctx.client.exchange(ctx.id_token(aud="another-client")), 400, "invalid_grant")


@case("N06", "IdP", "Rejects issuance when the Identity Binding is disabled",
      "core: Renewal and Negative Tests, Identity Binding disabled",
      needs=("set:idp.binding_enabled",), defeats=("idp.binding_enabled",))
def n06(ctx):
    ctx.adapter.set("idp", "binding_enabled", False)
    expect_error(ctx.client.exchange(ctx.id_token()), 400, "invalid_grant")


@case("N07", "IdP", "Rejects issuance for a disabled Agent Principal",
      "core: Issuance Errors; PLAYBOOK: Disable an agent everywhere, verification",
      needs=("set:idp.agent_active",), defeats=("idp.agent_active",))
def n07(ctx):
    ctx.adapter.set("idp", "agent_active", False)
    expect_error(ctx.client.exchange(ctx.id_token()), 400, "invalid_grant")


@case("N08", "IdP", "Refuses the actor when no Client Association permits the client",
      "core: Renewal and Negative Tests, Client Association disabled",
      needs=("set:idp.client_association",), defeats=("idp.client_association",))
def n08(ctx):
    ctx.adapter.set("idp", "client_association", False)
    expect_error(ctx.client.exchange(ctx.id_token()), 400, "actor_unauthorized")


@case("N09", "IdP", "Refuses the actor when the user's Delegation Authorization is withdrawn",
      "core: Delegation Authorization; PLAYBOOK: delegated recipe, rejection tests",
      needs=("set:idp.delegation",), defeats=("idp.delegation",))
def n09(ctx):
    ctx.adapter.set("idp", "delegation", False)
    expect_error(ctx.client.exchange(ctx.id_token()), 400, "actor_unauthorized")


# RAS rejections ------------------------------------------------------------

@case("N10", "RAS", "Rejects a grant without cnf when the bound profile is required",
      "core: Renewal and Negative Tests, grant has no cnf",
      needs=("set:idp.client_profile",), defeats=("ras.require_cnf",))
def n10(ctx):
    ctx.adapter.set("idp", "client_profile", "governed")
    grant = ctx.grant(dpop_key=None)
    check("cnf" not in jws.decode(grant)[1], "setup: the IdP issued a grant with cnf")
    expect_error(ctx.client.redeem(grant), 400, "invalid_grant")


@case("N11", "RAS", "Rejects redemption of a bound grant without a DPoP proof",
      "core: Renewal and Negative Tests, redemption omits the proof",
      defeats=("ras.require_proof",))
def n11(ctx):
    expect_error(ctx.client.redeem(ctx.grant(), dpop_key=None), 400, "invalid_grant")


@case("N12", "RAS", "Rejects redemption proven with a key other than the grant's",
      "core: Grant Protection (key mismatch); ID-JAG Section 9.8.1.2",
      defeats=("ras.proof_key_match",))
def n12(ctx):
    expect_error(ctx.client.redeem(ctx.grant(), dpop_key="k2"), 400, "invalid_grant")


@case("N13", "RAS", "Rejects a grant redeemed by a client other than its client_id",
      "core: Redemption Request; ID-JAG Section 4.4.1", defeats=("ras.client_id",))
def n13(ctx):
    expect_error(ctx.client.redeem(ctx.grant(), as_other_client=True), 400, "invalid_grant")


@case("N14", "RAS", "Rejects a resource parameter that differs from the grant's resource",
      "core: Common Grant Validation (Requested resource)", defeats=("ras.resource_match",))
def n14(ctx):
    resp = ctx.client.redeem(ctx.grant(), resource=ctx.cfg.other_resource)
    expect_error(resp, 400, "invalid_target")


@case("N15", "RAS", "Denies redemption for an agent disabled at the RAS",
      "core: Agent Principal Correlation; Applied Disablement and Revocation",
      needs=("set:ras.agent_active",), defeats=("ras.agent_eligibility",))
def n15(ctx):
    grant = ctx.grant()
    ctx.adapter.set("ras", "agent_active", False)
    expect_rejected(ctx, ctx.client.redeem(grant))


@case("N16", "RAS", "Denies redemption when RAS policy does not let the agent act for the user",
      "core: Delegated Actor Authorization (actor gate at the RAS)",
      needs=("set:ras.actor_gate",), defeats=("ras.actor_gate",))
def n16(ctx):
    grant = ctx.grant()
    ctx.adapter.set("ras", "actor_gate", False)
    expect_rejected(ctx, ctx.client.redeem(grant))


# API rejections ------------------------------------------------------------

@case("N17", "API", "Rejects an access token used in another tenant, even with a fresh proof",
      "core: Renewal and Negative Tests, another tenant", defeats=("api.tenant",))
def n17(ctx):
    resp = ctx.client.get(ctx.cfg.other_tenant_path, ctx.access_token())
    expect_challenge(resp, 401, "invalid_token")


@case("N18", "API", "Rejects a delegated-population access token without act",
      "core: Renewal and Negative Tests, missing act; Profile Applicability",
      needs=("mint_access_token",), defeats=("api.require_act",))
def n18(ctx):
    cfg = ctx.cfg
    token = ctx.adapter.mint_access_token({
        "sub": cfg.expect["token_sub"], "aud": cfg.resource, "client_id": cfg.ras_client_id,
        "scope": cfg.scope, "cnf": {"jkt": jws.thumbprint(jws.public_jwk(ctx.client.k))}})
    expect_challenge(ctx.client.get(cfg.read_path, token), 401, "invalid_token")


@case("N19", "API", "Rejects a request proven with a key other than the token's",
      "core: Token Validation (Protection); RFC 9449 Section 7.1",
      defeats=("api.key_binding",))
def n19(ctx):
    resp = ctx.client.get(ctx.cfg.read_path, ctx.access_token(), dpop_key="k2")
    expect_challenge(resp, 401, "invalid_token")


@case("N20", "API", "Denies the actor with actor_unauthorized, not insufficient_scope",
      "core: Error Responses; Delegated Actor Authorization",
      needs=("set:api.actor_gate",), defeats=("api.actor_gate",))
def n20(ctx):
    token = ctx.access_token()
    ctx.adapter.set("api", "actor_gate", False)
    expect_challenge(ctx.client.get(ctx.cfg.read_path, token), 403, "actor_unauthorized")


def run_case(c, cfg, adapter, disable=()):
    """Run one case from a reset deployment; return (passed, detail, notes)."""
    adapter.reset()
    for name in disable:
        adapter.disable_check(name.split(".")[0], name)
    ctx = Context(cfg, adapter)
    try:
        c.run(ctx)
        return True, "", ctx.notes
    except AssertionError as err:
        return False, str(err), ctx.notes


def wait_ready(cfg, timeout=5):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            http("GET", cfg.api_transport + "/")
            return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError("servers did not start")
