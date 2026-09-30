# CLI reference

Every command of `diffuse-chat`, generated from the script itself. If a page here disagrees with what your terminal prints, the page is a bug: a test regenerates all of this and fails on any difference.

`./diffuse-chat` is the script at the root of the diffuse-chat repository. It runs from inside that directory, on the machine that runs the chat interface, which needs Docker with the compose plugin and a route to the coordinator's `/v1` port.

## [`up`](up.md)

Start the stack.

```bash
./diffuse-chat up
```

## [`doctor`](doctor.md)

Check what is actually working.

```bash
./diffuse-chat doctor
```

## [`down`](down.md)

Stop the stack.

```bash
./diffuse-chat down
```
