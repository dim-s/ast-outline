// Braced package form — declarations INSIDE the braces belong to
// `alpha`, but declarations OUTSIDE stay at the file's default scope.
package alpha {
  class Inside {
    def method: Int = 1
  }
}

class Outside {
  def method: Int = 2
}
