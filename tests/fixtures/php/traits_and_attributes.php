<?php

namespace App\Mixins;

use Attribute;

#[Attribute(Attribute::TARGET_CLASS | Attribute::TARGET_METHOD)]
final class Route
{
    public function __construct(
        public readonly string $path,
        public readonly array $methods = ["GET"],
    ) {}
}

trait HasTimestamps
{
    public ?\DateTimeImmutable $createdAt = null;
    public ?\DateTimeImmutable $updatedAt = null;

    public function touch(): void
    {
        $this->updatedAt = new \DateTimeImmutable();
    }
}

trait Loggable
{
    abstract protected function logger(): object;

    public function log(string $msg): void {}
}

#[Route("/users", methods: ["GET", "POST"])]
class UserController
{
    use HasTimestamps;
    use Loggable;

    #[Route("/users/{id}")]
    public function show(int $id): string
    {
        return "user $id";
    }

    /**
     * @deprecated Use show() instead.
     */
    #[Route("/users/{id}/legacy")]
    public function legacyShow(int $id): string
    {
        return $this->show($id);
    }

    protected function logger(): object
    {
        return new \stdClass();
    }
}
