// Generic UI widget hierarchy fixture. Exercises the bread-and-butter
// shapes the C++ adapter has to handle: namespaces, classes with
// access specifiers, virtual / pure-virtual, ctors / dtors, templated
// members, fields with initialisers, free functions inside a namespace.
#pragma once

#include <vector>
#include <string>
#include "base.h"

namespace ui::widgets {

class Widget : public Base, protected Themed {
public:
    Widget();
    Widget(int width, int height);
    virtual ~Widget();

    virtual void draw() const = 0;
    int width() const noexcept;
    int height() const noexcept { return h_; }

    template<typename T>
    T cast() const;

protected:
    int x_ = 0;
    int y_ = 0;

private:
    static constexpr int kMax = 100;
    int w_;
    int h_;
    std::vector<int> data_;
};

struct Point {
    int x;
    int y;
};

enum class Color : int { Red, Green, Blue };
enum Mode { Idle, Running, Stopped };

template<typename T, int N>
class FixedArray {
    T data_[N];
public:
    T& at(int i);
    constexpr int size() const noexcept { return N; }
};

void freeFunc(int x);
inline int add(int a, int b) { return a + b; }

}  // namespace ui::widgets

namespace {
    void anonHelper() {}
}

inline namespace v1 {
    class Versioned {};
}
