// Multi-level inheritance fixture for `implements` transitive tests.
// Uses TypeScript classes (abstract + concrete), interface chain,
// and multiple inheritance via `extends class implements interface`.

export abstract class Animal {
    abstract eat(): void;
}

export class Dog extends Animal {
    eat() {}
}

export class Cat extends Animal {
    eat() {}
}

// Transitive through Dog.
export class Puppy extends Dog {
    play() {}
}

// Deep: Animal ← Dog ← Puppy ← Pomeranian.
export class Pomeranian extends Puppy {
    yap() {}
}

// Interface chain.
export interface IService {
    run(): void;
}

export interface IReadService extends IService {
    read(): unknown;
}

// Transitive: UserService implements IReadService which extends IService.
export class UserService implements IReadService {
    run() {}
    read() { return null; }
}
