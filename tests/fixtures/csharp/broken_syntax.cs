// Deliberately broken C# — used to verify parse-error counting.
// tree-sitter-c-sharp surfaces ERROR / MISSING nodes for missing
// braces, broken method signatures, and incomplete expressions.

namespace Demo.Broken
{
    public class Ok
    {
        public int Good() { return 1; }
    }

    public class Busted
    {
        public void Broken(int x {
            int y = ;
        }

        public int StillVisible => 42;
