package ctor

/**
 * Class with a primary constructor, multiple secondary constructors,
 * and an `init { }` block (which the adapter must skip as anonymous).
 */
class Connection(val host: String, val port: Int) {
    init {
        require(port > 0)
    }

    constructor(host: String) : this(host, 80)

    constructor() : this("localhost")

    fun open(): Boolean = true
}
