package util

/** Scala 3 extension on String — receiver kept in the rendered signature. */
extension (s: String) def reversed2: String = s.reverse

/** Extension block with multiple methods + type parameter. */
extension [T: Numeric](xs: List[T])
  def sumAs: Double = xs.map(implicitly[Numeric[T]].toDouble).sum
  def lengthAs: Int = xs.length

/** Top-level def + val (Scala 3). */
def pick(prefix: String = ">", values: Int*): List[Int] = values.toList

def topLevel(x: Int, y: Int = 0): Int = x + y

val TOP: String = "hi"
final val MAX: Int = 10

/** Type aliases — regular + opaque. */
type Handler = String => Unit
opaque type UserId = String
