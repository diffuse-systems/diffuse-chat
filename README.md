# diffuse-chat

A chat façade in front of a Diffuse Enterprise deployment. LibreChat, upstream
and unmodified, pinned by digest, deployed by compose.

**Contributions are not accepted.** This is a commercial product's deployment
tooling, published so customers can read what runs on their own machines.

## What is here today

Only the **header smoke test** of design 021 §D-G: the stack that answers
whether `{{LIBRECHAT_USER_*}}` placeholders in an endpoint's `headers` block
arrive at the upstream substituted, or as literal template text.

```bash
docker compose -f compose.smoke.yaml up -d --build
```

- `receiver/` — an HTTP endpoint that logs every `X-Diffuse-*` header it
  receives, `repr`-quoted so an empty value, an absent one and a literal
  template are three visibly different answers, and answers like an OpenAI
  endpoint so a conversation completes.
- `config/librechat.smoke.yaml` — one custom endpoint pointing at the receiver,
  with the two headers the design proposes.

Everything is pinned by digest. A tag is a moving target and this whole design
rests on what one specific build substitutes.

## What is not here yet

The enterprise and developer profiles, the `diffuse-chat` script, branding, and
the façade-side threat model. They are lot 3.
