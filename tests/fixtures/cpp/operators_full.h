// Comprehensive operator-overload coverage. Each op should classify
// as KIND_OPERATOR with a name that matches the source-true operator
// token (so `operator+` stays `operator+`, `operator<=>` stays
// `operator<=>`, etc.).
#pragma once

#include <cstddef>

namespace ops {

class Vec {
public:
    // Arithmetic
    Vec operator+(const Vec&) const;
    Vec operator-(const Vec&) const;
    Vec operator*(double) const;
    Vec& operator+=(const Vec&);
    Vec& operator-=(const Vec&);

    // Comparison + spaceship (C++20)
    bool operator==(const Vec&) const;
    auto operator<=>(const Vec&) const = default;

    // Subscript / call / arrow
    double& operator[](std::size_t i);
    double operator()(int row, int col) const;

    // Unary
    Vec operator-() const;
    Vec& operator++();    // pre-increment
    Vec operator++(int);  // post-increment

    // Allocation
    static void* operator new(std::size_t);
    static void operator delete(void*);
    static void* operator new[](std::size_t);
    static void operator delete[](void*);

    // Conversion
    explicit operator bool() const;
    operator double() const;
};

// User-defined literal — `123_kg` shape
constexpr long double operator""_kg(long double value) {
    return value * 1.0;
}

// Stream operator — free function
class Stream;
Stream& operator<<(Stream& s, const Vec& v);

}  // namespace ops
