package scala3

/** Indentation-based class body — no braces, `:` opens the block. */
class Foo(val x: Int):
  def double: Int = x * 2
  def triple: Int = x * 3
end Foo

/** Trait in indentation style. */
trait Greeter:
  def greet(name: String): String

/** `given` with an explicit name + body (class-shaped). */
given intOrdering: Ordering[Int] with
  def compare(a: Int, b: Int): Int = a - b

/** Anonymous given — falls back to a type-derived synthetic name. */
given Ordering[String] with
  def compare(a: String, b: String): Int = a.compareTo(b)

/** Function using a given via `using`. */
def sorted[T](xs: List[T])(using ord: Ordering[T]): List[T] = xs.sorted

/** Higher-kinded type parameter. */
trait Functor[F[_]]:
  def map[A, B](fa: F[A])(f: A => B): F[B]

/** Context bound. */
def findMax[T: Ordering](xs: List[T]): T = xs.max
