# Edge cases around the visibility state machine.
class A
  # Default — visible.
  def public_default
  end

  private

  def secret_one
  end

  def secret_two
  end

  protected

  def shareable_one
  end

  public

  def visible_after_public
  end

  # Targeted forward form: targets the as-yet-undefined `late_private`.
  # Should still apply because the deferred pass sees the def below.
  private :late_private

  def late_private
  end
end

class B
  def reachable
  end

  def hidden_method
  end

  # Targeted form that names methods defined ABOVE.
  private :hidden_method

  def again_visible
  end
end

class C
  def self.class_a
  end

  def self.class_b
  end

  private_class_method :class_a, :class_b

  def self.still_public_class
  end
end

# Bare `private()` with explicit empty parens — rare but valid Ruby.
class D
  def public_first
  end

  private()

  def now_private
  end
end
