package com.example.demo.service

import java.io.IOException

/**
 * Primary user-facing service with CRUD + auth.
 *
 * Used by the example suite as a canonical smoke fixture for the
 * Kotlin adapter — exercises visibility modifiers, KDoc, annotations,
 * generics, and nested types all at once.
 */
@Service
@Deprecated("use V2")
open class UserService(
    @JvmField val name: String,
    private val items: MutableList<String> = mutableListOf(),
) : BaseService(), UserRepository, AutoCloseable {

    companion object {
        const val MAX_USERS: Int = 100
        @JvmStatic
        fun defaultName(): String = "anonymous"
    }

    // package-private equivalent in Kotlin is `internal` — module-scoped
    internal var packagePrivateField: Int = 0

    protected val cache: MutableMap<String, Any> = mutableMapOf()

    /**
     * Persists the incoming user; throws IOException on I/O failure.
     */
    @Throws(IOException::class, IllegalArgumentException::class)
    @Override
    override fun save(user: String): Boolean {
        items.add(user)
        return true
    }

    private fun <T : Comparable<T>> findMax(xs: List<T>): T = xs.max()

    abstract fun compute(x: Int, y: Int): Int

    override fun close() {
        items.clear()
    }

    /** Nested class — public by default in Kotlin. */
    class Inner {
        fun value(): Int = 42
        constructor() { }
    }

    /** Nested interface (fun interface). */
    fun interface Callback {
        fun onDone(code: Int): Unit
    }
}
