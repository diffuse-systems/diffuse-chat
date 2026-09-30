#!/usr/bin/env python3
"""The CLI reference stays true to the script.

    python3 -m unittest discover -s tests -p 'test_*.py'

Four promises, each a test:

- the committed pages are the ones `scripts/cli_reference.py` generates, so a
  flag added to the script without regenerating fails here, not on a reader;
- every example on those pages is a command line the script accepts;
- every command in a use case, `docs/reference/*.cases.md`, the only pages
  written by hand, is one the script accepts, and its use case links the page
  of the command it runs;
- every option has a line of help, because that line is its documentation.

The commands are read the way the coordinator's reference reads its own: from
the `bash` blocks, a comment dropped, `\\` continuing a line, `&&`, `||`, `;`
and `|` separating commands, and `sudo` or `NAME=value` in front of one not
its program. Nothing is run: each is given to the parser.
"""

import argparse
import contextlib
import importlib.machinery
import importlib.util
import io
import pathlib
import sys
import unittest

sys.dont_write_bytecode = True

HERE = pathlib.Path(__file__).resolve().parents[1]
REFERENCE = HERE / "docs" / "reference"
PROGRAM = "diffuse-chat"


def module(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    loaded = importlib.util.module_from_spec(spec)
    loader.exec_module(loaded)
    return loaded


GENERATOR = module("cli_reference", HERE / "scripts" / "cli_reference.py")


def parse(args):
    """What the script's parser makes of `args`: the namespace, or its error.

    `--help` counts as accepted: it is a command line the script answers.
    """
    parser = GENERATOR.load().build_parser()
    out, err = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            return parser.parse_args(args), None
    except SystemExit as exit_:
        if exit_.code in (0, None):
            return None, None
        lines = [line for line in err.getvalue().splitlines() if line.strip()]
        return None, lines[-1] if lines else f"exit {exit_.code}"


# ---------------------------------------------------------------------------
# Reading a page as a person pastes it
# ---------------------------------------------------------------------------


def strip_comment(line):
    out, quote, previous = [], None, " "
    for character in line:
        if quote and character == quote:
            quote = None
        elif not quote and character in "'\"":
            quote = character
        elif not quote and character == "#" and previous.isspace():
            break
        out.append(character)
        previous = character
    return "".join(out)


def split_commands(line):
    commands, current, quote, index = [], [], None, 0
    while index < len(line):
        character = line[index]
        following = line[index + 1] if index + 1 < len(line) else ""
        if quote:
            if character == quote:
                quote = None
            current.append(character)
        elif character in "'\"":
            quote = character
            current.append(character)
        elif character == "&" and following == "&":
            index += 1
            commands.append("".join(current))
            current = []
        elif character == "|":
            if following == "|":
                index += 1
            commands.append("".join(current))
            current = []
        elif character in ";)":
            commands.append("".join(current))
            current = []
        elif character == "$" and following == "(":
            index += 1
            commands.append("".join(current))
            current = []
        else:
            current.append(character)
        index += 1
    commands.append("".join(current))
    return [command for command in commands if command.strip()]


def shell_words(line):
    out, current, quote, started = [], [], None, False
    for character in line:
        if quote:
            if character == quote:
                quote = None
            else:
                current.append(character)
        elif character in "'\"":
            quote, started = character, True
        elif character.isspace():
            if started or current:
                out.append("".join(current))
                current, started = [], False
        else:
            current.append(character)
    if started or current:
        out.append("".join(current))
    return out


def is_redirection(word):
    return word.lstrip("0123456789").startswith((">", "<"))


def is_assignment(word):
    name, equals, _ = word.partition("=")
    return bool(equals and name and not name[0].isdigit()
                and all(c.isalnum() or c == "_" for c in name))


def invocations(page, program=PROGRAM):
    """Each `(case, line, text, args)` running `program` in the page's bash blocks."""
    found, case, in_bash, in_other, pending, pending_line = [], "", False, False, "", 0
    for number, raw in enumerate(page.splitlines(), start=1):
        trimmed = raw.lstrip()
        if trimmed.startswith("```"):
            if in_bash or in_other:
                in_bash = in_other = False
            elif trimmed[3:].strip() in ("bash", "sh", "shell"):
                in_bash = True
            else:
                in_other = True
            continue
        if in_other:
            continue
        if not in_bash:
            for prefix in ("### ", "## "):
                if trimmed.startswith(prefix):
                    case = trimmed[len(prefix):].strip()
            continue

        text = strip_comment(trimmed.removeprefix("$ "))
        if not pending:
            pending_line = number
        if text.rstrip().endswith("\\"):
            pending += text.rstrip()[:-1] + " "
            continue
        whole, pending = pending + text, ""

        for command in split_commands(whole):
            words = []
            for word in shell_words(command):
                if is_redirection(word):
                    break
                words.append(word)
            if words and words[0] == "sudo":
                words = words[1:]
                while words and words[0].startswith("-"):
                    takes_value = words[0] in ("-u", "-g", "-C", "-h", "-p")
                    words = words[2:] if takes_value else words[1:]
            while words and is_assignment(words[0]):
                words = words[1:]
            if words and (words[0] == program or words[0].rsplit("/", 1)[-1] == program):
                found.append((case, pending_line, command.strip(), words[1:]))
    return found


def links_by_case(page):
    links, case, in_block = {}, "", False
    for line in page.splitlines():
        trimmed = line.lstrip()
        if trimmed.startswith("```"):
            in_block = not in_block
            continue
        if in_block:
            continue
        for prefix in ("### ", "## "):
            if trimmed.startswith(prefix):
                case = trimmed[len(prefix):].strip()
        rest = line
        while "](" in rest:
            after = rest[rest.index("](") + 2:]
            if ")" not in after:
                break
            links.setdefault(case, []).append(after[:after.index(")")].strip())
            rest = after[after.index(")") + 1:]
    return links


# ---------------------------------------------------------------------------
# The promises
# ---------------------------------------------------------------------------


class Reference(unittest.TestCase):
    def test_the_committed_pages_are_the_generated_ones(self):
        emitted = GENERATOR.pages(GENERATOR.load().build_parser())
        committed = {
            path.name: path.read_text()
            for path in REFERENCE.glob("*.md")
            if not path.name.endswith(GENERATOR.CASES_SUFFIX)
        }
        differ = sorted(set(committed) ^ set(emitted)) + sorted(
            name for name in set(committed) & set(emitted) if committed[name] != emitted[name]
        )
        if differ:
            self.fail("these pages are not what the script generates: "
                      + ", ".join(f"docs/reference/{name}" for name in differ)
                      + "\n  run: python3 scripts/cli_reference.py")

    def test_every_example_parses(self):
        broken = []
        for command, note in GENERATOR.NOTES.items():
            for example in note.get("examples", []):
                words = shell_words(example)
                _, error = parse(words[1:])
                if error:
                    broken.append(f"{command}: $ {example}\n    {error}")
        if broken:
            self.fail("these examples are not command lines the script accepts:\n  "
                      + "\n  ".join(broken))

    def test_every_command_in_the_use_cases_parses_and_links_its_page(self):
        pages = sorted(REFERENCE.glob("*" + GENERATOR.CASES_SUFFIX))
        self.assertTrue(pages, "no use-case page in docs/reference")
        seen, broken, unlinked = 0, [], []
        for path in pages:
            page = path.read_text()
            links = links_by_case(page)
            for case, line, text, args in invocations(page):
                seen += 1
                namespace, error = parse(args)
                if error:
                    broken.append(f"{path.name}:{line} ({case}):\n    $ {text}\n    {error}")
                    continue
                if namespace is None:
                    continue
                target = f"{namespace.command}.md"
                if not any(link == target or link.startswith(target + "#")
                           for link in links.get(case, [])):
                    unlinked.append(f'{path.name}:{line} ("{case}") runs '
                                    f"`{namespace.command}` and does not link {target}")
        self.assertGreater(seen, 0, "no use case runs ./diffuse-chat: the scan is "
                           "not looking where the pages are")
        problems = []
        if broken:
            problems.append("these commands in the use cases are not command lines the "
                            "script accepts, so a reader who copies them meets an "
                            "error:\n  " + "\n  ".join(broken))
        if unlinked:
            problems.append("each use case links the reference page of every command "
                            "it runs:\n  " + "\n  ".join(unlinked))
        if problems:
            self.fail("\n".join(problems))

    def test_the_reference_opens_on_its_use_cases(self):
        self.assertTrue((REFERENCE / ("index" + GENERATOR.CASES_SUFFIX)).is_file(),
                        "docs/reference/index.cases.md is where a reader starts")

    def test_every_option_has_a_line_of_help(self):
        bare = []
        for name, sub, help_text in GENERATOR.subcommands(GENERATOR.load().build_parser()):
            if not help_text:
                bare.append(name)
            for action in GENERATOR.options(sub):
                if not action.help or action.help == argparse.SUPPRESS:
                    bare.append(f"{name} {'/'.join(action.option_strings)}")
        if bare:
            self.fail("the reference is the script's help; these have none: "
                      + ", ".join(bare))


class Reading(unittest.TestCase):
    """The reader agrees with the coordinator's on the lines that matter."""

    def test_a_command_is_found_behind_comments_continuations_and_separators(self):
        page = (
            "### A case\n"
            "```bash\n"
            "cd diffuse-chat && ./diffuse-chat up \\\n"
            "    --enterprise  # the gateway profile\n"
            "FOO=1 ./diffuse-chat doctor > report.txt\n"
            "sudo -u chat ./diffuse-chat down --volumes\n"
            "```\n"
            "```text\n"
            "./diffuse-chat not-a-command\n"
            "```\n"
        )
        self.assertEqual(
            [(case, line, args) for case, line, _text, args in invocations(page)],
            [
                ("A case", 3, ["up", "--enterprise"]),
                ("A case", 5, ["doctor"]),
                ("A case", 6, ["down", "--volumes"]),
            ],
        )

    def test_a_link_belongs_to_the_case_above_it(self):
        page = "### One\n[`up`](up.md)\n```bash\n[x](not-a-link.md)\n```\n### Two\n[a](b.md#c)"
        self.assertEqual(links_by_case(page), {"One": ["up.md"], "Two": ["b.md#c"]})

    def test_a_flag_the_script_does_not_take_is_refused(self):
        _, error = parse(["down", "--forget"])
        self.assertIn("unrecognized arguments: --forget", error or "")


if __name__ == "__main__":
    unittest.main()
