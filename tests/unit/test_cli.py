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
    rc = main(["outline", str(tmp_path / "nope.cs")])
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.err == ""
    assert "# note:" in captured.out
    assert "no files found" in captured.out.lower() or "no input" in captured.out.lower()


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
    assert "+TakeDamage" in out


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
    assert "+Die" in out


# --- implements ----------------------------------------------------------


def test_implements_finds_match(fixtures_dir, capsys):
    rc = main(["implements", "IDamageable", str(fixtures_dir / "csharp")])
    out = capsys.readouterr().out
    assert rc == 0
    assert "HeroController" in out
    assert "IDamageable" in out


def test_implements_generic_interface(fixtures_dir, capsys):
    rc = main(["implements", "IRepository", str(fixtures_dir / "csharp")])
    out = capsys.readouterr().out
    assert rc == 0
    assert "UserRepository" in out


def test_implements_python(fixtures_dir, capsys):
    rc = main(["implements", "BaseEntity", str(fixtures_dir / "python")])
    out = capsys.readouterr().out
    assert rc == 0
    assert "User" in out


def test_implements_no_matches_returns_zero_with_note(fixtures_dir, capsys):
    """LLM-friendly mode: empty match set yields rc=0 + note on stdout."""
    rc = main(["implements", "TotallyUnrelatedType", str(fixtures_dir)])
    captured = capsys.readouterr()
    assert rc == 0
    # Transitive is default, so the "not found" message drops the word "direct"
    assert "no implementations" in captured.out.lower()


def test_implements_default_header_mentions_transitive(java_dir, capsys):
    """Default (transitive) mode header should say `(incl. transitive)`."""
    rc = main(["implements", "Animal", str(java_dir / "hierarchy.java")])
    out = capsys.readouterr().out
    assert rc == 0
    # Header on the first line
    first = out.splitlines()[0]
    assert "match(es) for 'Animal'" in first
    assert "incl. transitive" in first


def test_implements_default_finds_transitive_matches(java_dir, capsys):
    """Grandchildren should appear in the default output with a [via ...] tag."""
    rc = main(["implements", "Animal", str(java_dir / "hierarchy.java")])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Pomeranian" in out
    assert "Puppy" in out
    # [via Dog] for level-1 transitive, [via Dog → Puppy] for level-2
    assert "[via Dog]" in out
    assert "[via Dog → Puppy]" in out


def test_implements_direct_flag_suppresses_transitive(java_dir, capsys):
    """--direct mode: header says `direct match(es)`, grandchildren absent."""
    rc = main(["implements", "--direct", "Animal", str(java_dir / "hierarchy.java")])
    out = capsys.readouterr().out
    assert rc == 0
    first = out.splitlines()[0]
    assert "direct match(es)" in first
    assert "incl. transitive" not in first
    assert "Dog" in out
    assert "Cat" in out
    # Grandchild should NOT appear
    assert "Pomeranian" not in out
    assert "[via " not in out


def test_implements_short_d_alias_works(java_dir, capsys):
    """`-d` is the short alias for `--direct`."""
    rc = main(["implements", "-d", "Animal", str(java_dir / "hierarchy.java")])
    out = capsys.readouterr().out
    assert rc == 0
    assert "direct match(es)" in out.splitlines()[0]


def test_implements_no_direct_matches_message(csharp_dir, capsys):
    """With --direct and no hits, the note uses the word 'direct'."""
    rc = main(["implements", "--direct", "NoSuchBase", str(csharp_dir)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "no direct" in captured.out.lower()


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


def test_implements_crosses_directories(java_dir, capsys):
    """The multidir/ fixture spreads base + subclasses across 3 directories.
    Running implements from the parent dir should stitch the chain back together."""
    rc = main(["implements", "Animal", str(java_dir / "multidir")])
    out = capsys.readouterr().out
    assert rc == 0
    # Should find Dog (mammals/), Cat (felines/), Puppy (mammals/, transitive)
    assert "mammals/Dog.java" in out
    assert "felines/Cat.java" in out
    assert "mammals/Puppy.java" in out
    # Puppy is transitive via Dog → annotation present
    puppy_line = next(ln for ln in out.splitlines() if "Puppy" in ln)
    assert "[via Dog]" in puppy_line
