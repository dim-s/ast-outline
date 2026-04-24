// Deliberately malformed Scala — exercises the parse-error counter.
// The first method is intact so the adapter can still emit it; the
// second has a missing closing paren that trips tree-sitter.
class Broken {
  def good: Int = 1
  def oops(x: Int =
  def trailing: Int = 3
}
