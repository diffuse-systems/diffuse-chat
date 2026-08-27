# The 3c demonstration: LibreChat, unmodified, in front of a real deployment

Design 021 phase 2, end to end. The smoke test proved what the façade *sends*.
This proves what a real deployment *does with it*, and, more to the point, what
it refuses.

Everything below is against **packaged binaries**: `.deb`s built by
`packaging/build.sh` in the `debian:bookworm` container of the release workflow,
installed with `apt`, running in that image. LibreChat is
`ghcr.io/danny-avila/librechat@sha256:c5db3331…` (v0.8.7), unmodified, upstream,
with no plugin and no patch.

```
  LibreChat v0.8.7  ──►  diffuse-api  ──►  diffuse-coordinator  ──►  node agent
     (container)          (packaged)          (packaged)             (packaged)
```

The deployment ran as a container named `diffuse-api` on LibreChat's own compose
network, with its certificate issued for that name, so the façade reached it by
DNS with a certificate that matched. No hostname override, no `NODE_TLS_REJECT_
UNAUTHORIZED`: LibreChat was given the deployment's CA and nothing else.

```yaml
endpoints:
  custom:
    - name: "Diffuse"
      apiKey: "dfe_sk_…"                        # apikey create --act-as
      baseURL: "https://diffuse-api:18443/v1"
      headers:
        X-Diffuse-User-Id: "{{LIBRECHAT_USER_ID}}"
        X-Diffuse-User-Email: "{{LIBRECHAT_USER_EMAIL}}"
```

## Two people, two rows, one credential

Two accounts in LibreChat, each sending one message. What the coordinator wrote:

```
TIME                  ACTOR                                                  ACTION     OBJECT        RESULT
2026-08-26 16:35:12Z  identity/6a8f147edfaca7db56e1f340 via apikey/P8P5Q881  inference  diffuse-demo  allowed
2026-08-26 16:35:12Z  identity/6a8f147fdfaca7db56e1f34b via apikey/P8P5Q881  inference  diffuse-demo  allowed
```

Two different people. **One credential**, in `via`, on both. That is the whole
point of the milestone: before it, both rows would have read `apikey/P8P5Q881`
and no row would have named anybody.

`diffuse-coordinator audit --via P8P5Q881` reads back everything that came
through the façade: the question asked the day a gateway credential is
suspected.

## The refusal, which is the part that matters

One of the two was disabled in the deployment while the façade kept running:

```
$ diffuse-coordinator identity disable 6a8f147fdfaca7db56e1f34b
6a8f147fdfaca7db56e1f34b disabled. A gateway asking to act for them is refused
from the next request; everything the trail already records about them stays.
```

Both then sent another message. What LibreChat's own log recorded for the
disabled one, verbatim, our sentence carried through the OpenAI client:

```
the user the gateway asserted is disabled here. Re-enable them with
`diffuse-coordinator identity enable 6a8f147fdfaca7db56e1f34b`.
```

And what the trail recorded:

```
2026-08-26 16:36:57Z  identity/6a8f147edfaca7db56e1f340 via apikey/P8P5Q881  inference  diffuse-demo  allowed
```

**One row, not two.** The disabled person's request produced no row attributed to
anybody: in particular not to the gateway credential's owner. That is the
property design 021 exists for, and it is the one a fallback would have quietly
destroyed: the trail would have been complete, readable, and wrong.

## What this does not prove

- **The refusal is not visible in LibreChat's UI as a refusal.** `POST
  /api/agents/chat` answers `200 {"status":"started"}` and the failure arrives
  inside the stream; a user sees an error in the conversation and the operator
  sees our sentence in the server log. Whether that is good enough for a
  customer is a lot 3 question about the façade, not about the endpoint.
- **The two accounts were promoted to `ADMIN`** to reach their own seeded agents,
  which is the v0.8.7 permission asymmetry already recorded as a lot 3 delivery
  constraint. What is being demonstrated is what reaches `/v1`, and that is
  unaffected by which LibreChat role opened its front door.
- **`X-Diffuse-User-Name` and the `b64:` path** were exercised against the
  packaged endpoint directly (`b64:S293YWxjenlrLcWgaW1pxIc=` → resolved, 200),
  not through this stack: the deployment keys on the id, and the name header is
  not part of the honour chain.
