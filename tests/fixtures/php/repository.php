<?php

namespace App\Contracts;

interface Repository
{
    public const int DEFAULT_LIMIT = 50;

    public function find(int $id): ?object;

    public function save(object $entity): void;

    public function delete(int $id): bool;
}

interface PagedRepository extends Repository, \Countable
{
    public function page(int $offset, int $limit): array;
}
