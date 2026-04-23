package com.example.demo.repo;

import java.util.List;
import java.util.Optional;

/**
 * Generic repository interface — JDK 8+ features
 * (default methods, static methods on interfaces).
 */
public interface Repository<K, V> extends AutoCloseable {

    Optional<V> findById(K id);

    List<V> findAll();

    /** Default method: hides the Optional. */
    default boolean exists(K id) {
        return findById(id).isPresent();
    }

    static <K, V> Repository<K, V> empty() {
        return null;
    }

    @Override
    void close();

    // Nested type inside an interface — implicitly public per Java spec.
    class NotFound extends RuntimeException {
        public NotFound(String msg) { super(msg); }
    }
}

interface Marker {}

@FunctionalInterface
interface Mapper<A, B> {
    B map(A input);
}
