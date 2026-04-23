package multidir.mammals;

// Transitive subclass of Animal via Dog — same directory as Dog but
// Dog is the direct parent; Animal is only reachable through Dog.
public class Puppy extends Dog {
    public void play() {}
}
