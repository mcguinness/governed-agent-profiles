"""Minimal JOSE helpers for the conformance suite and reference servers.

Covers what the mandatory interoperability path needs: RS256 for client
assertions, grants and access tokens; ES256 for DPoP proofs; RFC 7638
JWK thumbprints; and the DPoP `ath` hash. Not a general JOSE library.
"""
import base64
import hashlib
import json
import time
import uuid

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature, encode_dss_signature)


def b64u(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64u_decode(text):
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _int_b64u(value, length):
    return b64u(value.to_bytes(length, "big"))


def new_rsa_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def new_ec_key():
    return ec.generate_private_key(ec.SECP256R1())


def public_jwk(key):
    """Public JWK for an RSA or P-256 private or public key."""
    pub = key.public_key() if hasattr(key, "public_key") else key
    numbers = pub.public_numbers()
    if isinstance(pub, rsa.RSAPublicKey):
        n_len = (numbers.n.bit_length() + 7) // 8
        return {"kty": "RSA", "n": _int_b64u(numbers.n, n_len),
                "e": _int_b64u(numbers.e, (numbers.e.bit_length() + 7) // 8)}
    return {"kty": "EC", "crv": "P-256",
            "x": _int_b64u(numbers.x, 32), "y": _int_b64u(numbers.y, 32)}


def thumbprint(jwk):
    """RFC 7638 JWK SHA-256 thumbprint."""
    required = {"RSA": ("e", "kty", "n"), "EC": ("crv", "kty", "x", "y")}
    members = {k: jwk[k] for k in required[jwk["kty"]]}
    canonical = json.dumps(members, separators=(",", ":"), sort_keys=True)
    return b64u(hashlib.sha256(canonical.encode("utf-8")).digest())


def key_from_jwk(jwk):
    """Public key object from a public JWK; rejects private members."""
    if any(k in jwk for k in ("d", "p", "q", "dp", "dq", "qi")):
        raise ValueError("JWK contains private key members")
    if jwk.get("kty") == "RSA":
        n = int.from_bytes(b64u_decode(jwk["n"]), "big")
        e = int.from_bytes(b64u_decode(jwk["e"]), "big")
        return rsa.RSAPublicNumbers(e, n).public_key()
    if jwk.get("kty") == "EC" and jwk.get("crv") == "P-256":
        x = int.from_bytes(b64u_decode(jwk["x"]), "big")
        y = int.from_bytes(b64u_decode(jwk["y"]), "big")
        return ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1()).public_key()
    raise ValueError("unsupported JWK")


def sign(header, payload, key):
    """Compact JWS. RSA keys sign RS256; P-256 keys sign ES256."""
    header = dict(header)
    header["alg"] = "RS256" if isinstance(key, rsa.RSAPrivateKey) else "ES256"
    signing_input = (b64u(json.dumps(header).encode()) + "." +
                     b64u(json.dumps(payload).encode())).encode("ascii")
    if header["alg"] == "RS256":
        sig = key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    else:
        r, s = decode_dss_signature(key.sign(signing_input, ec.ECDSA(hashes.SHA256())))
        sig = r.to_bytes(32, "big") + s.to_bytes(32, "big")
    return signing_input.decode("ascii") + "." + b64u(sig)


def decode(token):
    """Split and decode a compact JWS without verifying it."""
    if not isinstance(token, str) or token.count(".") != 2:
        raise ValueError("not a compact JWS")
    h, p, s = token.split(".")
    try:
        header = json.loads(b64u_decode(h))
        payload = json.loads(b64u_decode(p))
    except (ValueError, TypeError) as exc:
        raise ValueError("malformed JWS") from exc
    if not isinstance(header, dict) or not isinstance(payload, dict):
        raise ValueError("JWS header and payload must be objects")
    return header, payload, f"{h}.{p}".encode("ascii"), b64u_decode(s)


def verify(token, public_key, alg):
    """Verify a compact JWS with one expected algorithm; return (header, payload)."""
    header, payload, signing_input, sig = decode(token)
    if header.get("alg") != alg:
        raise ValueError("unexpected alg")
    try:
        if alg == "RS256":
            public_key.verify(sig, signing_input, padding.PKCS1v15(), hashes.SHA256())
        elif alg == "ES256":
            if len(sig) != 64:
                raise ValueError("bad ES256 signature length")
            der = encode_dss_signature(int.from_bytes(sig[:32], "big"),
                                       int.from_bytes(sig[32:], "big"))
            public_key.verify(der, signing_input, ec.ECDSA(hashes.SHA256()))
        else:
            raise ValueError("unsupported alg")
    except InvalidSignature as exc:
        raise ValueError("bad signature") from exc
    return header, payload


def ath(access_token):
    return b64u(hashlib.sha256(access_token.encode("ascii")).digest())


def dpop_proof(key, htm, htu, access_token=None, iat=None, jti=None):
    """A DPoP proof (RFC 9449) signed with a P-256 key."""
    payload = {"jti": jti or uuid.uuid4().hex, "htm": htm, "htu": htu,
               "iat": int(time.time()) if iat is None else iat}
    if access_token is not None:
        payload["ath"] = ath(access_token)
    return sign({"typ": "dpop+jwt", "jwk": public_jwk(key)}, payload, key)


def client_assertion(key, client_id, audience, lifetime=60, jti=None, extra=None):
    """An RFC 7523 private_key_jwt assertion with iss = sub = client_id."""
    now = int(time.time())
    claims = {"iss": client_id, "sub": client_id, "aud": audience, "iat": now,
              "exp": now + lifetime, "jti": jti or uuid.uuid4().hex}
    claims.update(extra or {})
    return sign({"typ": "JWT"}, claims, key)
