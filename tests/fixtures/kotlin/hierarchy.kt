package zoo

open class Animal(val name: String)

abstract class Dog(name: String) : Animal(name) {
    open fun bark(): String = "Woof"
}

open class Puppy(name: String) : Dog(name) {
    override fun bark() = "Yip"
}

class Pomeranian(name: String) : Puppy(name)

// Object + data class subclasses — both should show up in implements queries
object Rex : Dog("Rex")

data class Husky(val dogName: String) : Dog(dogName)

interface Movable {
    fun move(distance: Int): Int
}

class Skater : Animal("s"), Movable {
    override fun move(distance: Int) = distance * 2
}
