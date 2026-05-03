<?php
namespace App\First {
    use App\Foo;

    class FirstA {
        public function go(): void {}
    }
    class FirstB {}
}

namespace App\Second {
    use App\Bar;

    interface Greeter {
        public function greet(): string;
    }

    function helper(): int { return 0; }
}

namespace {
    class GlobalScoped {}
}
