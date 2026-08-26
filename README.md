# diffuse-chat

A chat façade in front of a Diffuse Enterprise deployment. LibreChat, upstream
and unmodified, pinned by digest, deployed by compose.

**Contributions are not accepted.** This is a commercial product's deployment
tooling, published so customers can read what runs on their own machines. Issues
and pull requests are not monitored; support goes through your contract.

Nothing here patches LibreChat. Everything this repository does to it goes
through its own configuration or its own HTTP API.

---

## Two profiles, and the difference is the audit trail

|  | developer | enterprise |
|---|---|---|
| credential | one ordinary API key | one **gateway** credential, `--act-as` |
| who the deployment sees | the key | **the person who signed in** |
| an audit row reads | `apikey/V7S80Q12` | `identity/6a8f44f9… via apikey/QQ5WDKKE` |
| model catalogue | what the key may call | what **that person** may call |
| rate limits | shared by everyone | per person |
| registration | open until the first account | closed |
| who may use it | anyone with an account here | people an operator imported |

Those two rows are the same deployment, one command apart. Pick the developer
profile for one person on one laptop. Pick the enterprise profile for anything
where "who generated this" is a question somebody will be asked.

### Before either

```bash
cp .env.example .env
```

Fill in three things: where your deployment serves `/v1`, the path to its
`ca.crt` on this machine, and a credential. `./diffuse-chat up` writes the rest
itself — LibreChat's four secrets and the service account it uses to own the
shared agent — into the same file, mode 0600. **`.env` is not committed and must
not be.**

### The developer profile

```bash
diffuse-coordinator apikey create --name chat      # on the coordinator
./diffuse-chat up
./diffuse-chat doctor
```

Open `http://127.0.0.1:3080`, create your account, and chat. Registration closes
by itself: the next `up` sees a person and shuts the door behind you.

### The enterprise profile

```bash
diffuse-coordinator apikey create --name chat --act-as    # on the coordinator
diffuse-coordinator identity import users.csv             # who may use it
./diffuse-chat up --enterprise
./diffuse-chat doctor
```

Registration is closed in this profile. The people who may use the deployment
are the ones in `users.csv`, and an account here that the deployment does not
know is refused by the endpoint with a message saying so.

The gateway credential is a master key for your organisation's traffic. Read
`THREAT_MODEL.md` before you deploy it — one page, and the first section is the
one that matters.

### The other two verbs

```bash
./diffuse-chat doctor          # what is actually working, and if not, why
./diffuse-chat down            # stop it
./diffuse-chat down --volumes  # and forget the conversations and accounts
```

`doctor` checks the things that break in practice: the images running are the
digests this repository pins, LibreChat answers, the deployment's CA is mounted
where node will look for it, the TLS chain validates **from inside the
container**, the endpoint answers this credential the way this profile expects,
and the default agent exists *and is shared*.

---

## Branding

`APP_TITLE` and `CUSTOM_FOOTER` in `.env`; images in `branding/assets`, mounted
over LibreChat's own. See `branding/README.md`. A customer's logo never means a
rebuilt image and never means a fork.

`titleConvo` is **off** by default. A conversation title is a second generation
per conversation: it costs your own machines compute nobody asked for, and it
puts a model-written summary of the conversation into the façade's database — a
second copy of content, in a store your deployment's retention rules do not
reach. Turn it on deliberately or not at all.

---

## v0.8.7, what the upstream documentation does not say

Five facts, each of which cost real time to find. All measured against
`ghcr.io/danny-avila/librechat@sha256:c5db3331…`, the digest this repository
pins, not against a tag and not against the development branch.

### 1. There is no direct chat. Every conversation needs an agent

There is no `/api/ask` route. Everything goes through `/api/agents/chat` and
requires an `agent_id`; a custom endpoint is reached through an agent that names
it as a *provider*. Out of the box the composer says "Please select an Agent"
and nothing can be sent.

**So `./diffuse-chat up` provisions one**, called `Diffuse`, and shares it with
everybody who can sign in. A shipped profile that told each user to build their
own agent first would not be a product.

It is created through `POST /api/agents` and shared through
`PUT /api/permissions/agent/<_id>`, which is what the UI does. Seeding the
`agents` collection in Mongo directly — the obvious shortcut, and what the smoke
test tried first — half-works: the document appears, and then a plain user is
refused **their own** agent with "Insufficient permissions to access this
agent", because v0.8.7 gates agents on ACL rows in a separate collection that a
hand-written document does not create. Going through the API makes LibreChat
write its own ACL rows, which is also a schema this repository then never has to
track.

Two smaller traps in the same corner: the permissions API is keyed on the Mongo
`_id`, not on the `id` string the rest of the agent API uses (passing the wrong
one answers `400 Invalid resource ID`), and the agent schema requires a `model`
even though the person picks one afterwards.

### 2. `endpointsMenu` and `modelSelect` are off, and turning them on is not enough

v0.8.7 hides the endpoint picker and the model selector by default. Both configs
here re-enable them, so a person can see which deployment they are talking to —
but that is a convenience, **not** what makes the chat work. Re-enabling them
was tried during the smoke test and the composer still demanded an agent. If you
remove the provisioning step above expecting these two settings to cover it, you
get a stack nobody can send a message from.

### 3. `uaParser` refuses anything that is not a browser

`api/server/middleware/uaParser.js` answers `{"message":"Illegal request"}` to
any request whose user agent is not a browser. It applies to the whole API and
looks nothing like a permission problem — it cost the smoke test more than every
other obstacle combined, because agent creation and every chat attempt failed
identically for a reason that was neither.

**So every call `./diffuse-chat` makes to LibreChat presents a browser user
agent**, with a comment in the source saying why. If you script against this
stack yourself, do the same.

### 4. A refusal from the deployment is not shown to the person

This is the one to know about before a customer asks.

When the deployment refuses a request — the person was disabled, or was never
imported, or their identity could not be established — it answers 403 with a
sentence written to be acted on:

```
the user the gateway asserted is disabled here. Re-enable them with
`diffuse-coordinator identity enable 6a8f44f9bc4f9191e4179b87`.
```

**The person does not see that sentence.** `POST /api/agents/chat` answers
`200 {"status":"started"}` and the failure arrives inside the SSE stream. What
the browser actually receives, measured:

```
event: error
data: {"error":"{ \"type\": \"illegal_model_request\", \"info\": \"Diffuse|diffuse-demo\" }"}
```

The 403 refuses the catalogue fetch first, so LibreChat concludes the model is
not available and rejects the request before ever calling the endpoint. The
error a user reads therefore blames **the model**, which is not the cause.

**What an operator needs to know:** the user reports "illegal model request" or
a chat that does nothing; the real cause is one command away, on the deployment
and not here:

```bash
diffuse-coordinator audit --via <gateway-handle> --result denied
```

Every refused assertion is on that trail — the identity that was attempted, the
credential it came through, and which of the refusals it was.

**Is there a configuration workaround?** One, and it is a trade rather than a
fix: with `models.fetch: false` and the model named literally in `default`,
LibreChat calls the endpoint anyway and logs the deployment's real sentence
verbatim in its own container log — but the person then sees an *empty* reply
instead of an error, and the catalogue stops being filtered per person, which is
a feature the enterprise profile exists to provide. Shipped as `fetch: true` for
that reason: a visible-but-wrong error the operator can diagnose from the audit
trail beats a silent one, and per-person catalogues are worth keeping.

### 5. `${VARIABLES}` are not substituted inside `models`

They are substituted in `apiKey` and `baseURL` and arrive **literally** inside
`models.default`, where they would show up in the picker as their own name. And
`models.default` may not be empty, even with `fetch: true` — the config schema
requires at least one element. So both config files carry a literal placeholder
there, which is only ever displayed when the deployment cannot be reached.

---

## What is also here

- `THREAT_MODEL.md` — the façade side of design 021 §6.
- `evidence/smoke-verdict.md` — what LibreChat actually sends, captured whole,
  from two different accounts.
- `evidence/delegation-demo.md` — the same stack in front of a real deployment
  built from the release packages: two people, two audit rows, one credential.
- `compose.smoke.yaml`, `receiver/` — the capture stub those two were measured
  with. Kept because a version bump re-runs that measurement rather than
  assuming it still holds.
