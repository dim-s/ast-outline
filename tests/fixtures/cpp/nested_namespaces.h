// Namespace-collapse fixture. The adapter should fold single-child
// `namespace a { namespace b { ... } }` chains into one
// `namespace a::b` declaration so the outline reads the same regardless
// of whether the source uses old-style or C++17 nested-namespace syntax.
// Multiple siblings at one level break the chain — those levels stay
// nested in the IR.
#pragma once

namespace solo {
    namespace deep {
        namespace nested {
            class OnlyClass {};
        }
    }
}

namespace c17::nested {
    class Same {};
}

namespace splits {
    namespace one {
        class A {};
    }
    namespace two {
        class B {};
    }
}
