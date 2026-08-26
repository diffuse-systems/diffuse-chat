# What a refused person actually sees

Lot 2 closed with this open: a delegated request that the deployment refuses
answers `200 {"status":"started"}` on `POST /api/agents/chat`, and the failure
arrives inside the SSE stream. Nobody had looked at the stream.

Measured here against `ghcr.io/danny-avila/librechat@sha256:c5db3331…`
(v0.8.7), in front of a deployment built from the release packages.

## The setup

One person, imported and working, sends a message. Then:

```
$ diffuse-coordinator identity disable 6a8f44f9bc4f9191e4179b87
6a8f44f9bc4f9191e4179b87 disabled. A gateway asking to act for them is refused
from the next request; everything the trail already records about them stays.
```

They send another.

## What the deployment says

403, with a sentence written to be acted on:

```
the user the gateway asserted is disabled here. Re-enable them with
`diffuse-coordinator identity enable 6a8f44f9bc4f9191e4179b87`.
```

## What the browser receives

The whole of it, read off `GET /api/agents/chat/stream/<streamId>`:

```
event: error
data: {"error":"{ \"type\": \"illegal_model_request\", \"info\": \"Diffuse|diffuse-demo\" }"}
```

**The deployment's sentence appears nowhere** — not in the stream, not in the
conversation, and not in LibreChat's own server log. The refused message is not
persisted at all: the conversation list is unchanged.

The mechanism is worth knowing, because it explains why the error blames the
wrong thing. With `models.fetch: true` the catalogue is fetched per request; the
403 refuses that fetch first, LibreChat concludes the model is unavailable, and
it rejects the request **before ever calling the completion endpoint**. So the
user is told about a model, and the cause is an identity.

## The one configuration that changes it, and what it costs

With `models.fetch: false` and the model named literally in `default`,
LibreChat calls the endpoint anyway. The deployment's real sentence then appears
verbatim in LibreChat's container log:

```
2026-08-26 20:08:20 error: [api/server/controllers/agents/client.js #sendCompletion]
  Unhandled error type 403 the user the gateway asserted is disabled here.
  Re-enable them with `diffuse-coordinator identity enable 6a8f44f9bc4f9191e4179b87`.
```

But the person then sees an **empty assistant reply** rather than an error — a
silent failure instead of a misleading one — and the model catalogue stops being
filtered per person, which is a feature the enterprise profile exists to
provide.

**Shipped as `fetch: true`.** A visible-but-wrong error beats a silent one for
the user, per-person catalogues are worth keeping, and the operator's real
answer does not depend on either setting: every refused assertion is on the
deployment's own audit trail.

```
diffuse-coordinator audit --via <gateway-handle> --result denied
```

```
attempted/6a8f44f9bc4f9191e4179b87 via apikey/QQ5WDKKE  identity.assert_refused  denied
  the user the gateway asserted is disabled here. Re-enable them with …
```

That row is what makes the trade acceptable, and it did not exist when lot 2
asked this question — the refusal reached nobody at all. It was added in
`fix(delegation): every refused assertion reaches the trail, not just the first`.

## Not fixed, and deliberately

Surfacing the deployment's sentence in the LibreChat UI would mean patching
LibreChat. This repository does not patch LibreChat: it is pinned upstream, and
a fork is a maintenance burden a customer inherits. The limitation is documented
in the README instead, where an operator will find it before a user reports it.
