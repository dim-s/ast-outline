package util

/** Extension function — receiver `String` is kept in the signature. */
fun String.reversed2(): String = this.reversed()

/** Extension with generics on both the receiver type and the function. */
fun <T : Number> List<T>.sumAs(): Double = sumOf { it.toDouble() }

/** Suspending function — coroutine-flavoured. */
suspend fun fetch(url: String): String = "ok: $url"

/** Inline + reified — common Kotlin idiom. */
inline fun <reified T> cast(any: Any): T = any as T

/** Infix + operator — qualify both via modifiers. */
class Vec2(val x: Int, val y: Int) {
    operator fun plus(other: Vec2): Vec2 = Vec2(x + other.x, y + other.y)
    infix fun dot(other: Vec2): Int = x * other.x + y * other.y
}

/** Default-arg + vararg in one signature. */
fun pick(prefix: String = ">", vararg values: Int): List<Int> = values.toList()

/** Module-level read-only top-level val/const. */
const val MAX: Int = 10
val TOP: String = "hi"

/** Type aliases. */
typealias Handler = (String) -> Unit
typealias Pair2<A> = Pair<A, A>
