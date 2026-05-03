<?php
// Legacy global-namespace file (still common in PHP 7.4 codebases).

require_once __DIR__ . "/bootstrap.php";

class GlobalThing
{
    public string $name = "global";

    public function hello(): string
    {
        return "hi from $this->name";
    }
}

function global_helper(int $x, int $y = 0): int
{
    return $x + $y;
}

const MAX_RETRIES = 3;
