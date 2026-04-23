package com.example.demo.model;

// Java 16+ features: records; Java 17+: sealed classes.

/** A 2D point — Java record (Java 16+). */
public record Point(double x, double y) implements Comparable<Point> {

    public static final Point ORIGIN = new Point(0, 0);

    /** Compact constructor — validates and normalises. */
    public Point {
        if (Double.isNaN(x) || Double.isNaN(y)) {
            throw new IllegalArgumentException("NaN coordinate");
        }
    }

    public Point(double xy) {
        this(xy, xy);
    }

    @Override
    public int compareTo(Point other) {
        int cx = Double.compare(x, other.x);
        return cx != 0 ? cx : Double.compare(y, other.y);
    }

    public double distanceTo(Point other) {
        double dx = x - other.x;
        double dy = y - other.y;
        return Math.sqrt(dx * dx + dy * dy);
    }
}

/** Sealed hierarchy (Java 17+). */
public sealed class Shape permits Circle, Square, Triangle {
    public double area() {
        return 0;
    }
}

public final class Circle extends Shape {
    private final double radius;

    public Circle(double radius) {
        this.radius = radius;
    }

    @Override
    public double area() {
        return Math.PI * radius * radius;
    }
}

public non-sealed class Square extends Shape {
    private final double side;

    public Square(double side) {
        this.side = side;
    }
}

public final class Triangle extends Shape {
    private final double base;
    private final double height;

    public Triangle(double base, double height) {
        this.base = base;
        this.height = height;
    }
}
