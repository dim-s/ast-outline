package com.example.demo.service

import java.io.IOException
import scala.collection.mutable

/**
 * Primary user-facing service with CRUD + auth.
 *
 * Canonical smoke fixture for the Scala adapter: exercises access
 * modifiers, Scaladoc, annotations, generics, nested types, and both
 * val- and var-defined primary-ctor properties.
 */
@deprecated("use V2")
@SerialVersionUID(1L)
class UserService(
  val name: String,
  private val items: mutable.ListBuffer[String] = mutable.ListBuffer.empty,
) extends BaseService with UserRepository with AutoCloseable {

  final val MAX_USERS: Int = 100

  // Scala's `internal`-like default is `public` — no modifier is public.
  var packageDefault: Int = 0

  protected val cache: mutable.Map[String, Any] = mutable.Map.empty

  /**
   * Persists the incoming user; throws IOException on I/O failure.
   */
  @throws(classOf[IOException])
  override def save(user: String): Boolean = {
    items += user
    true
  }

  private def findMax[T: Ordering](xs: List[T]): T = xs.max

  def compute(x: Int, y: Int): Int

  override def close(): Unit = items.clear()

  /** Nested class — public by default. */
  class Inner {
    def value: Int = 42
  }

  /** Nested trait. */
  trait Callback {
    def onDone(code: Int): Unit
  }
}

/** Companion object — standard Scala singleton-paired-with-class idiom. */
object UserService {
  def apply(name: String): UserService = new UserService(name)
}
