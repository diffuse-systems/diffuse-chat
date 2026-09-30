# `diffuse-chat down`

Stop the stack.

## Synopsis

```
./diffuse-chat down [OPTIONS]
```

## Options

| flag | type | default | description |
|---|---|---|---|
| `--volumes` | switch | - | Also delete the volumes: the conversations, the uploads and the accounts go with them. |

## Notes

Stops the containers and keeps what they stored. `--volumes` also deletes the conversations, the uploads and the accounts.

## Examples

```bash
$ ./diffuse-chat down
```

```bash
$ ./diffuse-chat down --volumes
```

---

[← All commands](index.md)
