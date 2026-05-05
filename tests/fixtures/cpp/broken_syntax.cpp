// Mixed valid + invalid C++ — the adapter should report parse errors
// without crashing, and still surface the well-formed parts of the
// file (here, `Healthy`) so the outline isn't empty for partially
// broken sources.

class Healthy {
public:
    void ok();
};

class Broken {
public:
    void method(  // missing closing paren
};

struct AlsoOk {
    int x;
};
