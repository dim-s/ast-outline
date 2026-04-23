package demo;

// Deliberately broken — used to verify parse-error counting and the
// header warning. Missing close brace on `broken(`, missing expression
// before `;`, unclosed class body. tree-sitter should still produce a
// partial tree with ERROR / MISSING nodes.
public class Broken {
    public int ok() { return 1; }

    public void broken( {
        int x = ;
    }

    public int stillVisible() { return 2; }

