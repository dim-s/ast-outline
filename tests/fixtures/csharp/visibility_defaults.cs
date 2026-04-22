// Fixture for testing C# default visibility rules:
//   - top-level type in a namespace with no modifier → default `internal`
//   - class member with no modifier → default `private`
//   - struct member with no modifier → default `private`
//   - interface member with no modifier → default `public`
namespace Demo.Visibility
{
    class DefaultInternalClass
    {
        void DefaultPrivateMethod() { }
        int defaultPrivateField;
    }

    struct DefaultInternalStruct
    {
        void StructDefaultPrivateMethod() { }
    }

    interface DefaultInternalInterface
    {
        void InterfaceDefaultPublicMethod();
    }
}
