// Operator overloads, defaulted/deleted special members, conversion
// operators. Exercises the OPERATOR / CTOR / DTOR classification paths.
#pragma once

class Money {
public:
    Money();
    Money(int cents);
    Money(const Money&) = default;
    Money(Money&&) noexcept = default;
    ~Money() = default;

    Money& operator=(const Money&) = delete;
    Money operator+(const Money& other) const;
    bool operator==(const Money& other) const;
    explicit operator bool() const;
    explicit operator double() const;

private:
    int cents_;
};
