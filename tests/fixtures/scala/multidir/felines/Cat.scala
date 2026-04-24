package zoo.felines

import zoo.base.Animal

class Cat(name: String) extends Animal(name) {
  override def sound: String = "Meow"
}
