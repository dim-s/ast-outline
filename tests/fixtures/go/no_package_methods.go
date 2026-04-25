// Package orphan exercises the "method without local receiver" path:
// the receiver type is declared in another file (or another package),
// so the adapter must keep the method visible at the namespace level
// rather than dropping it.
package orphan

// LocalThing is declared here.
type LocalThing struct {
	X int
}

// LocalMethod is on LocalThing — should be grouped under it.
func (l *LocalThing) LocalMethod() int {
	return l.X
}

// ForeignReceiver is a method on a type declared elsewhere
// (e.g. in another file of the same package). The adapter must
// surface it at the top level since it can't find the receiver here.
func (e *ExternalType) ForeignReceiver() string {
	return "from external"
}
