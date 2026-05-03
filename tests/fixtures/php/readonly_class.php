<?php

namespace App\Value;

/**
 * Immutable 2D vector (PHP 8.2+ readonly class).
 */
readonly class Vec2
{
    public function __construct(
        public float $x,
        public float $y,
    ) {}

    public function add(Vec2 $other): self
    {
        return new self($this->x + $other->x, $this->y + $other->y);
    }

    public function length(): float
    {
        return sqrt($this->x ** 2 + $this->y ** 2);
    }
}

abstract readonly class Money
{
    public function __construct(public int $cents) {}

    abstract public function currency(): string;
}

final readonly class Usd extends Money
{
    public function currency(): string
    {
        return "USD";
    }
}
