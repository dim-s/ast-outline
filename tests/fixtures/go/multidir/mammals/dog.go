// Package mammals lives in a different directory than `base`.
package mammals

import "ast_outline_test/base"

// Dog embeds base.Animal — cross-package embedding.
// `implements` matches by suffix-stripped name, so this is treated as
// `Dog : Animal` in the BFS.
type Dog struct {
	base.Animal
	Breed string
}

// Bark is Dog-specific.
func (d *Dog) Bark() string {
	return "Woof"
}
