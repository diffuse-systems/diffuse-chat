# Threat model — the façade side

Design 021 §6, from where the façade sits. The deployment's own surfaces are in
`docs/THREAT_MODEL.md` in the product repository; this file covers what putting
LibreChat in front of it adds.

Three entries. The first is the one that matters.

---

## 1. The gateway credential is a master key

**Whoever holds it can generate as every user of the deployment.** That is not a
weakness of the design; it is what delegation *is*, and writing it down is more
honest than describing the credential as "just another API key".

In the enterprise profile it lives in this repository's `.env`, which
`./diffuse-chat up` creates mode 0600 and `.gitignore` refuses to track. It is
passed to the container as an environment variable and reaches the endpoint in
an `Authorization` header inside TLS.

What bounds it:

- **Scope.** `act_as` and nothing else. A stolen gateway credential cannot mint
  a join token, revoke a node, read the audit trail, start a training job or
  reach the admin plane. It can generate completions as anybody, which is bad
  and is bounded.
- **TTL and rotation.** `diffuse-coordinator apikey rotate <handle> --overlap
  24h` issues the next credential — same name, same scope, same `act_as` — and
  puts the old one on a clock. Change `DIFFUSE_GATEWAY_TOKEN` in `.env` and run
  `./diffuse-chat up --enterprise` inside the overlap and nobody notices.
- **Host.** It never leaves the machine running this stack. Obtaining it means
  already being on that machine.
- **Detection.** Every delegated request is on the deployment's audit trail with
  the person in `actor` and this credential in `via`, so
  `diffuse-coordinator audit --via <handle>` reads back every account it spoke
  for. That is detection, not prevention.

**Residual, accepted:** somebody with this host's filesystem can generate as any
imported user until the credential is rotated. The compensating control is that
such an attacker is already inside the machine that holds every conversation in
the façade's database.

**In the developer profile there is no such credential**, and no delegation. One
ordinary API key makes every request and the trail says exactly that: one
credential, nobody named. That is the right shape for one person on one laptop
and the wrong shape for an organisation, which is the whole reason the
enterprise overlay exists.

---

## 2. An identity this façade asserts is a claim, never a fact

The two headers are filled by LibreChat from the account that signed in. The
deployment treats them as an assertion to be checked, not as a fact, and refuses
in this order: the credential may assert at all, something was actually
asserted, the subject is somebody the deployment knows and has not disabled.

**What this façade must not do**, and the configuration in `config/` is written
so it cannot:

- **Bind a header to a field some users lack.** v0.8.7 leaves an unresolved
  `{{LIBRECHAT_USER_*}}` placeholder as **literal template text** — measured, in
  `evidence/smoke-verdict.md`, against the digest this repository pins. A header
  bound to a provider-specific field would therefore arrive as the template's
  own name for every affected person, and a deployment that accepted it would
  file all of them under one identity. `{{LIBRECHAT_USER_ID}}` is always
  populated, which is why it is what the enterprise config uses.
- **Assert an identity from the developer profile.** `config/librechat.yaml` has
  no `headers` block at all. An ordinary key presenting one is refused with a
  message naming this file.

**Not mitigated, named:** the deployment cannot tell a correct assertion from a
forged one. Anybody holding the gateway credential can assert any imported
subject, and nothing in the request distinguishes them from this façade. An HMAC
was considered and rejected — it would be computed with the same credential, so
it stops nobody who has it. Design 021 D-1 records the reasoning and the
condition under which it is reopened: a façade that becomes multi-tenant, or
moves off the deployment's host.

---

## 3. The façade has no privilege of its own

Worth stating because it is what keeps the other two small. LibreChat here is
**a client**. It terminates no trust, holds no signing key, is not on the machine
plane, has no `diffuse://` certificate, and never reaches the coordinator's
admin port. It talks to `/v1` over ordinary TLS with a bearer token, exactly as
the OpenAI SDK does — the only thing it is given is the deployment's CA, so it
can verify the endpoint rather than be verified by it.

So compromising this stack yields the gateway credential, the conversations in
its Mongo, and nothing else: no node identity, no CA, no ability to enrol a
machine, no way to read the deployment's audit trail.

**Its Mongo is a second content store, and it is not covered by the
deployment's retention rules.** Conversations, uploaded files and — if anybody
turns `titleConvo` on — model-written summaries of conversations all live in the
`mongo` volume on this host. The deployment's own rule that prompts never reach
its audit trail says nothing about this database. Back it up, or do not; either
way it is a decision to take deliberately, and `titleConvo` is off by default
partly for this reason.
