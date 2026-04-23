package zoo.mammals

import zoo.base.Animal

open class Dog(name: String) : Animal(name) {
    override fun sound(): String = "Woof"
}
