package zoo.mammals

import zoo.base.Animal

class Dog(name: String) extends Animal(name) {
  override def sound: String = "Woof"
}
