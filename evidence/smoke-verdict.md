# Smoke test verdict: the headers arrive substituted

Design 021 §D-G was written by reading LibreChat's source at a pinned digest.
This is the same claim, measured: whole requests captured at the endpoint, from
`ghcr.io/danny-avila/librechat@sha256:c5db3331…` (v0.8.7).

## Two users, so the signal is per person and not an installation constant

```
  message              'hallo von anna'
  x-diffuse-user-id    '6a8edf7b6bc7078da8fac79b'
  x-diffuse-user-email 'anna@example.invalid'
  x-diffuse-user-name  'Anna Muller'
  body.user            '6a8edf7b6bc7078da8fac79b'

  message              'hallo von simic'
  x-diffuse-user-id    '6a8edf7b6bc7078da8fac7a6'
  x-diffuse-user-email 'simic@example.invalid'
  x-diffuse-user-name  'b64:S293YWxjenlrLcWgaW1pxIc='
  body.user            '6a8edf7b6bc7078da8fac7a6'
```

Different ids, different emails, different names. The header is the person.

## Three things this settles that reading could not

**`{{LIBRECHAT_USER_ID}}` resolves to the Mongo document id.** The design read a
fallback in the development tag and noted the stable release has none; what
arrives here is the `_id`, which is what the enterprise profile will index on.

**`b64:` is real, and the design's example was the right one.**
`Kowalczyk-Šimić` arrives as `b64:S293YWxjenlrLcWgaW1pxIc=`, which decodes back
to `Kowalczyk-Šimić`. For a DACH product this is a live path.

**An unresolved placeholder arrives as the literal template.** A header bound to
`{{LIBRECHAT_USER_OPENIDID}}` — a field these local accounts do not have —
arrives as:

```
  x-diffuse-unresolved: '{{LIBRECHAT_USER_OPENIDID}}'
```

That is the pooling hazard the design predicted from the stable release's
source, confirmed in the version a customer would deploy. **Rule 1 of D-G — a
value that is a literal placeholder is refused, never accepted as an identity —
is therefore measured rather than assumed.**

## A second signal, unasked for

The body carries `user` with the **same** stable id. The design did not rely on
it and still should not, because it is the client's own body and D-G's rule
about request-body placeholders applies. It is recorded because a redundancy
worth knowing about is worth writing down.

## What the smoke test cost, and what it found on the way

Three facts about v0.8.7 that no document stated:

1. **There is no `/api/ask` route.** Every conversation goes through
   `/api/agents/chat` and requires an `agent_id`. A custom endpoint is reached
   through an agent bound to it as a *provider*.
2. **`interface.endpointsMenu` and `modelSelect` are off by default**, so the
   composer says "Please select an Agent" until an agent exists.
3. **A non-browser user agent is refused** by `api/server/middleware/uaParser.js`
   with `{"message":"Illegal request"}` — which is what a script driving the API
   sees, and looks nothing like a permission problem.

The last one cost the most: it made agent creation and every chat attempt fail
identically, from two different directions, for a reason that was neither.
