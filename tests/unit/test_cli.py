"""End-to-end CLI integration tests.

These invoke `ast_outline.cli.main` directly and capture stdout/stderr,
so we don't need to spawn a subprocess.
"""
from __future__ import annotations

from ast_outline.cli import main


# --- Default / guide -----------------------------------------------------


def test_main_with_no_args_prints_guide(capsys):
    rc = main([])
    out = capsys.readouterr().out
    assert rc == 0
    assert "ast-outline" in out
    assert "COMMANDS" in out


def test_help_command(capsys):
    rc = main(["help"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "COMMANDS" in out


def test_help_topic_specific(capsys):
    rc = main(["help", "show"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "show" in out.lower()
    assert "symbols" in out.lower()


# --- outline -------------------------------------------------------------


def test_outline_implicit_subcommand(csharp_dir, capsys):
    """`ast-outline path.cs` with no subcommand should default to `outline`."""
    rc = main([str(csharp_dir / "unity_behaviour.cs")])
    out = capsys.readouterr().out
    assert rc == 0
    assert "HeroController" in out
    assert "TakeDamage" in out


def test_outline_explicit_subcommand(csharp_dir, capsys):
    rc = main(["outline", str(csharp_dir / "unity_behaviour.cs")])
    out = capsys.readouterr().out
    assert rc == 0
    assert "HeroController" in out


def test_outline_directory_mixed_languages(fixtures_dir, capsys):
    rc = main([str(fixtures_dir)])
    out = capsys.readouterr().out
    assert rc == 0
    # Both C# and Python symbols appear in one pass
    assert "HeroController" in out
    assert "UserService" in out


def test_outline_no_private_flag(csharp_dir, capsys):
    rc = main(["outline", str(csharp_dir / "unity_behaviour.cs"), "--no-private"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Die" not in out


def test_outline_no_lines_flag(csharp_dir, capsys):
    rc = main(["outline", str(csharp_dir / "unity_behaviour.cs"), "--no-lines"])
    out = capsys.readouterr().out
    assert rc == 0
    # Header is exempt; check signature lines
    body = "\n".join(out.splitlines()[1:])
    assert "  L" not in body


def test_outline_missing_file_returns_zero_with_note(tmp_path, capsys):
    """LLM-friendly mode: rc=0 + short ``# note:`` line on stdout so a
    parallel batch in Claude Code doesn't abort the whole chain."""
    nope = tmp_path / "nope.cs"
    rc = main(["outline", str(nope)])
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.err == ""
    assert "# note:" in captured.out
    assert "path not found" in captured.out.lower()
    assert str(nope) in captured.out


# --- show ----------------------------------------------------------------


def test_show_single_symbol(csharp_dir, capsys):
    rc = main(["show", str(csharp_dir / "unity_behaviour.cs"), "HeroController.TakeDamage"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "public void TakeDamage" in out
    assert "OnHealthChanged" in out  # part of the method body


def test_show_prints_ancestor_breadcrumb(csharp_dir, capsys):
    """The `# in:` line lists enclosing namespace/type so the agent knows
    what the extracted body is nested inside, without a second `outline`."""
    rc = main(["show", str(csharp_dir / "unity_behaviour.cs"), "HeroController.TakeDamage"])
    out = capsys.readouterr().out
    assert rc == 0
    # Breadcrumb line starts with `# in:` and contains both ancestor signatures
    in_lines = [ln for ln in out.splitlines() if ln.startswith("# in:")]
    assert len(in_lines) == 1
    assert "namespace" in in_lines[0]
    assert "HeroController" in in_lines[0]
    assert "→" in in_lines[0]  # separator between outer and inner


def test_show_multiple_symbols(csharp_dir, capsys):
    rc = main(
        [
            "show",
            str(csharp_dir / "unity_behaviour.cs"),
            "HeroController.TakeDamage",
            "HeroController.Die",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "TakeDamage" in out
    assert "Die" in out


def test_show_ambiguous_symbol_prints_all_matches(csharp_dir, capsys):
    rc = main(["show", str(csharp_dir / "unity_behaviour.cs"), "TakeDamage"])
    captured = capsys.readouterr()
    assert rc == 0
    # Both definitions present
    assert "public void TakeDamage" in captured.out
    assert "void TakeDamage(int amount);" in captured.out
    # Stderr mentions multiple matches
    assert "matches" in captured.err.lower()


def test_show_not_found_returns_zero_with_note(csharp_dir, capsys):
    """LLM-friendly mode: missing symbol yields rc=0 + ``# note:`` on stdout."""
    rc = main(["show", str(csharp_dir / "unity_behaviour.cs"), "NoSuchThing"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "# note:" in captured.out
    assert "not found" in captured.out.lower()


def test_show_no_doc_strips_leading_doc(csharp_dir, capsys):
    rc = main(
        [
            "show",
            str(csharp_dir / "unity_behaviour.cs"),
            "HeroController.TakeDamage",
            "--no-doc",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    # The ///-comment block is stripped
    assert "/// <summary>Apply damage" not in out
    assert "public void TakeDamage" in out


def test_show_python_method_with_docstring(python_dir, capsys):
    rc = main(["show", str(python_dir / "domain_model.py"), "UserService.get"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "def get" in out
    assert "Look up a user by id" in out


def test_show_python_strips_docstring_with_no_doc(python_dir, capsys):
    rc = main(
        ["show", str(python_dir / "domain_model.py"), "UserService.get", "--no-doc"]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "Look up a user by id" not in out
    assert "def get" in out


# --- digest --------------------------------------------------------------


def test_digest_directory(csharp_dir, capsys):
    rc = main(["digest", str(csharp_dir)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "HeroController" in out
    # Callables render with `()` suffix and no `+` prefix.
    assert "TakeDamage()" in out


def test_digest_missing_path_returns_zero_with_note(tmp_path, capsys):
    """LLM-friendly mode: missing path yields rc=0 + ``# note:`` on stdout."""
    rc = main(["digest", str(tmp_path / "nope")])
    captured = capsys.readouterr()
    assert rc == 0
    assert "# note:" in captured.out
    assert "not found" in captured.out.lower()


def test_digest_include_private(csharp_dir, capsys):
    rc = main(["digest", str(csharp_dir), "--include-private"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Die()" in out


# --- LLM-friendly error handling -----------------------------------------


def test_bad_subcommand_returns_zero_with_note(capsys):
    """A bogus subcommand must NOT call ``sys.exit`` with a non-zero code —
    that breaks parallel bash chains in Claude Code. Instead we expect a
    ``# note:`` line on stdout and rc=0."""
    rc = main(["help", "doesnotexist"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "# note:" in captured.out


def test_show_missing_file_returns_zero_with_note(tmp_path, capsys):
    rc = main(["show", str(tmp_path / "absent.cs"), "Foo"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "# note:" in captured.out
    assert "file not found" in captured.out.lower()


def test_show_unsupported_extension_returns_zero_with_note(tmp_path, capsys):
    """A file with an unsupported extension is a no-op, not a crash."""
    f = tmp_path / "hello.txt"
    f.write_text("not source code")
    rc = main(["show", str(f), "anything"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "# note:" in captured.out
    assert "no adapter" in captured.out.lower()


