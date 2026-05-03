<?php

namespace App\Broken;

class Salvageable
{
    public function ok(): string
    {
        return "fine";
    }

    // intentional syntax error below — adapter must surface partial outline
    public function broken(int $x int $y): void
    {
    }

    public function alsoOk(): int
    {
        return 1;
    }
}
