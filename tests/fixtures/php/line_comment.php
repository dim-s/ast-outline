<?php

namespace App\Comments;

class CommentedClass
{
    // Line comment — not a docblock; must NOT be captured.
    public function foo(): void {}

    /* Plain block comment — also not a docblock. */
    public function bar(): void {}

    # Hash-style line comment, common in older PHP code.
    public function baz(): void {}

    /** Real PHPDoc — this one MUST be captured. */
    public function quux(): void {}
}
