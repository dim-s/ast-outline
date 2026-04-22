using System;
using System.Collections.Generic;
using UnityEngine;

namespace Game.Player
{
    /// <summary>
    /// Player controller. Handles movement, input, and damage.
    /// </summary>
    [RequireComponent(typeof(Rigidbody2D))]
    public class PlayerController : MonoBehaviour, IDamageable
    {
        [SerializeField] private float speed = 5f;
        [SerializeField] private int maxHealth = 100;
        private Rigidbody2D _rb;

        public int CurrentHealth { get; private set; }
        public bool IsAlive => CurrentHealth > 0;

        /// <summary>Fired when health changes.</summary>
        public event Action<int> OnHealthChanged;

        public PlayerController() { }

        /// <summary>Apply damage to the player.</summary>
        /// <param name="amount">Damage amount in HP.</param>
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

        private void Awake() => _rb = GetComponent<Rigidbody2D>();

        public enum State { Idle, Moving, Dead }
    }

    public interface IDamageable
    {
        void TakeDamage(int amount);
    }

    public record struct Vec2(float X, float Y);
}
