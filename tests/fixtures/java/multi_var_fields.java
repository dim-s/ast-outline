package com.example.demo.misc;

/**
 * Edge case: multi-variable field declarations + array types.
 */
public class Vectors {

    // Two fields in one declaration — we pick the first name ("a")
    public int a, b, c;

    // Array type
    public int[] arr;

    // Multi-declarator with initialisers
    long start = 0, end = 100;

    // Generics with bounds
    private java.util.List<? extends Number> items;

    public Vectors() {}
}
