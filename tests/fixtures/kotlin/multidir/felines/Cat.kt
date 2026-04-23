package zoo.felines

import zoo.base.Animal

class Cat(name: String) : Animal(name) {
    override fun sound(): String = "Meow"
}
