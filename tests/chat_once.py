#!/usr/bin/env python3
"""One message through the façade, as a person, and what the deployment recorded.

Used by `tests/acceptance.sh`. Split out because the interesting part is not
sending the message — it is waiting for the deployment's own audit row and
checking its **shape**, which is the only thing that distinguishes the two
profiles from the outside.

    chat_once.py dev    expects a row naming the credential and nobody else
    chat_once.py ent    expects a row naming the person, and the credential
    chat_once.py import registers nothing; imports the account into the deployment
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

# See the README's "v0.8.7" section, fact 3: uaParser refuses anything that is
# not a browser, for the whole API, with a message that looks like a permission
# problem and is not.
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/140.0.0.0 Safari/537.36")

BASE = os.environ.get("CHAT_BASE", "http://127.0.0.1:3080")
EMAIL = os.environ.get("CHAT_EMAIL", "acceptance@example.invalid")
PASSWORD = os.environ.get("CHAT_PASSWORD", "Passwort-Acceptance-2026")
MODEL = os.environ.get("DIFFUSE_MODEL", "diffuse-demo")

# How the test reads the deployment's audit trail. Overridable because a
# customer's coordinator is not in a container called `diffuse-api`.
AUDIT = os.environ.get(
    "DIFFUSE_AUDIT_CMD",
    "docker exec diffuse-api diffuse-coordinator audit "
    "--action inference --limit 20 --config /home/lot3/coordinator.toml",
)


def call(path, payload=None, token=None, timeout=180):
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(BASE + path, data=data)
    request.add_header("User-Agent", UA)
    request.add_header("Accept", "application/json")
    if data:
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace")
    except Exception as error:  # noqa: BLE001
        return 0, repr(error)


def sign_in():
    status, body = call("/api/auth/login", {"email": EMAIL, "password": PASSWORD})
    if status != 200:
        return None, None
    payload = json.loads(body)
    return payload["token"], payload["user"]["id"]


def inference_rows():
    run = subprocess.run(AUDIT, shell=True, capture_output=True, text=True)
    return [line for line in run.stdout.splitlines() if " inference " in line]


mode = sys.argv[1]

if mode == "import":
    # The id is read from the façade's database rather than by signing in.
    # **Two logins for one account seconds apart cost a 401** — v0.8.7
    # invalidates the older session, and the import step used to mint one right
    # before the chat step minted another. Observed once in three runs, which is
    # exactly the kind of flake that gets blamed on the product later.
    run = subprocess.run(
        ["docker", "compose", "-f", "compose.yaml", "exec", "-T", "mongo",
         "mongosh", "--quiet", "LibreChat", "--eval",
         f'var u = db.users.findOne({{email: "{EMAIL}"}}); '
         f'print(u ? u._id.toString() : "")'],
        capture_output=True, text=True,
    )
    uid = run.stdout.strip().splitlines()[-1] if run.stdout.strip() else ""
    if len(uid) != 24:
        print(f"  FAIL  could not read the account id from the façade: {uid!r}")
        sys.exit(1)
    csv = f"subject,address,models,pool\n{uid},{EMAIL},,\n"
    subprocess.run(
        ["docker", "exec", "-i", "diffuse-api", "sh", "-c",
         "cat > /tmp/u.csv && diffuse-coordinator identity import /tmp/u.csv "
         "--config /home/lot3/coordinator.toml"],
        input=csv, text=True, capture_output=True,
    )
    print(f"  imported {uid} into the deployment")
    sys.exit(0)

call("/api/auth/register", {
    "name": "Acceptance", "username": "acceptance",
    "email": EMAIL, "password": PASSWORD, "confirm_password": PASSWORD,
})
token, uid = sign_in()
if not token:
    print("  FAIL  could not sign in")
    sys.exit(1)
print(f"  signed in as {uid}")

# The agent `up` provisioned, seen by a **plain** user. That is the assertion,
# not its existence: an agent with no ACL row exists and is refused to everybody
# but its owner, which is the trap the README's fact 1 is about.
status, body = call("/api/agents", token=token)
items = (json.loads(body).get("data") if status == 200 else []) or []
agent = next((item["id"] for item in items if item.get("name") == "Diffuse"), None)
if not agent:
    print("  FAIL  the provisioned agent is not visible to a plain user")
    sys.exit(1)
print(f"  the shared agent is visible to a plain user: {agent}")

def settle(quiet_for=15, deadline_s=240):
    """Waits until the deployment's trail stops growing.

    A generation against the fixture model runs to its token ceiling and takes
    half a minute, so a row from the *previous* profile can land in the middle
    of this one and be mistaken for its answer. Draining first is what makes
    "the next row is mine" true rather than probable.
    """
    deadline = time.time() + deadline_s
    seen = len(inference_rows())
    quiet_since = time.time()
    while time.time() < deadline:
        time.sleep(3)
        now = len(inference_rows())
        if now != seen:
            seen, quiet_since = now, time.time()
        elif time.time() - quiet_since >= quiet_for:
            return seen
    return len(inference_rows())


before = settle()

status, body = call("/api/agents/chat", {
    "conversationId": str(uuid.uuid4()),
    "parentMessageId": "00000000-0000-0000-0000-000000000000",
    "messageId": str(uuid.uuid4()),
    "text": f"hallo aus dem {mode}-profil",
    "sender": "User", "isCreatedByUser": True,
    "endpoint": "agents", "agent_id": agent, "model": MODEL,
    "endpointType": "agents", "key": "never",
}, token=token)
print(f"  POST /api/agents/chat -> {status}")
if status != 200:
    print(f"  FAIL  {body[:200]}")
    sys.exit(1)

# **Waited for, not assumed.** A trail read too early still holds the previous
# profile's row, and the test would pass for the wrong reason.
deadline = time.time() + 240
landed = None
while time.time() < deadline:
    rows = inference_rows()
    if len(rows) > before:
        landed = rows[-1]
        break
    time.sleep(3)

if landed is None:
    print("  FAIL  no inference row reached the deployment in four minutes")
    sys.exit(1)

delegated = "identity/" in landed and " via apikey/" in landed
if mode == "dev":
    if delegated:
        print(f"  FAIL  the developer profile named a person: {landed[:110]}")
        sys.exit(1)
    print("  the row names the credential and nobody else, as this profile promises")
else:
    if not delegated or uid not in landed:
        print(f"  FAIL  the enterprise profile did not name this person: {landed[:110]}")
        sys.exit(1)
    print("  the row names this person, and the credential they came through")
