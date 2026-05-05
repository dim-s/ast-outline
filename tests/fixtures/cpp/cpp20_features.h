// C++20 features — concepts, requires-clauses, spaceship operator,
// `consteval` / `constinit`, `[[likely]]` attributes, designated
// initializers (in field defaults). Most of these the adapter doesn't
// surface specially — the test is that they parse without errors and
// the surrounding declarations still come through.
#pragma once

#include <concepts>
#include <compare>

namespace cpp20 {

// Concept declaration
template<typename T>
concept Numeric = std::is_arithmetic_v<T>;

// Concept with multi-clause body
template<typename T>
concept Sortable = requires(T a, T b) {
    { a < b } -> std::convertible_to<bool>;
    { a == b } -> std::convertible_to<bool>;
};

// Function constrained by concept (short form)
template<Numeric T>
T abs_val(T x) {
    return x < 0 ? -x : x;
}

// Function constrained by concept (long form with `requires`)
template<typename T>
    requires Sortable<T>
T const& min_of(T const& a, T const& b) {
    return a < b ? a : b;
}

// Class with three-way comparison ("spaceship") operator
struct Version {
    int major;
    int minor;
    int patch;

    auto operator<=>(const Version&) const = default;
    bool operator==(const Version&) const = default;
};

// `consteval` immediate function
consteval int square(int x) {
    return x * x;
}

// `constinit` global
constinit int kCounter = 0;

// `if constexpr` body — adapter must not get confused
template<typename T>
void process(T value) {
    if constexpr (Numeric<T>) {
        // do something numeric
    } else {
        // do something else
    }
}

}  // namespace cpp20
