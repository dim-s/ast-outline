// Exercises file-scoped namespace syntax (C# 10+), records, generic classes,
// constructors, expression-bodied members.
using System;
using System.Collections.Generic;

namespace Demo.Services;

public record UserDto(int Id, string Name, string Email);

public record struct Vec2(float X, float Y);

public interface IRepository<T>
{
    T? GetById(int id);
    IReadOnlyList<T> List();
}

public class UserRepository : IRepository<UserDto>
{
    private readonly Dictionary<int, UserDto> _store = new();

    public UserRepository() { }

    public UserDto? GetById(int id) => _store.TryGetValue(id, out var u) ? u : null;

    public IReadOnlyList<UserDto> List()
    {
        var list = new List<UserDto>(_store.Values);
        return list;
    }

    public void Save(UserDto user)
    {
        _store[user.Id] = user;
    }
}

public static class UserExtensions
{
    public static string DisplayLabel(this UserDto u) => $"{u.Name} <{u.Email}>";
}
