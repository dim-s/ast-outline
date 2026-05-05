// Implementation file with out-of-class member definitions.
// The qualified declarator (`Widget::draw`, `Widget::Widget`,
// `Widget::~Widget`) is the canonical pattern for splitting a class
// across header + impl in C++. The adapter surfaces these as free
// functions whose name is the qualified form, classified by the
// trailing identifier shape.
#include "widget.h"

namespace ui::widgets {

Widget::Widget() : x_(0), y_(0), w_(0), h_(0) {}

Widget::Widget(int width, int height)
    : w_(width), h_(height) {}

Widget::~Widget() {}

int Widget::width() const noexcept {
    return w_;
}

void freeFunc(int x) {
    (void)x;
}

}  // namespace ui::widgets
