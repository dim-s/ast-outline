// Regression fixture for namespace-collapse: when a namespace level
// holds an inner namespace AND any sibling declaration (typedef,
// using, class, function, etc.), the chain must NOT collapse, or
// those siblings would silently disappear from the outline.
#pragma once

namespace outer {
    using LegacyAlias = int;

    typedef double scalar_t;

    namespace inner {
        class Tucked {};
    }
}

namespace mixed {
    void hello();

    namespace deep {
        class Buried {};
    }
}
