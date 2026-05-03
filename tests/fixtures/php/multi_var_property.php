<?php

namespace App\Multi;

class Bag
{
    public string $a, $b = "x", $c;

    private static int $count = 0;

    public function __construct()
    {
        $this->a = "init";
    }
}
