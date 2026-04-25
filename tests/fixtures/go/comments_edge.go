package edge

// SingleLineDoc is a one-line doc comment.
func SingleLineDoc() {}

// MultiLine doc spans
// across multiple lines
// and stops at the function.
func MultiLine() {}

func NoDoc() {}

// This comment has a blank line gap
// and SHOULD NOT be treated as Spaced's doc.

func Spaced() {}

/* BlockDoc uses the alternate Go block-comment form. */
func BlockDoc() {}
