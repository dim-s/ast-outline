package com.example.demo.gx;

import java.io.IOException;
import java.util.Collection;
import java.util.function.Function;

/**
 * Heavy-generics + throws-clause fixture.
 */
public class Graph<N extends Comparable<N>, E> {

    private final N root;

    public Graph(N root) {
        this.root = root;
    }

    public <R> R traverse(Function<? super N, ? extends R> visitor) throws IOException {
        return visitor.apply(root);
    }

    public static <T, U extends Collection<T>> U collect(
            Iterable<? extends T> input,
            U sink) throws IOException, InterruptedException {
        for (T t : input) {
            sink.add(t);
        }
        return sink;
    }

    @SafeVarargs
    public final <X> void accept(X... elements) {
        // varargs + generic
    }
}
