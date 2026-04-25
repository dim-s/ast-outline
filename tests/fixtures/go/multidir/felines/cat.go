package felines

import "ast_outline_test/base"

// Cat embeds base.Animal — direct subclass, different directory.
type Cat struct {
	base.Animal
}

// Meow is Cat-specific.
func (c *Cat) Meow() string { return "Meow" }
