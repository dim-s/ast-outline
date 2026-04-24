package com.example.demo.model

/** Case class — primary-ctor params surface as fields even without val/var. */
case class Point(x: Int, y: Int) extends Ordered[Point] {
  override def compare(that: Point): Int = x - that.x
}

/** Sealed trait + case class / case object branches. */
sealed trait Shape {
  def area: Double
}

case class Circle(radius: Double) extends Shape {
  override def area: Double = math.Pi * radius * radius
}

class Square(val side: Double) extends Shape {
  override def area: Double = side * side
}

case object UnitShape extends Shape {
  override def area: Double = 1.0
}

/** Scala 3 enum with primary-ctor field and a declared method. */
enum Status(val label: String, val weight: Int) extends java.io.Serializable:
  case Active   extends Status("Active",   3)
  case Inactive extends Status("Inactive", 1)
  case Banned   extends Status("Banned",   0)
  case Unknown  extends Status("?", -1)

  def display: String = s"$label[$weight]"
