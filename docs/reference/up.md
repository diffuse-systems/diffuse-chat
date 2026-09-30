# `diffuse-chat up`

Start the stack.

## Synopsis

```
./diffuse-chat up [OPTIONS]
```

## Options

| flag | type | default | description |
|---|---|---|---|
| `--enterprise` | switch | - | The gateway profile: the façade acts for each person. |

## Notes

Writes the rest of `.env` itself, LibreChat's secrets and the service account that owns the shared agent, starts LibreChat on `http://127.0.0.1:3080`, and provisions the agent everybody chats with. Run it again after changing `.env`: it recreates what it configured. In the developer profile, registration closes by itself once somebody has an account; in the gateway profile it is closed from the start.

## Examples

```bash
$ ./diffuse-chat up
```

```bash
$ ./diffuse-chat up --enterprise
```

---

[← All commands](index.md)
