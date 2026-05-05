// Assorted C++ edge cases the adapter should survive without crashing
// or losing the surrounding declarations:
// - friend class / friend function declarations
// - forward declarations
// - typedef + using aliases (file scope and inside types)
// - bitfields
// - lambdas (must NOT be exposed as top-level functions)
// - trailing return types (`auto f() -> int`)
// - nested types
// - `extern "C"` blocks (treated like a transparent scope)
// - default member initialisers (different bracket forms)
// - inline static variables
#pragma once

namespace edges {

// Forward declarations — declared but not defined here
class ForwardClass;
struct ForwardStruct;
enum class ForwardEnum;

// Type aliases at file scope
typedef unsigned int uint32;
using Callback = void (*)(int);

class Container {
public:
    Container();

    // Friend relationships — should NOT show up as members of Container
    friend class Helper;
    friend void global_friend_fn(Container&);

    // Nested type
    class Iterator {
    public:
        bool hasNext() const;
        int next();
    };

    struct Pair {
        int first;
        int second;
    };

    // Bitfield members
    unsigned int flag_a : 1;
    unsigned int flag_b : 3;

    // Default member initialisers (= and braced)
    int counter = 0;
    int width{640};

    // Trailing return type
    auto compute(int input) const -> double;

    // Static + inline static
    static int static_count;
    inline static int inline_static = 5;

    // Type alias inside the class
    using value_type = int;

private:
    int data_;
};

// Lambda inside a free function — must not surface as a top-level decl
inline auto make_adder(int n) {
    return [n](int x) { return x + n; };
}

// `extern "C"` block — its body holds C-linkage functions, treated
// like a transparent scope (the functions inside should still surface).
extern "C" {
    void c_function(int x);
    int c_other_function(double y);
}

}  // namespace edges
