// Multi-level inheritance fixture for `implements` transitive tests.
// Uses C# features: abstract base, virtual/override, interface chain,
// and an interface hierarchy (IService → IReadService → ISpecificService).

namespace Demo.Hierarchy
{
    public abstract class Animal
    {
        public abstract void Eat();
    }

    public class Dog : Animal
    {
        public override void Eat() {}
    }

    public class Cat : Animal
    {
        public override void Eat() {}
    }

    // Transitive through Dog.
    public class Puppy : Dog
    {
        public void Play() {}
    }

    // Deeper transitive: Animal ← Dog ← Puppy ← Pomeranian.
    public sealed class Pomeranian : Puppy
    {
        public void Yap() {}
    }

    // Interface chain.
    public interface IService
    {
        void Run();
    }

    public interface IReadService : IService
    {
        object Read();
    }

    // Transitive implementor: IReadService extends IService → UserService
    // transitively implements IService via IReadService.
    public class UserService : IReadService
    {
        public void Run() {}
        public object Read() => null;
    }
}
