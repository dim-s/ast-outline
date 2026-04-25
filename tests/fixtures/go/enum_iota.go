// Package palette demonstrates Go's enum-by-iota idiom.
package palette

// Color is a defined int type used as the value-set basis.
type Color int

// Color constants — the classic iota-driven block.
const (
	Red    Color = iota // 0
	Green               // 1
	Blue                // 2
	Yellow              // 3
)

// Direction is another iota-based enum, shifted to avoid zero-value bug.
type Direction int

const (
	North Direction = iota + 1
	East
	South
	West
)

// Name returns the human-readable name of a Color.
func (c Color) Name() string {
	switch c {
	case Red:
		return "red"
	case Green:
		return "green"
	case Blue:
		return "blue"
	default:
		return "?"
	}
}
