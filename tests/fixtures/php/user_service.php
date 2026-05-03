<?php
declare(strict_types=1);

namespace App\Service;

use App\Contracts\Repository;
use App\Models\User;
use App\Models\Order as OrderModel;
use function strlen;
use const PHP_INT_MAX;

/**
 * Coordinates user-related use cases.
 *
 * Glue layer between controllers and the persistence adapter.
 */
final class UserService
{
    public const string DEFAULT_ROLE = "guest";

    private array $cache = [];

    public function __construct(
        private readonly Repository $repository,
        protected int $maxCacheSize = 100,
    ) {}

    /**
     * Fetch a user by id, caching the result.
     */
    public function getUser(int $id): ?User
    {
        return $this->repository->find($id);
    }

    /** @deprecated Use getUser instead. */
    public function loadUser(int $id): ?User
    {
        return $this->getUser($id);
    }

    public function makeOrder(User $user): OrderModel
    {
        return new OrderModel($user);
    }

    private function flush(): void {}
}

abstract class BaseService
{
    abstract public function name(): string;

    final public function tag(): string
    {
        return static::class;
    }
}

function make_service(Repository $r): UserService
{
    return new UserService($r);
}

const APP_VERSION = "1.0.0";
