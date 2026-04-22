// Exercises: nested types, method overloads, operator overloading,
// explicit/implicit conversion operators, static members.
using System;

namespace Demo.Math
{
    public struct Money
    {
        public decimal Amount { get; }
        public string Currency { get; }

        public Money(decimal amount, string currency)
        {
            Amount = amount;
            Currency = currency;
        }

        public static Money operator +(Money a, Money b)
        {
            if (a.Currency != b.Currency) throw new InvalidOperationException();
            return new Money(a.Amount + b.Amount, a.Currency);
        }

        public static Money operator -(Money a, Money b)
        {
            if (a.Currency != b.Currency) throw new InvalidOperationException();
            return new Money(a.Amount - b.Amount, a.Currency);
        }

        public static implicit operator decimal(Money m) => m.Amount;
        public static explicit operator Money(decimal amount) => new Money(amount, "USD");

        public bool Equals(Money other) => Amount == other.Amount && Currency == other.Currency;
        public bool Equals(decimal other) => Amount == other;

        public override string ToString() => $"{Amount} {Currency}";

        public class Builder
        {
            private decimal _amount;
            private string _currency = "USD";

            public Builder WithAmount(decimal a) { _amount = a; return this; }
            public Builder WithCurrency(string c) { _currency = c; return this; }
            public Money Build() => new Money(_amount, _currency);
        }

        public enum Rounding { Floor, Ceiling, Nearest }
    }
}
