// Type-only module: type aliases, enums, interface inheritance, generics.
export type UserId = string;

export type Result<T> = { ok: true; value: T } | { ok: false; error: string };

export enum Status {
    Idle,
    Loading,
    Ready,
    Error,
}

export enum Priority {
    Low = "low",
    Medium = "medium",
    High = "high",
}

export interface Entity {
    id: UserId;
    createdAt: Date;
}

export interface User extends Entity {
    name: string;
    email: string;
    readonly role: "admin" | "user";
}

export interface Repository<T extends Entity> {
    get(id: UserId): Promise<T | null>;
    list(): Promise<readonly T[]>;
    save(entity: T): Promise<void>;
}
