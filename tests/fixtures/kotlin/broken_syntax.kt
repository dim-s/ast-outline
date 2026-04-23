// Deliberately malformed Kotlin — exercises the parse-error counter so the
// outline's WARNING header fires.
class Broken {
    fun good(): Int = 1

    fun oops(x: Int
}
