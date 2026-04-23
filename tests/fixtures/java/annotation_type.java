package com.example.demo.ann;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * Custom annotation (@interface declaration).
 */
@Retention(RetentionPolicy.RUNTIME)
@Target({ElementType.TYPE, ElementType.METHOD})
public @interface Tagged {

    /** Primary tag name. */
    String value() default "";

    /** Priority — higher runs first. */
    int priority() default 0;

    String[] aliases() default {};

    Class<?>[] consumers() default {};
}

@interface PackagePrivateMarker {}

// Class carrying an annotation whose value string contains unbalanced
// parens — must still strip the annotation cleanly.
@SuppressWarnings("tricky (value) with ) parens")
class TrickyAnnotated {
    public void m() {}
}
