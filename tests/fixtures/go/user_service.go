// Package service hosts the canonical smoke fixture for the Go adapter.
//
// It exercises: package declaration, multi-line doc comments, struct +
// methods (grouped under their receiver), exported vs unexported names
// (Go's case-based visibility), embedded types as bases, generics with
// constraints, interfaces with methods + embedded interfaces, type
// aliases and defined types, const/var blocks.
package service

import (
	"errors"
	"io"
)

// MaxUsers is the upper bound on registered users.
const MaxUsers = 100

// MaxItems is typed.
const MaxItems int = 50

var (
	// GlobalCounter is exported.
	GlobalCounter int = 0
	// privateCount is unexported (lowercase first letter → private).
	privateCount int = 0
)

// BaseService is a top-level service primitive other services embed.
type BaseService struct {
	Name string
	// closed is the package-private "is open?" flag.
	closed bool
}

// Open marks the service as ready.
func (b *BaseService) Open() {
	b.closed = false
}

// close is unexported.
func (b *BaseService) close() error {
	b.closed = true
	return nil
}

// UserService is the primary user-facing service.
//
// Embeds BaseService — Go's idiom for "extends BaseService" — and
// implements the io.Closer interface contract via Close().
type UserService struct {
	BaseService            // embedded, contributes its methods
	Repo        Repository // explicit field, named
	cache       map[string]any
}

// Save persists a user; returns an error on failure.
func (u *UserService) Save(user string) error {
	if user == "" {
		return errors.New("empty user")
	}
	return nil
}

// findMax is a private generic method.
func (u *UserService) findMax(xs []int) int {
	max := xs[0]
	for _, x := range xs {
		if x > max {
			max = x
		}
	}
	return max
}

// Close satisfies io.Closer.
func (u *UserService) Close() error {
	return u.close()
}

// Repository is the contract user-stores must satisfy.
type Repository interface {
	// Get fetches a user by id.
	Get(id string) (string, error)
	// List returns all users.
	List() []string
	// Has checks existence.
	Has(id string) bool
}

// AdminRepository embeds Repository and adds admin-only ops.
type AdminRepository interface {
	Repository
	// Delete removes a user.
	Delete(id string) error
}

// errMissing is an unexported sentinel.
var errMissing = errors.New("missing")

// Reader is an alias for io.Reader so the package surface stays compact.
type Reader = io.Reader

// UserID is a defined type (newtype) — distinct from int64 at compile time.
type UserID int64
