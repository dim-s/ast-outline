@file:JvmName("DemoAnnotations")

package gen

import java.io.Serializable

/**
 * Generic class with an upper-bound type parameter, a `where` constraint,
 * multiple interfaces, and a method with its own generics.
 */
@Deprecated("old API")
@JvmName("GraphImpl")
class Graph<N : Comparable<N>, E>(
    val root: N,
) : Iterable<N>, Serializable where N : Cloneable {

    @Throws(java.io.IOException::class)
    fun <R : Any> traverse(visitor: (N) -> R): List<R> = emptyList()

    @SafeVarargs
    fun <X> accept(vararg items: X): Int = items.size

    // Annotation whose arg contains a parens-bearing string literal:
    // the annotation stripper must skip the literal when balancing parens.
    @SuppressWarnings("unused(value)")
    class TrickyAnnotated
}

/** Annotation class (Kotlin's `@interface`). */
annotation class Marker(val value: String = "", val level: Int = 0)

/** Functional interface (`fun interface`). */
fun interface Mapper<A, B> {
    fun map(a: A): B
}
