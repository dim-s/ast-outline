package mammals

// Puppy embeds Dog — second-level transitive `implements Animal`.
type Puppy struct {
	Dog
}
