package com.example.demo.hierarchy;

// Multi-level inheritance fixture used by the `implements` transitive
// tests. Three levels (Base → Middle → Leaf), a diamond (both Middle
// variants as bases of Diamond), and a silly self-cycle that tree-sitter
// still parses — the search must not loop forever.

public abstract class Animal {
    public abstract void eat();
}

// Direct subclass of Animal.
public class Dog extends Animal {
    @Override
    public void eat() {}
}

// Direct subclass of Animal — branches away from Dog.
public class Cat extends Animal {
    @Override
    public void eat() {}
}

// Grandchild — transitive subclass of Animal via Dog.
public class Puppy extends Dog {
    public void play() {}
}

// Great-grandchild — transitive via Dog → Puppy.
public class Pomeranian extends Puppy {
    public void yap() {}
}

// Diamond: Mixed has both Dog and Cat as bases — Java single-inheritance
// forbids this for classes, but we approximate with an interface + class.
public interface Mixable {}

public class Mixed extends Dog implements Mixable {}

// Self-referencing cycle (nonsense but syntactically valid). The cycle
// walker must not loop on this.
public class Loopy extends Loopy {}
