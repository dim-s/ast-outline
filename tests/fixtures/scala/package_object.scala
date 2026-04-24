package com.example

/** Scala 2 package object — hybrid of namespace and singleton carrying
 *  package-level defs, vals, and type aliases. */
package object utils {
  type Handler = String => Unit

  def helper(x: Int): Int = x + 1

  val PI: Double = 3.14
}
