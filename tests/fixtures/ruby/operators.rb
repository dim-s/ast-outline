# Comprehensive operator coverage — every operator the grammar exposes.
class Vector
  attr_reader :x, :y

  def initialize(x, y)
    @x = x
    @y = y
  end

  # arithmetic
  def +(other); Vector.new(@x + other.x, @y + other.y); end
  def -(other); Vector.new(@x - other.x, @y - other.y); end
  def *(scalar); Vector.new(@x * scalar, @y * scalar); end
  def /(scalar); Vector.new(@x / scalar, @y / scalar); end
  def %(scalar); Vector.new(@x % scalar, @y % scalar); end
  def **(scalar); Vector.new(@x ** scalar, @y ** scalar); end

  # comparison
  def ==(other); @x == other.x && @y == other.y; end
  def !=(other); !(self == other); end
  def <(other); magnitude < other.magnitude; end
  def >(other); magnitude > other.magnitude; end
  def <=(other); magnitude <= other.magnitude; end
  def >=(other); magnitude >= other.magnitude; end
  def <=>(other); magnitude <=> other.magnitude; end
  def ===(other); equal?(other); end

  # bitwise / shift
  def &(other); Vector.new(@x & other.x, @y & other.y); end
  def |(other); Vector.new(@x | other.x, @y | other.y); end
  def ^(other); Vector.new(@x ^ other.x, @y ^ other.y); end
  def ~; Vector.new(~@x, ~@y); end
  def <<(n); Vector.new(@x << n, @y << n); end
  def >>(n); Vector.new(@x >> n, @y >> n); end

  # indexing
  def [](key); key == :x ? @x : @y; end
  def []=(key, value); key == :x ? @x = value : @y = value; end

  # unary
  def -@; Vector.new(-@x, -@y); end
  def +@; self; end
  def !; @x.zero? && @y.zero?; end

  def magnitude
    Math.sqrt(@x ** 2 + @y ** 2)
  end
end
