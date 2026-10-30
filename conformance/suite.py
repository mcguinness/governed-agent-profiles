"""Black-box conformance cases for the mandatory delegated path (EXAMPLES scene 2).

The suite plays the client role over HTTP against an IdP, a RAS and an API.
Each case names the role it checks, the draft text it comes from, and any
test-control capability it needs from the deployment's Adapter. Cases that
need no adapter capability beyond an ID Token run against any deployment
with the configured identities.

The D cases test deferred redemption at the RAS. Most of them approve,
deny or revoke through the RAS's Access Request Service, or advance the
clock, so they are reference-implementation tests rather than black-box
conformance cases.
"""
import json
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from urllib.parse import urlencode, urlsplit

import jws

TOKEN_EXCHANGE = "urn:ietf:params:oauth:grant-type:token-exchange"
JWT_BEARER = "urn:ietf:params:oauth:grant-type:jwt-bearer"
DEFERRED_GRANT = "urn:ietf:params:oauth:grant-type:deferred"
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
    max_grant_lifetime: int = 300  # the IdP's configured limit; the core recommends 300 s
    # Deferred redemption (D cases): a second agent the RAS correlates and
    # lets act for the user, and a scope beyond `scope` that RAS policy can
    # require approval for.
    second_agent: str = "agent-43"
    extra_scope: str = "files.write"


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
    """The client role of scene 2: one grant proof key K, and a second key for mismatches.

    The client signs proofs and assertions at its own clock, which a case
    advances together with the servers' (Context.advance).
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self.k, self.k2 = jws.new_ec_key(), jws.new_ec_key()
        self.offset = 0

    def now(self):
        return int(time.time()) + self.offset

    def proof(self, dpop_key, method, url, access_token=None):
        return jws.dpop_proof(getattr(self, dpop_key), method, url,
                              access_token=access_token, iat=self.now())

    def exchange(self, id_token, dpop_key="k", assertion=None, resources=None,
                 assertion_aud=None):
        cfg = self.cfg
        assertion = assertion or jws.client_assertion(
            cfg.idp_client_key, cfg.idp_client_id, assertion_aud or cfg.idp.issuer,
            now=self.now())
        form = {"grant_type": TOKEN_EXCHANGE, "requested_token_type": ID_JAG_TYPE,
                "client_id": cfg.idp_client_id, "client_assertion_type": ASSERTION_TYPE,
                "client_assertion": assertion, "subject_token": id_token,
                "subject_token_type": ID_TOKEN_TYPE, "audience": cfg.ras.issuer,
                "resource": resources or [cfg.resource], "scope": cfg.scope}
        headers = {}
        if dpop_key:
            headers["DPoP"] = self.proof(dpop_key, "POST", cfg.idp.token_endpoint)
        return http("POST", cfg.idp.transport + urlsplit(cfg.idp.token_endpoint).path,
                    form, headers)

    def ras_token(self, form, dpop_key="k", as_other_client=False, proof=None):
        """A token request to the RAS with fresh client authentication and DPoP proof.

        proof, where given, is sent as the DPoP header instead of a fresh one.
        """
        cfg = self.cfg
        client_id = cfg.other_ras_client_id if as_other_client else cfg.ras_client_id
        key = cfg.other_ras_client_key if as_other_client else cfg.ras_client_key
        form = dict(form, client_id=client_id, client_assertion_type=ASSERTION_TYPE,
                    client_assertion=jws.client_assertion(key, client_id, cfg.ras.issuer,
                                                          now=self.now()))
        headers = {}
        if proof:
            headers["DPoP"] = proof
        elif dpop_key:
            headers["DPoP"] = self.proof(dpop_key, "POST", cfg.ras.token_endpoint)
        return http("POST", cfg.ras.transport + urlsplit(cfg.ras.token_endpoint).path,
                    form, headers)

    def redeem(self, grant, dpop_key="k", resource=None, as_other_client=False,
               deferred=False, proof=None):
        form = {"grant_type": JWT_BEARER, "assertion": grant,
                "resource": resource or self.cfg.resource}
        if deferred:
            form["completion_mode"] = "deferred"
        return self.ras_token(form, dpop_key, as_other_client, proof)

    def poll(self, deferral_code, dpop_key="k"):
        return self.ras_token({"grant_type": DEFERRED_GRANT, "deferral_code": deferral_code},
                              dpop_key)

    def refresh(self, refresh_token, dpop_key="k"):
        return self.ras_token({"grant_type": "refresh_token", "refresh_token": refresh_token},
                              dpop_key)

    def get(self, path, token, dpop_key="k"):
        proof = self.proof(dpop_key, "GET", self.cfg.api_base + path, access_token=token)
        return http("GET", self.cfg.api_transport + path,
                    headers={"Authorization": f"DPoP {token}", "DPoP": proof})


class Adapter:
    """Test-control contract. A deployment under test supplies an implementation.

    id_token(user, aud=None, claims=None)
                                   an ID Token for the user, for the IdP client
                                   unless aud names another audience; claims
                                   overrides members such as iat
    set(role, what, value)         change one relationship or setting:
                                     idp: binding_enabled, agent_active,
                                          client_association, delegation,
                                          client_profile ("bound" or "governed")
                                     ras: agent_active, actor_gate,
                                          client_profile ("bound" or "governed"),
                                          approval_required (a list of scopes
                                          RAS policy requires approval for),
                                          refresh_permitted (refresh tokens for
                                          approved standing access),
                                          max_pending_lifetime and
                                          authorization_lifetime (seconds)
                                     api: actor_gate
    mint_grant(claims)             an ID-JAG the IdP signs with these claims
    mint_access_token(claims, typ="at+jwt")
                                   an access token the RAS signs with these
                                   claims and this typ
    reset()                        restore the scene 1 configuration
    disable_check(role, name)      reference implementation only (vacuity mode)

    The deferral cases also control the RAS's Access Request Service and
    the clock. A task is a dict with id, status ("pending", "approved",
    "denied" or "cancelled"), agent and scope.
    tasks()                        every access request the RAS opened
    approve(task, approved_until, scope=None)
                                   approve a task until approved_until
                                   (seconds since the epoch, server clock),
                                   narrowing to scope where given
    deny(task)                     deny a task
    revoke(task)                   revoke a task's approval
    shorten(task, approved_until)  the next re-evaluation of the task's
                                   approval returns this earlier approved_until
    substitute(task, other)        the service answers a status request for
                                   task with other's result
    advance_clock(seconds)         advance every server's clock
    """

    def reset(self):
        raise NotImplementedError

    def id_token(self, user, aud=None, claims=None):
        raise NotImplementedError

    def set(self, role, what, value):
        raise NotImplementedError

    def mint_grant(self, claims):
        raise NotImplementedError

    def mint_access_token(self, claims, typ="at+jwt"):
        raise NotImplementedError

    def disable_check(self, role, name):
        raise NotImplementedError

    def tasks(self):
        raise NotImplementedError

    def approve(self, task, approved_until, scope=None):
        raise NotImplementedError

    def deny(self, task):
        raise NotImplementedError

    def revoke(self, task):
        raise NotImplementedError

    def shorten(self, task, approved_until):
        raise NotImplementedError

    def substitute(self, task, other):
        raise NotImplementedError

    def advance_clock(self, seconds):
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

    def id_token(self, user, aud=None, claims=None):
        body = {"user": user, "claims": claims or {}}
        if aud:
            body["aud"] = aud
        return self._call("idp", "id_token", body)["id_token"]

    def set(self, role, what, value):
        self._call(role, "set", {"what": what, "value": value})

    def mint_grant(self, claims):
        return self._call("idp", "mint_grant", {"claims": claims})["grant"]

    def mint_access_token(self, claims, typ="at+jwt"):
        return self._call("ras", "mint_access_token",
                          {"claims": claims, "typ": typ})["access_token"]

    def disable_check(self, role, name):
        self._call(role, "disable_check", {"name": name})

    def tasks(self):
        return self._call("ras", "tasks")["tasks"]

    def approve(self, task, approved_until, scope=None):
        body = {"task": task, "approved_until": approved_until}
        if scope is not None:
            body["scope"] = scope
        self._call("ras", "approve", body)

    def deny(self, task):
        self._call("ras", "deny", {"task": task})

    def revoke(self, task):
        self._call("ras", "revoke", {"task": task})

    def shorten(self, task, approved_until):
        self._call("ras", "shorten", {"task": task, "approved_until": approved_until})

    def substitute(self, task, other):
        self._call("ras", "substitute", {"task": task, "with": other})

    def advance_clock(self, seconds):
        for role in ("idp", "ras", "api"):
            self._call(role, "clock", {"advance": seconds})


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

    def id_token(self, aud=None, claims=None):
        return self.adapter.id_token(self.cfg.user, aud, claims)

    def grant(self, dpop_key="k"):
        resp = self.client.exchange(self.id_token(), dpop_key=dpop_key)
        check(resp.status == 200, f"exchange failed: {resp}")
        return resp.json()["access_token"]

    def access_token(self):
        resp = self.client.redeem(self.grant())
        check(resp.status == 200, f"redemption failed: {resp}")
        return resp.json()["access_token"]

    def now(self):
        return self.client.now()

    def advance(self, seconds):
        """Advance the servers' clocks and the client's together."""
        self.adapter.advance_clock(seconds)
        self.client.offset += seconds


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def typ_is(header, media_type):
    """typ names the media type, with or without "application/" (RFC 7515 Section 4.1.9)."""
    value = header.get("typ")
    return isinstance(value, str) and value.lower() in (media_type, "application/" + media_type)


def single(value):
    """A JWT claim that may be a string or a one-element array, as one value."""
    return value[0] if isinstance(value, list) and len(value) == 1 else value


def jkt(claims):
    cnf = claims.get("cnf")
    return cnf.get("jkt") if isinstance(cnf, dict) else None


def expect_error(resp, status, error):
    body = resp.json()
    check(resp.status == status and body.get("error") == error,
          f"expected HTTP {status} {error}, got {resp}")
    check("access_token" not in body, "an error response carried a token")


def expect_challenge(ctx, resp, status, error):
    """The status, the DPoP scheme, and the error code where the challenge carries one."""
    challenge = resp.headers.get("WWW-Authenticate", "") if resp.headers else ""
    check(resp.status == status and challenge.startswith("DPoP"),
          f"expected HTTP {status} with a DPoP challenge, got {resp} {challenge!r}")
    if "error=" in challenge:
        check(f'error="{error}"' in challenge, f"expected error {error}, got {challenge!r}")
    else:
        ctx.notes.append(f"challenge carries no error parameter; {error} expected "
                         "(RFC 9449 Section 7.1 SHOULD)")


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
    check(typ_is(header, "oauth-id-jag+jwt"), "typ")
    check(grant.get("iss") == cfg.idp.issuer, "iss")
    check(single(grant.get("aud")) == cfg.ras.issuer, "aud")
    check(grant.get("sub") == cfg.expect["grant_sub"], "sub is the user in the RAS namespace")
    check(grant.get("client_id") == cfg.ras_client_id, "client_id is the RAS registration")
    check(single(grant.get("resource")) == cfg.resource, "resource")
    check(grant.get("scope") == cfg.scope, "scope")
    act = grant.get("act")
    check(isinstance(act, dict) and "act" not in act and
          act.get("iss") == cfg.expect["agent_iss"] and act.get("sub") == cfg.expect["agent"],
          f"act names the Agent Principal: {act}")
    check(jkt(grant) == jws.thumbprint(jws.public_jwk(ctx.client.k)),
          "cnf.jkt is the grant proof key")
    lifetime = grant["exp"] - grant["iat"]
    check(lifetime <= cfg.max_grant_lifetime,
          f"grant lifetime {lifetime} s exceeds the configured limit {cfg.max_grant_lifetime} s")
    if lifetime > 300:
        ctx.notes.append(f"grant lifetime {lifetime} s exceeds the recommended 300 s (SHOULD)")
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
    if "refresh_token" in body:
        ctx.notes.append("a refresh token was issued; the core permits one only under "
                         "explicit policy (Optional RAS Refresh Tokens)")
    header, token, _, _ = jws.decode(body["access_token"])
    _, grant_claims, _, _ = jws.decode(grant)
    check(typ_is(header, "at+jwt"), "typ at+jwt or application/at+jwt")
    check(token.get("sub") == cfg.expect["token_sub"], "sub is the local user")
    check(token.get("act") == grant_claims["act"], f"act unchanged: {token.get('act')}")
    check(token.get("client_id") == cfg.ras_client_id, "client_id")
    check(single(token.get("aud")) == cfg.resource, "aud is the tenant resource")
    check(jkt(token) == jws.thumbprint(jws.public_jwk(ctx.client.k)),
          "access token bound to the same key")


@case("P3", "API", "Serves a read to the bound access token with a fresh proof",
      "core: Token Validation; Delegated Access")
def p3(ctx):
    resp = ctx.client.get(ctx.cfg.read_path, ctx.access_token())
    check(resp.status == 200, f"read failed: {resp}")


def minted_token_claims(ctx, **overrides):
    """Claims of a valid delegated access token bound to K, with overrides."""
    cfg = ctx.cfg
    claims = {"sub": cfg.expect["token_sub"], "aud": cfg.resource,
              "client_id": cfg.ras_client_id, "scope": cfg.scope,
              "act": {"iss": cfg.expect["agent_iss"], "sub": cfg.expect["agent"]},
              "cnf": {"jkt": jws.thumbprint(jws.public_jwk(ctx.client.k))}}
    claims.update(overrides)
    return claims


@case("P4", "API", "Accepts typ application/at+jwt and a one-element audience array",
      "RFC 9068 Sections 2.1 and 4; core: Token Validation", needs=("mint_access_token",))
def p4(ctx):
    token = ctx.adapter.mint_access_token(minted_token_claims(ctx, aud=[ctx.cfg.resource]),
                                          typ="application/at+jwt")
    resp = ctx.client.get(ctx.cfg.read_path, token)
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


@case("N16", "RAS", "Refuses with actor_unauthorized when RAS policy does not let the agent "
      "act for the user",
      "core: Delegated Actor Authorization (actor gate at the RAS); Redemption Errors",
      needs=("set:ras.actor_gate",), defeats=("ras.actor_gate",))
def n16(ctx):
    grant = ctx.grant()
    ctx.adapter.set("ras", "actor_gate", False)
    expect_error(ctx.client.redeem(grant), 400, "actor_unauthorized")


# API rejections ------------------------------------------------------------

@case("N17", "API", "Rejects an access token used in another tenant, even with a fresh proof",
      "core: Renewal and Negative Tests, another tenant", defeats=("api.tenant",))
def n17(ctx):
    resp = ctx.client.get(ctx.cfg.other_tenant_path, ctx.access_token())
    expect_challenge(ctx, resp, 401, "invalid_token")


@case("N18", "API", "Rejects a delegated-population access token without act",
      "core: Renewal and Negative Tests, missing act; Profile Applicability",
      needs=("mint_access_token",), defeats=("api.require_act",))
def n18(ctx):
    claims = minted_token_claims(ctx)
    del claims["act"]
    token = ctx.adapter.mint_access_token(claims)
    expect_challenge(ctx, ctx.client.get(ctx.cfg.read_path, token), 401, "invalid_token")


@case("N19", "API", "Rejects a request proven with a key other than the token's",
      "core: Token Validation (Protection); RFC 9449 Section 7.1",
      defeats=("api.key_binding",))
def n19(ctx):
    resp = ctx.client.get(ctx.cfg.read_path, ctx.access_token(), dpop_key="k2")
    expect_challenge(ctx, resp, 401, "invalid_token")


@case("N20", "API", "Denies the actor with actor_unauthorized, not insufficient_scope",
      "core: Error Responses; Delegated Actor Authorization",
      needs=("set:api.actor_gate",), defeats=("api.actor_gate",))
def n20(ctx):
    token = ctx.access_token()
    ctx.adapter.set("api", "actor_gate", False)
    expect_challenge(ctx, ctx.client.get(ctx.cfg.read_path, token), 403, "actor_unauthorized")


# Time claims ---------------------------------------------------------------

HOUR = 3600


@case("N21", "IdP", "Rejects an ID Token whose iat is an hour in the future",
      "core: Time, Replay, and Key Validation", needs=("id_token:claims",),
      defeats=("idp.id_token_time",))
def n21(ctx):
    now = int(time.time())
    id_token = ctx.id_token(claims={"iat": now + HOUR, "exp": now + HOUR + 3900})
    expect_error(ctx.client.exchange(id_token), 400, "invalid_grant")


@case("N22", "IdP", "Rejects a client assertion whose nbf is an hour in the future",
      "RFC 7523 Section 3; core: Time, Replay, and Key Validation",
      defeats=("idp.client_assertion_time",))
def n22(ctx):
    cfg, now = ctx.cfg, int(time.time())
    assertion = jws.client_assertion(cfg.idp_client_key, cfg.idp_client_id, cfg.idp.issuer,
                                     extra={"nbf": now + HOUR, "exp": now + HOUR + 60})
    expect_error(ctx.client.exchange(ctx.id_token(), assertion=assertion), 400, "invalid_client")


@case("N23", "RAS", "Rejects a grant whose nbf is an hour in the future",
      "RFC 7523 Section 3; core: Time, Replay, and Key Validation",
      needs=("mint_grant",), defeats=("ras.grant_time",))
def n23(ctx):
    cfg, now = ctx.cfg, int(time.time())
    grant = ctx.adapter.mint_grant({
        "sub": cfg.expect["grant_sub"], "client_id": cfg.ras_client_id,
        "resource": cfg.resource, "scope": cfg.scope,
        "act": {"iss": cfg.expect["agent_iss"], "sub": cfg.expect["agent"]},
        "cnf": {"jkt": jws.thumbprint(jws.public_jwk(ctx.client.k))},
        "nbf": now + HOUR, "exp": now + HOUR + 300})
    expect_error(ctx.client.redeem(grant), 400, "invalid_grant")


@case("N24", "API", "Rejects an access token whose iat is an hour in the future",
      "core: Time, Replay, and Key Validation; RFC 9068 Section 4",
      needs=("mint_access_token",), defeats=("api.token_time",))
def n24(ctx):
    now = int(time.time())
    token = ctx.adapter.mint_access_token(
        minted_token_claims(ctx, iat=now + HOUR, exp=now + HOUR + 600))
    expect_challenge(ctx, ctx.client.get(ctx.cfg.read_path, token), 401, "invalid_token")


# Deferred redemption at the RAS ---------------------------------------------
#
# The oversight companion's Deferred Redemption rows. In every case RAS
# policy requires approval for the requested scope. Cases that approve,
# deny, revoke or substitute need control of the RAS's Access Request
# Service, and the clock cases advance every clock: they are tests of the
# reference implementation, not black-box conformance cases.

def require_approval(ctx, scopes=None):
    ctx.adapter.set("ras", "approval_required", list(scopes or [ctx.cfg.scope]))


def expect_deferred(resp):
    """A DTR deferred response: HTTP 400, authorization_pending, deferral_code, expires_in."""
    body = resp.json()
    check(resp.status == 400 and body.get("error") == "authorization_pending",
          f"expected a deferred response, got {resp}")
    check(isinstance(body.get("deferral_code"), str) and body["deferral_code"],
          "deferral_code")
    check(isinstance(body.get("expires_in"), int) and body["expires_in"] > 0, "expires_in")
    check("interval" not in body or isinstance(body["interval"], int), "interval")
    check("access_token" not in body, "a deferred response carried a token")
    return body


def expect_pending(resp):
    """A poll that leaves the request pending: authorization_pending or slow_down."""
    body = resp.json()
    check(resp.status == 400 and body.get("error") in ("authorization_pending", "slow_down"),
          f"expected authorization_pending, got {resp}")
    check("access_token" not in body, "a pending response carried a token")


def expect_token(resp):
    """A successful token response; returns the body and the access token's claims."""
    body = resp.json()
    check(resp.status == 200 and isinstance(body.get("access_token"), str),
          f"expected a token response, got {resp}")
    return body, jws.decode(body["access_token"])[1]


def defer(ctx, grant, **kwargs):
    return expect_deferred(ctx.client.redeem(grant, deferred=True, **kwargs))


def tasks(ctx, agent=None, status="pending"):
    return [t for t in ctx.adapter.tasks()
            if (status is None or t.get("status") == status) and
            (agent is None or t.get("agent") == agent)]


def only_task(ctx, agent=None):
    """The one pending access request, for one agent where given."""
    found = tasks(ctx, agent)
    check(len(found) == 1, f"expected one pending access request"
          f"{' for ' + agent if agent else ''}, found {len(found)}")
    return found[0]["id"]


def minted_grant(ctx, agent=None, scope=None):
    """An ID-JAG for the user, bound to K, for another agent or scope.

    For the second agent it stands for a shared client's issuance, which
    the reference IdP does not implement: a grant naming another agent
    for the same RAS client, user, resource and scope.
    """
    cfg = ctx.cfg
    return ctx.adapter.mint_grant({
        "sub": cfg.expect["grant_sub"], "client_id": cfg.ras_client_id,
        "resource": cfg.resource, "scope": scope or cfg.scope,
        "act": {"iss": cfg.expect["agent_iss"], "sub": agent or cfg.expect["agent"]},
        "cnf": {"jkt": jws.thumbprint(jws.public_jwk(ctx.client.k))}})


def scopes(value):
    return set(str(value or "").split())


@case("D01", "RAS", "Refuses with actor_unauthorized, not a deferral, without the opt-in",
      "oversight: Redemption Opt-In; core: Redemption Errors",
      needs=("set:ras.approval_required",), defeats=("ras.approval_gate",))
def d01(ctx):
    require_approval(ctx)
    resp = ctx.client.redeem(ctx.grant())
    expect_error(resp, 400, "actor_unauthorized")
    check("deferral_code" not in resp.json(), "the refusal carried a deferral code")


@case("D02", "RAS", "Defers, stays pending, then issues once on approval",
      "oversight: Deferring a Redemption; Redemption Resolution",
      needs=("set:ras.approval_required", "tasks", "approve"),
      defeats=("ras.code_single_use",))
def d02(ctx):
    cfg = ctx.cfg
    require_approval(ctx)
    grant = ctx.grant()
    code = defer(ctx, grant)["deferral_code"]
    expect_pending(ctx.client.poll(code))
    approved_until = ctx.now() + 3600
    ctx.adapter.approve(only_task(ctx), approved_until)
    body, token = expect_token(ctx.client.poll(code))
    check(body.get("token_type") == "DPoP", "token_type DPoP")
    header = jws.decode(body["access_token"])[0]
    check(typ_is(header, "at+jwt"), "typ at+jwt or application/at+jwt")
    check(token.get("sub") == cfg.expect["token_sub"], "sub is the local user")
    check(token.get("act") == jws.decode(grant)[1]["act"], f"act unchanged: {token.get('act')}")
    check(token.get("client_id") == cfg.ras_client_id, "client_id")
    check(single(token.get("aud")) == cfg.resource, "aud is the tenant resource")
    check(jkt(token) == jws.thumbprint(jws.public_jwk(ctx.client.k)),
          "access token bound to the redemption key")
    check(token.get("exp", approved_until + 1) <= approved_until, "exp after approved_until")
    check(ctx.client.get(cfg.read_path, body["access_token"]).status == 200,
          "the API refused the access token")
    expect_error(ctx.client.poll(code), 400, "invalid_grant")


@case("D03", "RAS", "Rejects a poll proven with a key other than the deferral code's",
      "oversight: Deferring a Redemption (deferral code bound to the client and key)",
      needs=("set:ras.approval_required",), defeats=("ras.deferral_key_binding",))
def d03(ctx):
    require_approval(ctx)
    code = defer(ctx, ctx.grant())["deferral_code"]
    expect_error(ctx.client.poll(code, dpop_key="k2"), 400, "invalid_dpop_proof")


@case("D04", "RAS", "Bounds expires_in by the absolute expiration; a later approval finds "
      "expired_token",
      "oversight: Deferring a Redemption (absolute authorization expiration)",
      needs=("set:ras.approval_required", "set:ras.max_pending_lifetime",
             "set:ras.authorization_lifetime", "tasks", "approve", "advance_clock"),
      defeats=("ras.absolute_expiration",))
def d04(ctx):
    require_approval(ctx)
    ctx.adapter.set("ras", "max_pending_lifetime", 24 * HOUR)
    ctx.adapter.set("ras", "authorization_lifetime", 8 * HOUR)
    body = defer(ctx, ctx.grant())
    check(body["expires_in"] <= 8 * HOUR,
          f"expires_in {body['expires_in']} s exceeds the 8 h absolute expiration")
    task = only_task(ctx)
    ctx.advance(9 * HOUR)
    ctx.adapter.approve(task, ctx.now() + HOUR)
    expect_error(ctx.client.poll(body["deferral_code"]), 400, "expired_token")


@case("D05", "RAS", "Denies at the next poll when the agent is disabled while pending",
      "oversight: Redemption Resolution",
      needs=("set:ras.approval_required", "set:ras.agent_active", "tasks", "approve"),
      defeats=("ras.resolution_recheck",))
def d05(ctx):
    require_approval(ctx)
    code = defer(ctx, ctx.grant())["deferral_code"]
    ctx.adapter.set("ras", "agent_active", False)
    ctx.adapter.approve(only_task(ctx), ctx.now() + 3600)
    expect_error(ctx.client.poll(code), 400, "access_denied")


@case("D06", "RAS", "After a denial, the same grant presented again fails with invalid_grant",
      "oversight: Recovery; Redemption Resolution",
      needs=("set:ras.approval_required", "tasks", "deny"), defeats=("ras.grant_consumed",))
def d06(ctx):
    require_approval(ctx)
    grant = ctx.grant()
    code = defer(ctx, grant)["deferral_code"]
    ctx.adapter.deny(only_task(ctx))
    expect_error(ctx.client.poll(code), 400, "access_denied")
    expect_error(ctx.client.redeem(grant, deferred=True), 400, "invalid_grant")


@case("D07", "RAS", "While pending, the same grant without the opt-in fails with invalid_grant",
      "oversight: Recovery (every other presentation); Deferring a Redemption",
      needs=("set:ras.approval_required",), defeats=("ras.grant_consumed",))
def d07(ctx):
    require_approval(ctx)
    grant = ctx.grant()
    defer(ctx, grant)
    expect_error(ctx.client.redeem(grant), 400, "invalid_grant")


@case("D08", "RAS", "Recovery returns the same code; an unbound grant with another key fails",
      "oversight: Recovery",
      needs=("set:ras.approval_required", "set:idp.client_profile", "set:ras.client_profile"),
      defeats=("ras.recovery_match",))
def d08(ctx):
    require_approval(ctx)
    ctx.adapter.set("idp", "client_profile", "governed")
    ctx.adapter.set("ras", "client_profile", "governed")
    grant = ctx.grant(dpop_key=None)
    check("cnf" not in jws.decode(grant)[1], "setup: the IdP issued a grant with cnf")
    first = defer(ctx, grant)
    again = defer(ctx, grant)
    check(again["deferral_code"] == first["deferral_code"],
          "recovery returned another deferral code")
    check(again["expires_in"] <= first["expires_in"], "recovery increased expires_in")
    expect_error(ctx.client.redeem(grant, deferred=True, dpop_key="k2"), 400, "invalid_grant")


@case("D09", "RAS", "Recovery after approval returns the code, and the poll then issues",
      "oversight: Recovery",
      needs=("set:ras.approval_required", "tasks", "approve"))
def d09(ctx):
    require_approval(ctx)
    grant = ctx.grant()
    code = defer(ctx, grant)["deferral_code"]
    ctx.adapter.approve(only_task(ctx), ctx.now() + 3600)
    check(defer(ctx, grant)["deferral_code"] == code, "recovery returned another deferral code")
    expect_token(ctx.client.poll(code))


@case("D10", "RAS", "A second agent through the same client gets its own access request",
      "oversight: Approval Binding",
      needs=("set:ras.approval_required", "mint_grant", "tasks", "approve"),
      defeats=("ras.task_per_redemption",))
def d10(ctx):
    cfg = ctx.cfg
    require_approval(ctx)
    code_a = defer(ctx, ctx.grant())["deferral_code"]
    code_b = defer(ctx, minted_grant(ctx, agent=cfg.second_agent))["deferral_code"]
    check(code_b != code_a, "the second agent's redemption got the first one's code")
    found = tasks(ctx)
    check(len(found) == 2, f"expected two pending access requests, found {len(found)}")
    ctx.adapter.approve(only_task(ctx, cfg.expect["agent"]), ctx.now() + 3600)
    expect_pending(ctx.client.poll(code_b))
    expect_token(ctx.client.poll(code_a))


@case("D11", "RAS", "Another task's approval leaves the redemption pending",
      "oversight: Approval Binding",
      needs=("set:ras.approval_required", "mint_grant", "tasks", "approve", "substitute"),
      defeats=("ras.approval_binding",))
def d11(ctx):
    cfg = ctx.cfg
    require_approval(ctx)
    defer(ctx, ctx.grant())
    code_b = defer(ctx, minted_grant(ctx, agent=cfg.second_agent))["deferral_code"]
    task_a = only_task(ctx, cfg.expect["agent"])
    task_b = only_task(ctx, cfg.second_agent)
    ctx.adapter.approve(task_a, ctx.now() + 3600)
    ctx.adapter.substitute(task_b, task_a)
    expect_pending(ctx.client.poll(code_b))


@case("D12", "RAS", "Reports a narrowed approval in scope",
      "oversight: Redemption Resolution",
      needs=("set:ras.approval_required", "mint_grant", "tasks", "approve"),
      defeats=("ras.approval_narrowing",))
def d12(ctx):
    cfg = ctx.cfg
    require_approval(ctx, [cfg.extra_scope])
    code = defer(ctx, minted_grant(ctx, scope=f"{cfg.scope} {cfg.extra_scope}"))["deferral_code"]
    ctx.adapter.approve(only_task(ctx), ctx.now() + 3600, scope=cfg.scope)
    body, token = expect_token(ctx.client.poll(code))
    check(scopes(body.get("scope")) == {cfg.scope},
          f"response scope {body.get('scope')!r}, approved {cfg.scope!r}")
    check(scopes(token.get("scope")) == {cfg.scope},
          f"access token scope {token.get('scope')!r}, approved {cfg.scope!r}")


def approved_refresh(ctx, approved_until):
    """Defer, approve until approved_until, poll; return the token body and claims."""
    require_approval(ctx)
    ctx.adapter.set("ras", "refresh_permitted", True)
    code = defer(ctx, ctx.grant())["deferral_code"]
    task = only_task(ctx)
    ctx.adapter.approve(task, approved_until)
    body, token = expect_token(ctx.client.poll(code))
    check(isinstance(body.get("refresh_token"), str),
          "setup: no refresh token with refresh permitted")
    return task, body, token


@case("D13", "RAS", "No token outlives approved_until; a refresh after it fails",
      "oversight: Redemption Resolution; Refresh and Continuation",
      needs=("set:ras.approval_required", "set:ras.refresh_permitted", "tasks", "approve",
             "advance_clock"),
      defeats=("ras.approval_deadline",))
def d13(ctx):
    approved_until = ctx.now() + 300
    _, body, token = approved_refresh(ctx, approved_until)
    check(token.get("exp", approved_until + 1) <= approved_until,
          f"access token exp {token.get('exp')} is after approved_until {approved_until}")
    ctx.advance(400)
    expect_error(ctx.client.refresh(body["refresh_token"]), 400, "invalid_grant")


@case("D14", "RAS", "A refresh after the approval is revoked fails with invalid_grant",
      "oversight: Refresh and Continuation",
      needs=("set:ras.approval_required", "set:ras.refresh_permitted", "tasks", "approve",
             "revoke", "advance_clock"),
      defeats=("ras.approval_reevaluation",))
def d14(ctx):
    task, body, _ = approved_refresh(ctx, ctx.now() + 3600)
    ctx.advance(300)
    check(ctx.client.refresh(body["refresh_token"]).status == 200,
          "setup: refresh before revocation failed")
    ctx.advance(300)
    ctx.adapter.revoke(task)
    ctx.advance(300)
    expect_error(ctx.client.refresh(body["refresh_token"]), 400, "invalid_grant")


@case("D15", "RAS", "A shorter approved_until from re-evaluation bounds every later token",
      "oversight: Approval Binding; Refresh and Continuation",
      needs=("set:ras.approval_required", "set:ras.refresh_permitted", "tasks", "approve",
             "shorten"),
      defeats=("ras.enforcement_deadline",))
def d15(ctx):
    task, body, _ = approved_refresh(ctx, ctx.now() + 3600)
    shorter = ctx.now() + 120
    ctx.adapter.shorten(task, shorter)
    for attempt in ("first", "second"):
        _, token = expect_token(ctx.client.refresh(body["refresh_token"]))
        check(token.get("exp", shorter + 1) <= shorter,
              f"{attempt} refreshed token exp {token.get('exp')} is after the shorter "
              f"approved_until {shorter}")


@case("D16", "RAS", "Two identical requests share one pending redemption and access request",
      "oversight: Recovery (atomicity)",
      needs=("set:ras.approval_required", "tasks"), defeats=("ras.single_pending",))
def d16(ctx):
    require_approval(ctx)
    grant, responses = ctx.grant(), [None, None]

    def send(i):
        responses[i] = ctx.client.redeem(grant, deferred=True)
    threads = [threading.Thread(target=send, args=(i,)) for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    codes = {expect_deferred(r)["deferral_code"] for r in responses}
    check(len(codes) == 1, "the two requests got different deferral codes")
    found = tasks(ctx, status=None)
    check(len(found) == 1, f"expected one access request, found {len(found)}")


@case("D17", "RAS", "Recovery after the grant's exp returns the code without extending it",
      "oversight: Recovery (grant expiry; no extension)",
      needs=("set:ras.approval_required", "tasks", "approve", "advance_clock"),
      defeats=("ras.recovery_no_extension",))
def d17(ctx):
    require_approval(ctx)
    grant = ctx.grant()
    first = defer(ctx, grant)
    ctx.advance(900)
    check(ctx.now() > jws.decode(grant)[1]["exp"] + 300, "setup: the grant has not expired")
    again = defer(ctx, grant)
    check(again["deferral_code"] == first["deferral_code"],
          "recovery returned another deferral code")
    check(again["expires_in"] <= first["expires_in"] - 900 + 1,
          f"recovery extended the pending deadline: expires_in {first['expires_in']} s, "
          f"then {again['expires_in']} s 900 s later")
    ctx.adapter.approve(only_task(ctx), ctx.now() + 3600)
    expect_token(ctx.client.poll(first["deferral_code"]))


@case("D18", "RAS", "Recovery that reuses the first request's DPoP proof fails",
      "oversight: Recovery (freshness); RFC 9449 Section 11.1",
      needs=("set:ras.approval_required",), defeats=("ras.proof_replay",))
def d18(ctx):
    require_approval(ctx)
    grant = ctx.grant()
    proof = ctx.client.proof("k", "POST", ctx.cfg.ras.token_endpoint)
    defer(ctx, grant, proof=proof)
    resp = ctx.client.redeem(grant, deferred=True, proof=proof)
    expect_error(resp, 400, "invalid_dpop_proof")
    check("deferral_code" not in resp.json(), "the error carried a deferral code")


@case("D19", "RAS", "After a token response redeems the code, recovery fails",
      "oversight: Recovery (window)",
      needs=("set:ras.approval_required", "tasks", "approve"),
      defeats=("ras.recovery_window",))
def d19(ctx):
    require_approval(ctx)
    grant = ctx.grant()
    code = defer(ctx, grant)["deferral_code"]
    ctx.adapter.approve(only_task(ctx), ctx.now() + 3600)
    expect_token(ctx.client.poll(code))
    expect_error(ctx.client.redeem(grant, deferred=True), 400, "invalid_grant")


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
