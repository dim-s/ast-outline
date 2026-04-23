package com.example.demo.service;

import java.io.IOException;
import java.util.List;
import java.util.Optional;

/**
 * Service layer for user accounts.
 *
 * <p>Demonstrates: Javadoc, multiple annotations, inheritance,
 * generics, throws, abstract methods, nested types.
 */
@Service
@Deprecated(since = "2.0", forRemoval = false)
public class UserService extends BaseService implements UserRepository, AutoCloseable {

    /** Hard cap on concurrent users. */
    public static final int MAX_USERS = 100;

    private final String name;
    protected List<String> items;
    String packagePrivateField;

    public UserService(String name) {
        super();
        this.name = name;
    }

    protected UserService() {
        this("anonymous");
    }

    /** Saves a user. */
    @Override
    public void save(User user) throws IOException, IllegalArgumentException {
        // impl
    }

    private static <T extends Comparable<T>> T findMax(List<T> items) {
        return items.isEmpty() ? null : items.get(0);
    }

    public abstract int compute();

    @Override
    public void close() {}

    public static final class Inner {
        private final int value;

        public Inner(int value) {
            this.value = value;
        }

        public int value() {
            return value;
        }
    }

    public interface Callback {
        void onDone(String result);
    }
}
