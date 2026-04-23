package com.example.demo;

import java.io.Serializable;

/**
 * Enum with constructor, fields and instance methods.
 */
public enum Status implements Serializable {

    ACTIVE("Active", 1),
    INACTIVE("Inactive", 0),
    BANNED("Banned", -1),
    UNKNOWN;  // constant without constructor args

    private final String label;
    private final int weight;

    Status() {
        this("?", 0);
    }

    Status(String label, int weight) {
        this.label = label;
        this.weight = weight;
    }

    public String label() {
        return label;
    }

    public int weight() {
        return weight;
    }

    public static Status parse(String raw) {
        return raw == null ? UNKNOWN : valueOf(raw.toUpperCase());
    }
}
