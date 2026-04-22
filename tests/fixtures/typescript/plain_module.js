// Plain JavaScript module — no types. Parsed by the TS grammar (TS is a
// superset of JS). Exercises: top-level const, arrow export, plain function
// declaration, class without types.
const VERSION = "1.0.0";

export function greet(name) {
    return "Hello, " + name;
}

export const add = (a, b) => a + b;

export class Counter {
    constructor(start = 0) {
        this.value = start;
    }

    increment() {
        this.value += 1;
        return this.value;
    }

    reset() {
        this.value = 0;
    }
}
