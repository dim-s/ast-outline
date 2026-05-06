# Regression test for the C++ HIGH-fix: when a module has siblings,
# collapse must NOT swallow them. App::Outer should NOT collapse with
# Inner because Outer has TWO children (Inner + a class A) — collapsing
# would silently drop A.
module App
  module Outer
    class A
      def a_method
      end
    end

    class B
      def b_method
      end
    end
  end
end

# This module's body has only one named child but it's a class, not a
# module — must NOT trigger collapse (that rule only fires when the
# single child is itself a module).
module Solo
  class OnlyClass
    def lonely
    end
  end
end
