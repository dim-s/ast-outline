// Package base provides the shared Animal type.
package base

// Animal is the root of the cross-directory hierarchy.
type Animal struct {
	Name string
}

// Sound is the default vocalisation.
func (a *Animal) Sound() string {
	return "..."
}
