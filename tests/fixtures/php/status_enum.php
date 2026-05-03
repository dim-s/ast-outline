<?php

namespace App\Models;

/**
 * Lifecycle status of a user account (PHP 8.1+ backed enum).
 */
enum Status: string implements HasName
{
    case Active = "active";
    case Pending = "pending";
    case Banned = "banned";

    public const string DEFAULT_VALUE = "active";

    public function label(): string
    {
        return match ($this) {
            Status::Active => "Active",
            Status::Pending => "Pending",
            Status::Banned => "Banned",
        };
    }

    public static function default(): self
    {
        return self::Active;
    }
}

enum Priority
{
    case Low;
    case High;
}
