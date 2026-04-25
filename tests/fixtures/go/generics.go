// Package gen covers Go 1.18+ generics — both on types and functions.
package gen

import "cmp"

// Coordinate is a generic struct with a single type parameter.
type Coordinate[T any] struct {
	X T
	Y T
}

// Translate returns a translated coordinate.
func (c Coordinate[T]) Translate(dx, dy T) Coordinate[T] {
	return Coordinate[T]{X: c.X, Y: c.Y}
}

// Pair holds two values of distinct types.
type Pair[K comparable, V any] struct {
	Key   K
	Value V
}

// Min returns the smaller of two ordered values.
func Min[T cmp.Ordered](a, b T) T {
	if a < b {
		return a
	}
	return b
}

// Map transforms a slice using a per-element function.
func Map[A, B any](xs []A, f func(A) B) []B {
	out := make([]B, len(xs))
	for i, x := range xs {
		out[i] = f(x)
	}
	return out
}

// Container is a generic interface.
type Container[T any] interface {
	Add(item T)
	Get(index int) T
	Len() int
}
