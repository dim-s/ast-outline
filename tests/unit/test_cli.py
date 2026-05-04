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


def test_version_flag_long(capsys):
    """`--version` follows the universal CLI convention and prints
    version + author on dedicated lines so a script can grep one
    field without prose-parsing."""
    from ast_outline import __version__

    rc = main(["--version"])
    out = capsys.readouterr().out
    assert rc == 0
    assert f"ast-outline {__version__}" in out
    assert "Dmitrii Zaitsev" in out
    assert "github.com/ast-outline/ast-outline" in out


def test_version_flag_short(capsys):
    """`-V` short form mirrors `git --version` / `rg --version` —
    both spellings produce identical output."""
    from ast_outline import __version__

    rc = main(["-V"])
    out = capsys.readouterr().out
    assert rc == 0
    assert f"ast-outline {__version__}" in out


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


# --- show --view signature -----------------------------------------------


def test_show_signature_view_csharp_omits_body(csharp_dir, capsys):
    """`--view signature` returns docs + attrs + signature, no method body.

    The agent's "I want the contract, not the implementation" view: useful
    after `digest` when the symbol name is known but the body would burn
    context. Body lines like the `{` / `}` and statements inside MUST NOT
    appear; the signature line and its leading XML doc MUST."""
    rc = main(
        [
            "show",
            str(csharp_dir / "unity_behaviour.cs"),
            "HeroController.TakeDamage",
            "--view",
            "signature",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    # XML doc + signature are present
    assert "/// <summary>Apply damage" in out
    assert "public void TakeDamage(int amount)" in out
    # Body content is NOT
    assert "CurrentHealth -=" not in out
    assert "OnHealthChanged" not in out


def test_show_signature_alias_equals_view_signature(csharp_dir, capsys):
    """`--signature` is a flag alias for `--view signature` — both should
    produce byte-identical output. If they ever diverge the agent gets a
    confusing UX where two equivalent forms behave differently."""
    rc1 = main(
        [
            "show",
            str(csharp_dir / "unity_behaviour.cs"),
            "HeroController.TakeDamage",
            "--signature",
        ]
    )
    out1 = capsys.readouterr().out
    rc2 = main(
        [
            "show",
            str(csharp_dir / "unity_behaviour.cs"),
            "HeroController.TakeDamage",
            "--view",
            "signature",
        ]
    )
    out2 = capsys.readouterr().out
    assert rc1 == 0 and rc2 == 0
    assert out1 == out2


def test_show_full_alias_equals_default(csharp_dir, capsys):
    """`--full` is a flag alias for `--view full` (the default). Output must
    match a no-flag invocation byte-for-byte — guard against accidental
    divergence in the depth-routing branch."""
    rc1 = main(
        ["show", str(csharp_dir / "unity_behaviour.cs"), "HeroController.TakeDamage"]
    )
    out1 = capsys.readouterr().out
    rc2 = main(
        [
            "show",
            str(csharp_dir / "unity_behaviour.cs"),
            "HeroController.TakeDamage",
            "--full",
        ]
    )
    out2 = capsys.readouterr().out
    assert rc1 == 0 and rc2 == 0
    assert out1 == out2


def test_show_view_aliases_are_mutually_exclusive(csharp_dir, capsys):
    """argparse's mutex group rejects `--signature --full` so the agent can
    never accidentally pass both. The CLI's LLM-friendly error path turns
    the parse failure into a `# note:` on stdout with rc=0."""
    rc = main(
        [
            "show",
            str(csharp_dir / "unity_behaviour.cs"),
            "HeroController.TakeDamage",
            "--signature",
            "--full",
        ]
    )
    captured = capsys.readouterr()
    assert rc == 0
    assert "# note:" in captured.out
    assert "not allowed" in captured.out.lower()


def test_show_signature_view_python_keeps_docstring_after_sig(python_dir, capsys):
    """Python docstrings live INSIDE the body in source, but `outline` and
    signature-view both render them AFTER the signature with +1 indent —
    same `docs_inside` placement as the outline render. Verifies signature
    view tracks outline's doc placement, not C#'s."""
    rc = main(
        [
            "show",
            str(python_dir / "domain_model.py"),
            "UserService.get",
            "--signature",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    # Signature comes first
    sig_idx = out.find("def get")
    doc_idx = out.find("Look up a user by id")
    assert sig_idx >= 0 and doc_idx >= 0
    assert sig_idx < doc_idx
    # No method body content
    assert "return self" not in out
    assert "raise " not in out


def test_show_signature_view_strips_docs_with_no_doc(csharp_dir, capsys):
    """`--no-doc` composes with `--signature`: the XML doc lines disappear,
    only attrs+signature remain. Useful when the agent already has the doc
    elsewhere and just wants the bare contract line."""
    rc = main(
        [
            "show",
            str(csharp_dir / "unity_behaviour.cs"),
            "HeroController.TakeDamage",
            "--signature",
            "--no-doc",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "/// <summary>" not in out
    assert "public void TakeDamage(int amount)" in out


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


# --- All-files-fail visibility -------------------------------------------
#
# Regression: if every file in a batch raised during `adapter.parse`,
# stdout used to be empty (warnings went only to stderr) and an LLM
# harness reading stdout saw `(no output)`. The CLI promises
# rc=0 + a `# note:` line on stdout for any user-facing failure, so an
# all-failure batch must surface the parse errors there too.


class _BoomAdapter:
    """Adapter stub that claims `.yml` and always raises on parse."""
    language_name = "yaml"
    extensions = {".yml", ".yaml"}

    def parse(self, path):
        raise RuntimeError(f"boom on {path}")


def test_outline_all_files_fail_emits_notes_on_stdout(tmp_path, monkeypatch, capsys):
    a = tmp_path / "a.yml"
    b = tmp_path / "b.yml"
    a.write_text("k: 1\n")
    b.write_text("k: 2\n")
    monkeypatch.setattr("ast_outline.adapters.ADAPTERS", [_BoomAdapter()])

    rc = main(["outline", str(a), str(b)])
    captured = capsys.readouterr()
    assert rc == 0
    # Both files surface as `# note:` lines on stdout — the channel the
    # LLM agent reads. No silent empty stdout.
    assert captured.out.count("# note: parse error in") == 2
    assert str(a) in captured.out
    assert str(b) in captured.out


def test_digest_all_files_fail_emits_notes_on_stdout(tmp_path, monkeypatch, capsys):
    a = tmp_path / "a.yml"
    b = tmp_path / "b.yml"
    a.write_text("k: 1\n")
    b.write_text("k: 2\n")
    monkeypatch.setattr("ast_outline.adapters.ADAPTERS", [_BoomAdapter()])

    rc = main(["digest", str(a), str(b)])
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out.count("# note: parse error in") == 2
    # Should NOT print the misleading `# no files` line from
    # `render_digest([])` when files were present but all failed.
    assert "# no files" not in captured.out


