package props

/**
 * Exercises all the property-declaration shapes the adapter must handle:
 * plain val/var (→ FIELD), val with a custom getter (→ PROPERTY), var with
 * both get+set (→ PROPERTY), primary-ctor val/var (→ FIELD), and top-level
 * const / lateinit.
 */
class Container(val id: Int, var label: String) {

    // plain storage → FIELD
    var weight: Double = 0.0
    val species: String = "unknown"

    // custom getter only → PROPERTY
    val square: Int
        get() = id * id

    // custom getter AND setter → PROPERTY
    var cached: String = ""
        get() = field.uppercase()
        set(value) { field = value.trim() }

    // lateinit var — still plain storage → FIELD
    lateinit var pending: String
}

const val TOP_CONST: Int = 42
val TOP_VAL: String = "hello"
var TOP_VAR: Int = 0
lateinit var TOP_LATEINIT: String
