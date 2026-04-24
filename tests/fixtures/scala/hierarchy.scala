package zoo

class Animal(val name: String)

abstract class Dog(name: String) extends Animal(name) {
  def bark: String = "Woof"
}

class Puppy(name: String) extends Dog(name) {
  override def bark: String = "Yip"
}

class Pomeranian(name: String) extends Puppy(name)

// `case object` and `case class` as subclasses — both should show up
// in `implements` queries for their parent.
case object Rex extends Dog("Rex")

case class Husky(dogName: String) extends Dog(dogName)

trait Movable {
  def move(distance: Int): Int
}

class Skater extends Animal("s") with Movable {
  override def move(distance: Int): Int = distance * 2
}
