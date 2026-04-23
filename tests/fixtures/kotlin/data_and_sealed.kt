package com.example.demo.model

/** Plain data class — primary-ctor components should become fields. */
data class Point(val x: Int, val y: Int) : Comparable<Point> {
    override fun compareTo(other: Point): Int = x.compareTo(other.x)
}

/** Sealed class hierarchy — permits is implicit (subclasses in same file/module). */
sealed class Shape {
    abstract fun area(): Double
}

data class Circle(val radius: Double) : Shape() {
    override fun area(): Double = Math.PI * radius * radius
}

class Square(val side: Double) : Shape() {
    override fun area(): Double = side * side
}

object UnitShape : Shape() {
    override fun area(): Double = 1.0
}

/**
 * Enum class with a primary-ctor field, value-carrying entries, and a
 * declared method that follows the entries.
 */
enum class Status(val label: String, val weight: Int) : java.io.Serializable {
    ACTIVE("Active", 3),
    INACTIVE("Inactive", 1),
    BANNED("Banned", 0),
    UNKNOWN("?", -1);

    fun display(): String = "$label[$weight]"

    companion object {
        fun parse(s: String): Status = values().firstOrNull { it.label == s } ?: UNKNOWN
    }
}
