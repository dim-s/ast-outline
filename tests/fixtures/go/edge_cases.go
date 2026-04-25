// Package edges collects Go-specific syntactic edge cases that the
// adapter must handle correctly even when they're rare or unusual:
//
//   - multi-name struct fields and var/const specs
//   - parenthesised type blocks (`type ( A struct{}; B int )`)
//   - empty struct / interface
//   - function types as named types and as aliases
//   - variadic, multi-return, and named-return signatures
//   - channel and map field types
//   - blank-identifier interface-satisfaction declarations
//   - embedded pointer + generic types
//   - generic methods on generic receivers (the regrouping case)
//   - special-named functions (init, main)
package edges

// Multi-name field — adapter picks the FIRST identifier and keeps the
// full slice as the rendered signature.
type Vec3 struct {
	X, Y, Z float64
}

// Multi-name var/const at module level.
var (
	A, B, C int = 1, 2, 3
)

const D, E = 10, 20

// Type block with mixed shapes.
type (
	BlockStruct    struct{ x int }
	BlockInterface interface{ M() }
	BlockNewtype   int
)

// Empty composites — must NOT crash and should still be classified.
type Marker struct{}
type Anything interface{}

// Function-typed declarations.
type HandlerFunc func(int) error
type CallbackAlias = func(string)

// Stack is a generic struct; receiver-grouping must work for `*Stack[T]`.
type Stack[T any] struct {
	items []T
}

// Push and Pop must surface as children of Stack, not as siblings.
func (s *Stack[T]) Push(item T) {
	s.items = append(s.items, item)
}

func (s *Stack[T]) Pop() T {
	var zero T
	return zero
}

// Variadic + named multi-return.
func Sum(nums ...int) (total int, err error) {
	for _, n := range nums {
		total += n
	}
	return total, nil
}

// Channel + map fields.
type Server struct {
	Done    chan struct{}
	Receive <-chan int
	Send    chan<- string
	Cache   map[string]any
	Outputs []func(string) error
}

// Blank-identifier interface-satisfaction check — common Go idiom.
type Closer interface{ Close() error }

type MyConn struct{}

func (c *MyConn) Close() error { return nil }

var _ Closer = (*MyConn)(nil)

// Embedded pointer type — `*Base` registers Base as a base of Owner.
type Base struct {
	Name string
}

type Owner struct {
	*Base
	Extra int
}

// Embedded generic type — `Container[Color]` registers Container.
type Container[T any] struct{}
type ColorBox struct {
	Container[int]
	Label string
}

// Special-named functions: init runs at import time, main is entrypoint
// (despite this not being a real `package main`, the parser is fine).
func init() {}

func helper() {} // unexported helper — visibility = private
