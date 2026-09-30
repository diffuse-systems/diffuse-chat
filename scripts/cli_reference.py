#!/usr/bin/env python3
"""The CLI reference of `./diffuse-chat`, generated from its own parser.

    python3 scripts/cli_reference.py            # writes docs/reference/
    python3 scripts/cli_reference.py --check    # fails if the pages differ

**The prose is the parser's.** Each page is built from the `argparse` tree the
script runs with, so an option added without a line of help is a defect in the
script rather than a gap in a page, and `tests/test_reference.py` fails when
the committed pages stop matching what this emits. The same layout as the
coordinator's and the node agent's references, which the documentation site
shows side by side.

What the parser cannot know is here, as data: an example of each command and a
note on what it does. No output is shown that was not printed by a real run.
The use cases, `docs/reference/*.cases.md`, are written by hand; the tests
parse every command they show.
"""

import argparse
import importlib.machinery
import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = HERE / "diffuse-chat"
OUT = HERE / "docs" / "reference"
CASES_SUFFIX = ".cases.md"

INTRO = (
    "Every command of `diffuse-chat`, generated from the script itself. If a page "
    "here disagrees with what your terminal prints, the page is a bug: a test "
    "regenerates all of this and fails on any difference.\n\n"
    "`./diffuse-chat` is the script at the root of the diffuse-chat repository. It "
    "runs from inside that directory, on the machine that runs the chat "
    "interface, which needs Docker with the compose plugin and a route to the "
    "coordinator's `/v1` port."
)

NOTES = {
    "up": {
        "remark": (
            "Writes the rest of `.env` itself, LibreChat's secrets and the service "
            "account that owns the shared agent, starts LibreChat on "
            "`http://127.0.0.1:3080`, and provisions the agent everybody chats "
            "with. Run it again after changing `.env`: it recreates what it "
            "configured. In the developer profile, registration closes by itself "
            "once somebody has an account; in the gateway profile it is closed "
            "from the start."
        ),
        "examples": ["./diffuse-chat up", "./diffuse-chat up --enterprise"],
    },
    "doctor": {
        "remark": (
            "Checks what breaks in practice, and changes nothing: the images "
            "running are the digests this repository pins, LibreChat answers, the "
            "deployment's CA is mounted where node looks for it, the TLS chain "
            "validates from inside the container, the endpoint answers this "
            "credential the way the profile expects, and the default agent exists "
            "and is shared."
        ),
        "examples": ["./diffuse-chat doctor", "./diffuse-chat doctor --enterprise"],
    },
    "down": {
        "remark": (
            "Stops the containers and keeps what they stored. `--volumes` also "
            "deletes the conversations, the uploads and the accounts."
        ),
        "examples": ["./diffuse-chat down", "./diffuse-chat down --volumes"],
    },
}


def load():
    """The script as a module: its definitions, without running `main`."""
    loader = importlib.machinery.SourceFileLoader("diffuse_chat", str(SCRIPT))
    spec = importlib.util.spec_from_loader("diffuse_chat", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def subcommands(parser):
    """The verbs, in the order the parser declares them, with their help."""
    # argparse has no public way to walk its tree, so this reads its attributes.
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            helps = {choice.dest: choice.help for choice in action._choices_actions}
            for name, sub in action.choices.items():
                yield name, sub, helps.get(name) or ""


def options(sub):
    """Each option a verb takes, help excluded."""
    return [
        action
        for action in sub._actions
        if action.option_strings and not isinstance(action, argparse._HelpAction)
    ]


def sentence(text):
    """A help string as the first sentence of a page: capital, full stop."""
    text = text.strip()
    if not text:
        return text
    text = text[0].upper() + text[1:]
    return text if text.endswith(".") else text + "."


def kind(action):
    if isinstance(action, (argparse._StoreTrueAction, argparse._StoreFalseAction)):
        return "switch"
    if action.choices:
        return "one of " + ", ".join(f"`{choice}`" for choice in action.choices)
    return "text"


def default(action):
    if isinstance(action, (argparse._StoreTrueAction, argparse._StoreFalseAction)):
        return "-"
    return f"`{action.default}`" if action.default not in (None, "") else "-"


def page(name, sub, help_text):
    lines = [f"# `diffuse-chat {name}`", "", sentence(help_text), "", "## Synopsis", ""]
    usage = f"./diffuse-chat {name}" + (" [OPTIONS]" if options(sub) else "")
    lines += ["```", usage, "```", ""]
    if options(sub):
        lines += ["## Options", "", "| flag | type | default | description |", "|---|---|---|---|"]
        for action in options(sub):
            flag = ", ".join(f"`{option}`" for option in action.option_strings)
            description = sentence(action.help or "").replace("|", "\\|")
            lines.append(f"| {flag} | {kind(action)} | {default(action)} | {description} |")
        lines.append("")
    note = NOTES.get(name, {})
    if note.get("remark"):
        lines += ["## Notes", "", note["remark"], ""]
    lines += ["## Examples", ""]
    for example in note.get("examples", []):
        lines += ["```bash", f"$ {example}", "```", ""]
    lines += ["---", "", "[← All commands](index.md)"]
    return "\n".join(lines) + "\n"


def index(parser):
    lines = ["# CLI reference", "", INTRO, ""]
    for name, _sub, help_text in subcommands(parser):
        lines += [f"## [`{name}`]({name}.md)", "", sentence(help_text), ""]
        first = NOTES.get(name, {}).get("examples", [])
        if first:
            lines += ["```bash", first[0], "```", ""]
    return "\n".join(lines)


def pages(parser):
    """Every page, by file name."""
    out = {"index.md": index(parser)}
    missing = []
    for name, sub, help_text in subcommands(parser):
        if not NOTES.get(name, {}).get("examples"):
            missing.append(name)
        out[f"{name}.md"] = page(name, sub, help_text)
    if missing:
        raise SystemExit(
            "these commands have no example, so their page would be a table and "
            f"nothing else. Add one to NOTES: {', '.join(missing)}"
        )
    return out


def main(argv):
    arguments = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    arguments.add_argument("--out", type=pathlib.Path, default=OUT)
    arguments.add_argument("--check", action="store_true",
                           help="fail if the committed pages differ from these")
    args = arguments.parse_args(argv)

    emitted = pages(load().build_parser())
    if args.check:
        committed = {
            path.name: path.read_text()
            for path in args.out.glob("*.md")
            if not path.name.endswith(CASES_SUFFIX)
        }
        if committed != emitted:
            differ = sorted(set(committed) ^ set(emitted)) + sorted(
                name for name in set(committed) & set(emitted)
                if committed[name] != emitted[name]
            )
            print("the committed reference differs from the script's: " + ", ".join(differ))
            print("run: python3 scripts/cli_reference.py")
            return 1
        return 0

    args.out.mkdir(parents=True, exist_ok=True)
    for name, text in emitted.items():
        (args.out / name).write_text(text)
    print(f"CLI reference written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
