## Where to start

`./diffuse-chat` puts a chat interface in front of a deployment that already
serves a model. It runs from its repository, on the machine that runs the
interface:

```bash
git clone https://github.com/diffuse-systems/diffuse-chat.git
cd diffuse-chat
cp .env.example .env
```

In `.env`: the coordinator's `/v1` address, the path to a copy of its
`/etc/diffuse/ca.crt`, and the key from one of the two cases below.

### Chat on your own machine, with one key

On the coordinator, [give an application a key](../cli/apikey.md#give-an-application-a-key)
named `chat`, and put it in `.env` as `DIFFUSE_TOKEN`. Then, here:

```bash
./diffuse-chat up
./diffuse-chat doctor
```

[`up`](up.md) starts it on `http://127.0.0.1:3080`; the first account created
there closes registration behind it. [`doctor`](doctor.md) says what works, and
what does not with the reason.

### Chat for an organisation, as each person

The deployment then records who asked, not which key. On the coordinator,
[a key that acts for each person](../cli/apikey.md#a-key-for-a-chat-interface-that-acts-for-each-person),
in `.env` as `DIFFUSE_GATEWAY_TOKEN`, and
[the people it acts for](../cli/identity.md#import-the-people-from-your-directory).
Then, here:

```bash
./diffuse-chat up --enterprise
./diffuse-chat doctor
```

[`up --enterprise`](up.md): registration stays closed, and somebody not imported
on the coordinator is refused by it. [`doctor`](doctor.md) reads the profile
from what is running.

### After changing `.env`

A new key, a moved coordinator, a new title: the same `up` again recreates
what it configured. With the flag of the profile that runs, because `up`
without `--enterprise` starts the one-key profile.

```bash
./diffuse-chat up --enterprise
./diffuse-chat doctor
```

[`up`](up.md) · [`doctor`](doctor.md)

### Stop it, or remove it

```bash
./diffuse-chat down
./diffuse-chat down --volumes
```

[`down`](down.md) keeps the conversations and the accounts; with `--volumes`
they go with it.
