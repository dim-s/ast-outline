// Multiple, virtual, and protected inheritance — classic diamond
// hierarchy. The adapter should record every base with its access
// specifier and `virtual` marker preserved.
#pragma once

namespace inh {

class Animal {
public:
    virtual ~Animal() = default;
    virtual void speak() const = 0;
};

class Swimmer {
public:
    virtual void swim() = 0;
};

class Flier {
public:
    virtual void fly() = 0;
};

// Diamond — both Mammal and Bird virtually inherit from Animal so
// Duck only has one Animal sub-object.
class Mammal : public virtual Animal {
public:
    void breathe();
};

class Bird : public virtual Animal {
public:
    void layEgg();
};

class Duck : public Mammal, public Bird, public Swimmer, public Flier {
public:
    void speak() const override;
    void swim() override;
    void fly() override;
};

// `final` class — sealed, no further derivation
class FinalAnimal final : public Animal {
public:
    void speak() const final;
};

// Private inheritance + using-declaration to expose a base member
class Wrapper : private Animal {
public:
    using Animal::speak;
};

}  // namespace inh
