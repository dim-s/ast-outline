// Deliberately malformed — exercises the parse-error counter.
// Earlier declarations stay intact so the adapter still emits them.
package broken

type Good struct {
	X int
}

func (g *Good) Method() int { return g.X }

// Missing closing brace below trips tree-sitter:
func Oops(
