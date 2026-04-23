package app

/** Top-level singleton object. */
object Logger {
    private const val PREFIX = "[app]"

    fun log(msg: String) {
        println("$PREFIX $msg")
    }
}

/** Class with a named companion object that carries static-like state. */
class Registry {
    companion object Factory {
        private var counter: Int = 0
        fun next(): Int {
            counter += 1
            return counter
        }
    }

    fun id(): Int = Factory.next()
}

/** Class with an unnamed companion — Kotlin auto-names it `Companion`. */
class Cache {
    companion object {
        const val SIZE = 256
        fun empty(): Cache = Cache()
    }
}

/** Object inheriting a class and implementing an interface. */
interface Named {
    val name: String
}

open class BaseHandler {
    open fun handle() { }
}

object RootHandler : BaseHandler(), Named {
    override val name: String = "root"
    override fun handle() { }
}

