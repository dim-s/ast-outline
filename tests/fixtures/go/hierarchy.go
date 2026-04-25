// Package zoo exercises Go's struct embedding as the inheritance idiom
// — used by the cross-language `implements` tests.
package zoo

// Animal is the root.
type Animal struct {
	Name string
}

// Dog embeds Animal — counted as `Dog : Animal` for `implements`.
type Dog struct {
	Animal
	Breed string
}

// Puppy embeds Dog — two-level transitive: Puppy → Dog → Animal.
type Puppy struct {
	Dog
}

// Pomeranian embeds Puppy — three-level transitive.
type Pomeranian struct {
	Puppy
}

// Cat is a sibling subclass of Animal.
type Cat struct {
	Animal
	Indoor bool
}

// Movable is an interface; Walker embeds it.
type Movable interface {
	Move(distance int) bool
}

// Walker embeds Movable + adds Walk().
type Walker interface {
	Movable
	Walk()
}

// Skater embeds Animal AND implements Movable explicitly.
type Skater struct {
	Animal
}

// Move is a method on Skater.
func (s *Skater) Move(distance int) bool { return distance > 0 }
