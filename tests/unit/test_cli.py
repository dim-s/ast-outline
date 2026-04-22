"""End-to-end CLI integration tests.

These invoke `code_outline.cli.main` directly and capture stdout/stderr,
so we don't need to spawn a subprocess.
"""
from __future__ import annotations

from code_outline.cli import main


# --- Default / guide -----------------------------------------------------


def test_main_with_no_args_prints_guide(capsys):
    rc = main([])
    out = capsys.readouterr().out
    assert rc == 0
    assert "code-outline" in out
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
    """`code-outline path.cs` with no subcommand should default to `outline`."""
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


def test_outline_missing_file_exits_nonzero(tmp_path, capsys):
    rc = main(["outline", str(tmp_path / "nope.cs")])
    err = capsys.readouterr().err
    assert rc != 0
    assert "no files found" in err.lower() or "no input" in err.lower()


# --- show ----------------------------------------------------------------


def test_show_single_symbol(csharp_dir, capsys):
    rc = main(["show", str(csharp_dir / "unity_behaviour.cs"), "HeroController.TakeDamage"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "public void TakeDamage" in out
    assert "OnHealthChanged" in out  # part of the method body


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


def test_show_not_found_exits_1(csharp_dir, capsys):
    rc = main(["show", str(csharp_dir / "unity_behaviour.cs"), "NoSuchThing"])
    err = capsys.readouterr().err
    assert rc == 1
    assert "not found" in err.lower()


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


def test_digest_missing_path_exits_nonzero(tmp_path, capsys):
    rc = main(["digest", str(tmp_path / "nope")])
    err = capsys.readouterr().err
    assert rc != 0
    assert "not found" in err.lower()


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


def test_implements_no_matches_exits_1(fixtures_dir, capsys):
    rc = main(["implements", "TotallyUnrelatedType", str(fixtures_dir)])
    captured = capsys.readouterr()
    assert rc == 1
    assert "no direct" in captured.err.lower()
