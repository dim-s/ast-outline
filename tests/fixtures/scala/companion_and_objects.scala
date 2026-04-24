package app

/** Top-level singleton object. */
object Logger {
  private val Prefix: String = "[app]"

  def log(msg: String): Unit = println(s"$Prefix $msg")
}

/**
 * Class + companion object pair — Scala's idiomatic equivalent of
 * Kotlin's companion object, but modelled as two SEPARATE top-level
 * declarations with the same name.
 */
class Registry {
  def id: Int = Registry.nextId
}

object Registry {
  private var counter: Int = 0
  def nextId: Int = {
    counter += 1
    counter
  }
}

/** Named singleton implementing a trait. */
trait Named {
  def name: String
}

class BaseHandler {
  def handle(): Unit = ()
}

object RootHandler extends BaseHandler with Named {
  override def name: String = "root"
  override def handle(): Unit = ()
}
