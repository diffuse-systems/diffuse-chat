# `diffuse-chat users`

Create and disable chat accounts.

## Synopsis

```
./diffuse-chat users
```

## Notes

Creates chat accounts from a CSV of `email,name,password`, an empty password generated and shown once, reads each account's id, writes `identities.csv` for the coordinator and runs `identity import` when the coordinator is on this machine. `disable` refuses every request for a person on the coordinator and keeps their history.

## Examples

```bash
$ ./diffuse-chat users import users.csv
```

```bash
$ ./diffuse-chat users add marie@klinik.example 'Marie Weber'
```

```bash
$ ./diffuse-chat users list
```

```bash
$ ./diffuse-chat users disable jonas@klinik.example
```

---

[← All commands](index.md)
