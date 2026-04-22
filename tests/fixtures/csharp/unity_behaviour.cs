// Unity-style MonoBehaviour. Exercises:
//   - traditional (braced) namespace
//   - XML doc comments above types and members
//   - [Attributes] on type and fields
//   - auto-property and expression-bodied property
//   - event field
//   - private method (default visibility for class members)
//   - nested enum inside a class
//   - interface declaration alongside the class
using System;
using UnityEngine;

namespace Demo.Combat
{
    /// <summary>
    /// Controls the hero in-scene: movement, damage, death.
    /// </summary>
    [RequireComponent(typeof(Rigidbody2D))]
    public class HeroController : MonoBehaviour, IDamageable
    {
        [SerializeField] private float _speed = 5f;
        [SerializeField] private int _maxHealth = 100;

        public int CurrentHealth { get; private set; }
        public bool IsAlive => CurrentHealth > 0;

        /// <summary>Fired whenever health changes.</summary>
        public event Action<int> OnHealthChanged;

        public HeroController() { }

        /// <summary>Apply damage to the hero.</summary>
        /// <param name="amount">HP to subtract.</param>
        public void TakeDamage(int amount)
        {
            CurrentHealth -= amount;
            OnHealthChanged?.Invoke(CurrentHealth);
            if (CurrentHealth <= 0) Die();
        }

        private void Die()
        {
            Destroy(gameObject);
        }

        public enum State { Idle, Moving, Dead }
    }

    public interface IDamageable
    {
        void TakeDamage(int amount);
    }
}
