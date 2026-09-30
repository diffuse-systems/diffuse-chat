# `diffuse-chat doctor`

Check what is actually working.

## Synopsis

```
./diffuse-chat doctor [OPTIONS]
```

## Options

| flag | type | default | description |
|---|---|---|---|
| `--enterprise` | switch | - | Check the gateway profile; without it, the profile is read from what is running. |

## Notes

Checks what breaks in practice, and changes nothing: the images running are the digests this repository pins, LibreChat answers, the deployment's CA is mounted where node looks for it, the TLS chain validates from inside the container, the endpoint answers this credential the way the profile expects, and the default agent exists and is shared.

## Examples

```bash
$ ./diffuse-chat doctor
```

```bash
$ ./diffuse-chat doctor --enterprise
```

---

[← All commands](index.md)
