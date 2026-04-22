// Fixture for TS visibility rules:
//   - class members without modifier → public (unlike C#)
//   - private/protected modifiers captured verbatim
//   - `#name` true-private names also treated as private
//   - leading-underscore identifiers are a convention; we mark them private too
export class Visibility {
    publicByDefault(): void {}
    public explicitPublic(): void {}
    private explicitPrivate(): void {}
    protected explicitProtected(): void {}

    #truePrivate(): void {}

    _conventionallyPrivate(): void {}
}

export function _underscorePrefixedFunc(): void {}
export function publicFunc(): void {}
