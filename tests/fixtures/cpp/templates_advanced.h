// Advanced template shapes — variadic templates, full and partial
// specialisation, template template parameters, member templates,
// default template arguments, non-type parameters.
#pragma once

#include <type_traits>

namespace tmpl {

// Default template args
template<typename T = int, std::size_t N = 16>
class Buffer {
    T data_[N];
public:
    constexpr std::size_t size() const noexcept { return N; }
};

// Variadic template (parameter pack)
template<typename... Args>
class Tuple {
public:
    static constexpr std::size_t arity = sizeof...(Args);
    void unpack();
};

// Variadic function template + perfect forwarding
template<typename T, typename... Args>
T construct(Args&&... args) {
    return T(static_cast<Args&&>(args)...);
}

// Template template parameter — `Container` itself takes a `typename`
template<template<typename> class Container, typename T>
class Wrapper {
    Container<T> inner_;
public:
    void push(const T& v);
};

// Primary template
template<typename T>
class TypeTraits {
public:
    static constexpr bool is_pointer = false;
};

// Full specialisation
template<>
class TypeTraits<int> {
public:
    static constexpr bool is_pointer = false;
    static constexpr bool is_int = true;
};

// Partial specialisation
template<typename T>
class TypeTraits<T*> {
public:
    static constexpr bool is_pointer = true;
};

// Class with member templates (templated method on a non-templated class)
class Visitor {
public:
    template<typename T>
    void visit(const T& value);

    template<typename T, typename U>
    auto combine(T t, U u) -> decltype(t + u);
};

// Non-type template parameters of various kinds
template<int N, char C, bool B>
struct Tag {
    static constexpr int n = N;
    static constexpr char c = C;
    static constexpr bool b = B;
};

}  // namespace tmpl
