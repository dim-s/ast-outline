// Deliberately broken TypeScript — used to verify parse-error counting.
// tree-sitter-typescript surfaces ERROR / MISSING nodes for unmatched
// brackets, bad type annotations, and incomplete expressions.

export function ok(): number {
    return 1;
}

export function broken(x: number {
    return x + ;
}

export class Partial
    private field: = ;

    method() {
